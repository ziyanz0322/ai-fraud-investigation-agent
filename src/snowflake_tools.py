import json
from datetime import date, datetime
from decimal import Decimal

from snowflake.connector import DictCursor

from src.snowflake_database import create_snowflake_connection


def normalize_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def fetch_one(conn, query, parameters):
    with conn.cursor(DictCursor) as cursor:
        cursor.execute(query, parameters)
        row = cursor.fetchone()

    if row is None:
        return None

    return {key.lower(): normalize_value(value) for key, value in row.items()}


def get_target_transaction(conn, transaction_id):
    row = fetch_one(
        conn,
        """
        SELECT
            transaction_id,
            account_id,
            transaction_time,
            amount,
            transaction_type,
            merchant_id,
            device_id,
            status,
            state,
            channel
        FROM FRAUD_DB.DBT_DEV.STG_TRANSACTIONS
        WHERE transaction_id = %s
        """,
        (transaction_id,),
    )

    if row is None:
        raise ValueError(f"Transaction not found: {transaction_id}")

    return row


def get_account_profile(conn, account_id):
    return fetch_one(
        conn,
        """
        SELECT
            account_id,
            created_at,
            state,
            customer_segment,
            status
        FROM FRAUD_DB.DBT_DEV.STG_USERS
        WHERE account_id = %s
        """,
        (account_id,),
    )


def get_risk_features(conn, transaction_id):
    row = fetch_one(
        conn,
        """
        SELECT *
        FROM FRAUD_DB.DBT_DEV.FCT_TRANSACTION_RISK
        WHERE transaction_id = %s
        """,
        (transaction_id,),
    )

    if row is None:
        raise ValueError(f"Risk features not found: {transaction_id}")

    return row


def fetch_all(conn, query, parameters):
    with conn.cursor(DictCursor) as cursor:
        cursor.execute(query, parameters)
        rows = cursor.fetchall()

    return [
        {key.lower(): normalize_value(value) for key, value in row.items()}
        for row in rows
    ]


def get_transaction_history(conn, transaction_id):
    get_target_transaction(conn, transaction_id)

    return fetch_all(
        conn,
        """
        SELECT
            h.transaction_id,
            h.transaction_time,
            h.amount,
            h.transaction_type,
            h.merchant_id,
            h.device_id,
            h.status,
            h.state,
            h.channel
        FROM FRAUD_DB.DBT_DEV.STG_TRANSACTIONS h
        JOIN FRAUD_DB.DBT_DEV.STG_TRANSACTIONS t
            ON h.account_id = t.account_id
        WHERE t.transaction_id = %s
          AND h.transaction_time < t.transaction_time
        ORDER BY h.transaction_time DESC, h.transaction_id
        """,
        (transaction_id,),
    )


def get_chargeback_history(conn, transaction_id):
    get_target_transaction(conn, transaction_id)

    return fetch_all(
        conn,
        """
        SELECT
            c.chargeback_id,
            c.transaction_id,
            c.chargeback_date,
            c.reason_code,
            c.amount
        FROM FRAUD_DB.DBT_DEV.STG_CHARGEBACKS c
        JOIN FRAUD_DB.DBT_DEV.STG_TRANSACTIONS t
            ON c.account_id = t.account_id
        WHERE t.transaction_id = %s
          AND c.chargeback_date < t.transaction_time
        ORDER BY c.chargeback_date DESC, c.chargeback_id
        """,
        (transaction_id,),
    )


def calculate_risk_signals(conn, transaction_id):
    row = get_risk_features(conn, transaction_id)

    # These descriptions must stay aligned with the dbt rules.
    definitions = [
        (
            "S01",
            "new_account",
            "account_age_days",
            "s01_new_account",
            "<",
            30,
            None,
            None,
        ),
        (
            "S02",
            "high_value_transaction",
            "amount",
            "s02_high_value_transaction",
            ">",
            3000,
            None,
            None,
        ),
        (
            "S03",
            "high_transaction_velocity",
            "transaction_count_last_30m",
            "s03_high_transaction_velocity",
            ">=",
            5,
            "window_minutes",
            30,
        ),
        (
            "S04",
            "new_device",
            "device_age_hours",
            "s04_new_device",
            "<",
            24,
            None,
            None,
        ),
        (
            "S05",
            "dormant_account_reactivation",
            "days_since_previous_transaction",
            "s05_dormant_account_reactivation",
            ">",
            180,
            None,
            None,
        ),
        (
            "S06",
            "repeated_counterparty",
            "same_merchant_transaction_count_last_24h",
            "s06_repeated_counterparty",
            ">=",
            4,
            "window_hours",
            24,
        ),
        (
            "S07",
            "repeated_failed_payments",
            "failed_transaction_count_last_30m",
            "s07_repeated_failed_payments",
            ">=",
            3,
            "window_minutes",
            30,
        ),
        (
            "S08",
            "prior_chargebacks",
            "chargeback_count_last_180d",
            "s08_prior_chargebacks",
            ">=",
            2,
            "window_days",
            180,
        ),
    ]

    signals = []

    for (
        signal_id,
        signal_name,
        feature_name,
        result_column,
        operator,
        threshold,
        window_key,
        window_value,
    ) in definitions:
        triggered = row[result_column]

        if not isinstance(triggered, bool):
            raise ValueError(
                f"{transaction_id}: invalid result for {signal_id}: {triggered!r}"
            )

        value = row[feature_name]

        if value is not None:
            if feature_name in {"amount", "device_age_hours"}:
                value = float(value)
            else:
                value = int(value)
        elif signal_id != "S05":
            raise ValueError(f"{transaction_id}: missing feature {feature_name}")

        signal = {
            "signal_id": signal_id,
            "signal_name": signal_name,
            "feature_name": feature_name,
            "feature_value": value,
            "operator": operator,
            "threshold": threshold,
            "triggered": triggered,
        }

        if window_key:
            signal[window_key] = window_value

        if signal_id in {"S03", "S06", "S07"}:
            signal["window_includes_target_time"] = True
            signal["counts_attempts"] = True

        if signal_id == "S07":
            signal["included_statuses"] = ["failed", "declined"]

        if signal_id == "S08":
            signal["strictly_before_target"] = True

        if signal_id == "S01":
            signal["created_at"] = row["account_created_at"]
            signal["transaction_time"] = row["transaction_time"]

            if value < 0:
                signal["data_quality_issue"] = (
                    "transaction_time_before_account_creation"
                )

        signals.append(signal)

    stored_count = row["triggered_signal_count"]

    if stored_count is None:
        raise ValueError(f"{transaction_id}: missing signal count")

    triggered_count = int(stored_count)

    if triggered_count != sum(s["triggered"] for s in signals):
        raise ValueError(f"{transaction_id}: inconsistent signal count")

    return {
        "transaction_id": row["transaction_id"],
        "account_id": row["account_id"],
        "triggered_signal_count": triggered_count,
        "signals": signals,
    }


if __name__ == "__main__":
    conn = create_snowflake_connection()

    try:
        result = calculate_risk_signals(conn, "TXN_010")
        print(json.dumps(result, indent=2))
    finally:
        conn.close()
