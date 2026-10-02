import sqlite3


def create_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(conn):
    users_table = """
    CREATE TABLE IF NOT EXISTS users (
        account_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        state TEXT NOT NULL,
        customer_segment TEXT NOT NULL,
        status TEXT NOT NULL
    );
    """

    transactions_table = """
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id TEXT PRIMARY KEY,
        account_id TEXT NOT NULL,
        transaction_time TEXT NOT NULL,
        amount REAL NOT NULL,
        transaction_type TEXT NOT NULL,
        merchant_id TEXT NOT NULL,
        device_id TEXT NOT NULL,
        status TEXT NOT NULL,
        state TEXT NOT NULL,
        channel TEXT NOT NULL,

        FOREIGN KEY (account_id) REFERENCES users(account_id)
    );
    """

    devices_table = """
    CREATE TABLE IF NOT EXISTS devices (
        account_id TEXT NOT NULL,
        device_id TEXT NOT NULL,
        first_seen_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        device_type TEXT NOT NULL,
        trusted INTEGER NOT NULL,

        PRIMARY KEY (account_id, device_id),
        FOREIGN KEY (account_id) REFERENCES users(account_id)
    );
    """

    chargebacks_table = """
    CREATE TABLE IF NOT EXISTS chargebacks (
        chargeback_id TEXT PRIMARY KEY,
        transaction_id TEXT NOT NULL,
        account_id TEXT NOT NULL,
        chargeback_date TEXT NOT NULL,
        reason_code TEXT NOT NULL,
        amount REAL NOT NULL,
        status TEXT NOT NULL,

        FOREIGN KEY (account_id) REFERENCES users(account_id),
        FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id)
    );
    """

    conn.execute(users_table)
    conn.execute(transactions_table)
    conn.execute(devices_table)
    conn.execute(chargebacks_table)
    conn.commit()


if __name__ == "__main__":
    conn = create_connection("data/fraud.db")
    create_tables(conn)
    conn.close()
