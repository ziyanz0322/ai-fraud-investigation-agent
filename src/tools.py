from pathlib import Path

from src.database import create_connection
from src.risk_engine import calculate_all_risk_signals


def get_account_profile(conn, account_id):
    row = conn.execute(
        """
        SELECT *
        FROM users
        WHERE account_id = ?;
        """,
        (account_id,),
    ).fetchone()

    return dict(row) if row is not None else None


def get_target_transaction(conn, transaction_id):
    row = conn.execute(
        """
        SELECT *
        FROM transactions
        WHERE transaction_id = ?;
        """,
        (transaction_id,),
    ).fetchone()

    if row is None:
        raise ValueError(f"Transaction not found: {transaction_id}")

    return dict(row)


def get_transaction_history(conn, transaction_id):
    target = get_target_transaction(conn, transaction_id)

    rows = conn.execute(
        """
        SELECT
            transaction_id,
            transaction_time,
            amount,
            transaction_type,
            merchant_id,
            device_id,
            status,
            state,
            channel
        FROM transactions
        WHERE account_id = ?
          AND julianday(transaction_time) < julianday(?)
        ORDER BY julianday(transaction_time) DESC, transaction_id;
        """,
        (
            target["account_id"],
            target["transaction_time"],
        ),
    ).fetchall()

    return [dict(row) for row in rows]


def calculate_risk_signals(conn, transaction_id):
    return calculate_all_risk_signals(conn, transaction_id)


def get_chargeback_history(conn, transaction_id):
    target = get_target_transaction(conn, transaction_id)

    rows = conn.execute(
        """
        SELECT
            chargeback_id,
            transaction_id,
            chargeback_date,
            reason_code,
            amount
        FROM chargebacks
        WHERE account_id = ?
          AND julianday(chargeback_date) < julianday(?)
        ORDER BY julianday(chargeback_date) DESC, chargeback_id;
        """,
        (
            target["account_id"],
            target["transaction_time"],
        ),
    ).fetchall()

    # Resolution status is omitted because the schema does not
    # record when that status became known.
    return [dict(row) for row in rows]


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    db_path = project_root / "data" / "fraud_synthetic.db"

    if not db_path.is_file():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = create_connection(str(db_path))

    try:
        transaction_ids = [
            "TXN_001",
            "TXN_010",
            "TXN_004",
            "TXN_017",
        ]

        for transaction_id in transaction_ids:
            history = get_transaction_history(conn, transaction_id)
            chargebacks = get_chargeback_history(conn, transaction_id)

            assert all(row["transaction_id"] != transaction_id for row in history), (
                "Transaction history includes the target transaction."
            )

            print(f"\nTransaction: {transaction_id}")
            print(f"Prior transactions: {len(history)}")
            print(f"Prior chargebacks: {len(chargebacks)}")
    finally:
        conn.close()
