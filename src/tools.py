def get_account_profile(conn, account_id):
    query = """
    SELECT *
    FROM users
    WHERE account_id = ?;
    """

    cursor = conn.execute(query, (account_id,))
    row = cursor.fetchone()

    if row is None:
        return None
    return dict(row)


def get_transaction_history(conn, account_id):
    query = """
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
    ORDER BY transaction_time DESC;
    """

    cursor = conn.execute(query, (account_id,))
    rows = cursor.fetchall()

    return [dict(row) for row in rows]


from risk_engine import calculate_all_risk_signals


def calculate_risk_signals(conn, transaction_id):
    return calculate_all_risk_signals(conn, transaction_id)


def get_chargeback_history(conn, account_id):
    query = """
    SELECT
        chargeback_id,
        transaction_id,
        chargeback_date,
        reason_code,
        amount,
        status
    FROM chargebacks
    WHERE account_id = ?
    ORDER BY chargeback_date DESC;
    """

    cursor = conn.execute(query, (account_id,))
    rows = cursor.fetchall()

    return [dict(row) for row in rows]


# test
from database import create_connection

if __name__ == "__main__":
    conn = create_connection("data/fraud.db")

    # print(get_account_profile(conn, "ACC_003"))
    # print(get_transaction_history(conn, "ACC_003"))
    print(calculate_risk_signals(conn, "TXN_010"))
    conn.close()
