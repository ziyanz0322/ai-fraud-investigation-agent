from datetime import datetime


# S01: NEW ACCOUNTS
# used to calculate how many days between a certain transaction and accounts opening
def calculate_account_age_signal(conn, transaction_id, threshold_days=30):
    query = """
    SELECT
        t.transaction_time,
        u.created_at
    FROM transactions t
    JOIN users u
        ON t.account_id = u.account_id
    WHERE t.transaction_id = ?;
    """

    cursor = conn.execute(query, (transaction_id,))
    row = cursor.fetchone()

    if row is None:
        return None

    transaction_time = row[0]
    created_at = row[1]

    transaction_dt = datetime.fromisoformat(transaction_time)
    created_dt = datetime.fromisoformat(created_at)

    account_age = transaction_dt - created_dt
    account_age_days = account_age.days

    triggered = account_age_days < threshold_days

    # data quality adjustment --> if account age dates < 0
    if account_age_days < 0:
        return {
            "signal_id": "S01",
            "signal_name": "new_account",
            "feature_name": "account_age_days",
            "feature_value": account_age_days,
            "threshold": threshold_days,
            "triggered": False,
            "data_quality_issue": "transaction_time_before_account_creation",
            "created_at": created_at,
            "transaction_time": transaction_time,
        }

    return {
        "signal_id": "S01",
        "signal_name": "new_account",
        "feature_name": "account_age_days",
        "feature_value": account_age_days,
        "threshold": threshold_days,
        "triggered": triggered,
        "created_at": created_at,
        "transaction_time": transaction_time,
    }


# S02: HIGH VALUE TRANSACTION
# used to calculate if the transaction value is higher than threshold
def calculate_high_value_signal(conn, transaction_id, threshold_amount=3000):
    query = """
    SELECT amount
    FROM transactions
    WHERE transaction_id = ?;
    """

    cursor = conn.execute(query, (transaction_id,))
    row = cursor.fetchone()

    if row is None:
        return None

    amount = row[0]

    triggered = amount > threshold_amount

    return {
        "signal_id": "S02",
        "signal_name": "high_value_transaction",
        "feature_name": "transactions_amount",
        "feature_value": amount,
        "threshold": threshold_amount,
        "triggered": triggered,
    }


# S03: Transaction Volatility
# used to calculate counts of transactions (included current transaction) in last 30 minutes
from datetime import timedelta


def calculate_velocity_signal(
    conn, transaction_id, window_minutes=30, threshold_count=5
):
    query = """
    SELECT
        account_id,
        transaction_time
    FROM transactions
    WHERE transaction_id = ?;
    """

    cursor = conn.execute(query, (transaction_id,))
    row = cursor.fetchone()

    if row is None:
        return None

    account_id = row[0]
    transaction_time = row[1]

    transaction_dt = datetime.fromisoformat(transaction_time)
    window_start_dt = transaction_dt - timedelta(minutes=window_minutes)

    count_query = """
    SELECT COUNT(*)
    FROM transactions
    WHERE account_id = ?
      AND transaction_time >= ?
      AND transaction_time <= ?;
    """

    cursor = conn.execute(
        count_query,
        (
            account_id,
            window_start_dt.isoformat(sep=" "),
            transaction_dt.isoformat(sep=" "),
        ),
    )

    transaction_count = cursor.fetchone()[0]

    triggered = transaction_count >= threshold_count

    return {
        "signal_id": "S03",
        "signal_name": "high_transaction_velocity",
        "feature_name": "transaction_count_last_30m",
        "feature_value": transaction_count,
        "threshold": threshold_count,
        "window_minutes": window_minutes,
        "triggered": triggered,
    }


# S04: New Device
# used to calculate how many hours between a transaction and device first enrolled
def calculate_new_device_signal(conn, transaction_id, threshold_hours=24):
    query = """
    SELECT
        t.transaction_time,
        t.account_id,
        t.device_id,
        d.first_seen_at
    FROM transactions t
    JOIN devices d
        ON t.account_id = d.account_id
        AND t.device_id = d.device_id
    WHERE t.transaction_id = ?;
    """

    cursor = conn.execute(query, (transaction_id,))
    row = cursor.fetchone()

    if row is None:
        return None

    transaction_time = row[0]
    first_seen_at = row[3]

    transaction_dt = datetime.fromisoformat(transaction_time)
    first_seen_dt = datetime.fromisoformat(first_seen_at)

    device_age = transaction_dt - first_seen_dt
    device_age_hours = device_age.total_seconds() / 3600

    triggered = device_age_hours < threshold_hours

    return {
        "signal_id": "S04",
        "signal_name": "new_device",
        "feature_name": "device_age_hours",
        "feature_value": round(device_age_hours, 2),
        "threshold": threshold_hours,
        "triggered": triggered,
    }


# S05: Dormant Account Reactivation
# used to calculate days since last payments
def calculate_dormant_account_signal(conn, transaction_id, threshold_days=180):
    query = """
    SELECT
        account_id,
        transaction_time
    FROM transactions
    WHERE transaction_id = ?;
    """

    cursor = conn.execute(query, (transaction_id,))
    row = cursor.fetchone()

    if row is None:
        return None

    account_id = row[0]
    transaction_time = row[1]

    previous_query = """
    SELECT transaction_time
    FROM transactions
    WHERE account_id = ?
      AND transaction_time < ?
    ORDER BY transaction_time DESC
    LIMIT 1;
    """

    cursor = conn.execute(previous_query, (account_id, transaction_time))

    previous_row = cursor.fetchone()

    if previous_row is None:
        return {
            "signal_id": "S05",
            "signal_name": "dormant_account_reactivation",
            "feature_name": "days_since_previous_transaction",
            "feature_value": None,
            "threshold": threshold_days,
            "triggered": False,
        }

    previous_transaction_time = previous_row[0]

    current_dt = datetime.fromisoformat(transaction_time)
    previous_dt = datetime.fromisoformat(previous_transaction_time)

    days_since_previous = (current_dt - previous_dt).days

    triggered = days_since_previous > threshold_days

    return {
        "signal_id": "S05",
        "signal_name": "dormant_account_reactivation",
        "feature_name": "days_since_previous_transaction",
        "feature_value": days_since_previous,
        "threshold": threshold_days,
        "triggered": triggered,
    }


# S06: Repeated Counterparty
# used to calculate how many transactions to the same counterparties in recent 24 hours
def calculate_repeated_counterparty_signal(
    conn, transaction_id, window_hours=24, threshold_count=4
):
    query = """
    SELECT
        account_id,
        merchant_id,
        transaction_time
    FROM transactions
    WHERE transaction_id = ?;
    """

    cursor = conn.execute(query, (transaction_id,))
    row = cursor.fetchone()

    if row is None:
        return None

    account_id = row[0]
    merchant_id = row[1]
    transaction_time = row[2]

    transaction_dt = datetime.fromisoformat(transaction_time)
    window_start_dt = transaction_dt - timedelta(hours=window_hours)

    count_query = """
    SELECT COUNT(*)
    FROM transactions
    WHERE account_id = ?
      AND merchant_id = ?
      AND transaction_time >= ?
      AND transaction_time <= ?;
    """

    cursor = conn.execute(
        count_query,
        (
            account_id,
            merchant_id,
            window_start_dt.isoformat(sep=" "),
            transaction_dt.isoformat(sep=" "),
        ),
    )

    same_merchant_count = cursor.fetchone()[0]

    triggered = same_merchant_count >= threshold_count

    return {
        "signal_id": "S06",
        "signal_name": "repeated_counterparty",
        "feature_name": "same_merchant_transaction_count_last_24h",
        "feature_value": same_merchant_count,
        "threshold": threshold_count,
        "window_hours": window_hours,
        "triggered": triggered,
    }


# S07: Repeated Failed Payments
# used to calculate how many failure transactions happened in past 30 minutes
def calculate_failed_payment_signal(
    conn, transaction_id, window_minutes=30, threshold_count=3
):
    query = """
    SELECT
        account_id,
        transaction_time
    FROM transactions
    WHERE transaction_id = ?;
    """

    cursor = conn.execute(query, (transaction_id,))
    row = cursor.fetchone()

    if row is None:
        return None

    account_id = row[0]
    transaction_time = row[1]

    transaction_dt = datetime.fromisoformat(transaction_time)
    window_start_dt = transaction_dt - timedelta(minutes=window_minutes)

    count_query = """
    SELECT COUNT(*)
    FROM transactions
    WHERE account_id = ?
      AND status IN ('failed', 'declined')
      AND transaction_time >= ?
      AND transaction_time <= ?;
    """

    cursor = conn.execute(
        count_query,
        (
            account_id,
            window_start_dt.isoformat(sep=" "),
            transaction_dt.isoformat(sep=" "),
        ),
    )

    failed_count = cursor.fetchone()[0]

    triggered = failed_count >= threshold_count

    return {
        "signal_id": "S07",
        "signal_name": "repeated_failed_payments",
        "feature_name": "failed_transaction_count_last_30m",
        "feature_value": failed_count,
        "threshold": threshold_count,
        "window_minutes": window_minutes,
        "triggered": triggered,
    }


# S08: Prior Chargebacks
# calculate how many chargbacks happened for a account in last 180 days
def calculate_prior_chargeback_signal(
    conn, transaction_id, window_days=180, threshold_count=2
):
    query = """
    SELECT
        account_id,
        transaction_time
    FROM transactions
    WHERE transaction_id = ?;
    """

    cursor = conn.execute(query, (transaction_id,))
    row = cursor.fetchone()

    if row is None:
        return None

    account_id = row[0]
    transaction_time = row[1]

    transaction_dt = datetime.fromisoformat(transaction_time)
    window_start_dt = transaction_dt - timedelta(days=window_days)

    count_query = """
    SELECT COUNT(*)
    FROM chargebacks
    WHERE account_id = ?
      AND chargeback_date >= ?
      AND chargeback_date <= ?;
    """

    cursor = conn.execute(
        count_query,
        (
            account_id,
            window_start_dt.isoformat(sep=" "),
            transaction_dt.isoformat(sep=" "),
        ),
    )

    chargeback_count = cursor.fetchone()[0]

    triggered = chargeback_count >= threshold_count

    return {
        "signal_id": "S08",
        "signal_name": "prior_chargebacks",
        "feature_name": "chargeback_count_last_180d",
        "feature_value": chargeback_count,
        "threshold": threshold_count,
        "window_days": window_days,
        "triggered": triggered,
    }


# overview
def calculate_all_risk_signals(conn, transaction_id):
    account_query = """
    SELECT account_id
    FROM transactions
    WHERE transaction_id = ?;
    """

    cursor = conn.execute(account_query, (transaction_id,))
    row = cursor.fetchone()

    if row is None:
        return None

    account_id = row["account_id"]

    signals = [
        calculate_account_age_signal(conn, transaction_id),
        calculate_high_value_signal(conn, transaction_id),
        calculate_velocity_signal(conn, transaction_id),
        calculate_new_device_signal(conn, transaction_id),
        calculate_dormant_account_signal(conn, transaction_id),
        calculate_repeated_counterparty_signal(conn, transaction_id),
        calculate_failed_payment_signal(conn, transaction_id),
        calculate_prior_chargeback_signal(conn, transaction_id),
    ]

    valid_signals = [s for s in signals if s is not None]

    triggered_count = sum(1 for signal in valid_signals if signal["triggered"])

    return {
        "transaction_id": transaction_id,
        "account_id": account_id,
        "triggered_signal_count": triggered_count,
        "signals": valid_signals,
    }


# test
from database import create_connection

if __name__ == "__main__":
    conn = create_connection("data/fraud.db")

    # result_1 = calculate_account_age_signal(conn, "TXN_010")
    # print(result_1)
    # result_2 = calculate_account_age_signal(conn, "TXN_001")
    # print(result_2)

    # print(calculate_high_value_signal(conn, "TXN_010"))
    # print(calculate_high_value_signal(conn, "TXN_001"))

    # print(calculate_velocity_signal(conn, "TXN_010"))
    # print(calculate_velocity_signal(conn, "TXN_001"))

    # print(calculate_new_device_signal(conn, "TXN_010"))
    # print(calculate_new_device_signal(conn, "TXN_001"))

    # print(calculate_dormant_account_signal(conn, "TXN_012"))
    # print(calculate_dormant_account_signal(conn, "TXN_010"))

    # print(calculate_repeated_counterparty_signal(conn, "TXN_010"))
    # print(calculate_repeated_counterparty_signal(conn, "TXN_001"))

    # print(calculate_failed_payment_signal(conn, "TXN_021"))

    # print(calculate_prior_chargeback_signal(conn, "TXN_017"))

    print(calculate_all_risk_signals(conn, "TXN_012"))  # dormant account
    print(calculate_all_risk_signals(conn, "TXN_017"))  # prior chargebacks

    conn.close()
