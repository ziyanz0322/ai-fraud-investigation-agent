from database import create_connection


def insert_users(conn, users):
    query = """
    INSERT INTO users (
        account_id,
        created_at,
        state,
        customer_segment,
        status
    )
    VALUES (?, ?, ?, ?, ?);
    """

    conn.executemany(query, users)  # insert multiple rows
    conn.commit()


def insert_transactions(conn, transactions):
    query = """
    INSERT INTO transactions (
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
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    conn.executemany(query, transactions)
    conn.commit()


def insert_devices(conn, devices):
    query = """
    INSERT INTO devices (
        account_id,
        device_id,
        first_seen_at,
        last_seen_at,
        device_type,
        trusted
    )
    VALUES (?, ?, ?, ?, ?, ?);
    """

    conn.executemany(query, devices)
    conn.commit()


def insert_chargebacks(conn, chargebacks):
    query = """
    INSERT INTO chargebacks (
        chargeback_id,
        transaction_id,
        account_id,
        chargeback_date,
        reason_code,
        amount,
        status
    )
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """

    conn.executemany(query, chargebacks)
    conn.commit()


def show_users(conn):
    cursor = conn.execute("""
        SELECT
            account_id,
            created_at,
            state,
            customer_segment,
            status
        FROM users
        ORDER BY account_id;
    """)

    rows = cursor.fetchall()

    for row in rows:
        print(row)


def show_transactions(conn):
    cursor = conn.execute("""
        SELECT
            transaction_id,
            account_id,
            transaction_time,
            amount,
            status
        FROM transactions
        ORDER BY transaction_time;
    """)

    for row in cursor.fetchall():
        print(row)


def show_devices(conn):
    cursor = conn.execute("""
        SELECT *
        FROM devices
        ORDER BY account_id;
    """)

    for row in cursor.fetchall():
        print(row)


def show_chargebacks(conn):
    cursor = conn.execute("""
        SELECT *
        FROM chargebacks
        ORDER BY chargeback_date;
    """)

    for row in cursor.fetchall():
        print(row)


if __name__ == "__main__":
    conn = create_connection("data/fraud.db")

    # users = [
    #     ("ACC_001", "2024-01-15 10:00:00", "CA", "standard", "active"),
    #     ("ACC_002", "2023-06-20 09:30:00", "NY", "premium", "active"),
    #     ("ACC_003", "2026-09-10 14:20:00", "TX", "standard", "active"),
    #     ("ACC_004", "2022-11-05 08:45:00", "FL", "standard", "active"),
    #     ("ACC_005", "2021-03-18 16:10:00", "CA", "premium", "active"),
    #     ("ACC_006", "2024-07-22 11:15:00", "IL", "standard", "active"),
    #     ("ACC_007", "2025-02-10 13:40:00", "WA", "standard", "active"),
    #     ("ACC_008", "2026-09-22 17:05:00", "CA", "standard", "active"),
    #     ("ACC_009", "2020-08-30 09:00:00", "NY", "premium", "active"),
    #     ("ACC_010", "2023-12-12 15:25:00", "TX", "standard", "active"),
    # ]

    transactions = [
        #     (
        #         "TXN_001",
        #         "ACC_001",
        #         "2026-09-20 10:00:00",
        #         85.00,
        #         "purchase",
        #         "MER_001",
        #         "DEV_001",
        #         "approved",
        #         "CA",
        #         "mobile",
        #     ),
        #     (
        #         "TXN_002",
        #         "ACC_001",
        #         "2026-09-21 14:20:00",
        #         120.00,
        #         "purchase",
        #         "MER_002",
        #         "DEV_001",
        #         "approved",
        #         "CA",
        #         "mobile",
        #     ),
        #     (
        #         "TXN_003",
        #         "ACC_002",
        #         "2026-09-18 11:15:00",
        #         4200.00,
        #         "purchase",
        #         "MER_003",
        #         "DEV_002",
        #         "approved",
        #         "NY",
        #         "web",
        #     ),
        #     (
        #         "TXN_004",
        #         "ACC_002",
        #         "2026-09-24 16:40:00",
        #         5800.00,
        #         "purchase",
        #         "MER_004",
        #         "DEV_002",
        #         "approved",
        #         "NY",
        #         "web",
        #     ),
        #     (
        #         "TXN_005",
        #         "ACC_003",
        #         "2026-09-25 09:01:00",
        #         200.00,
        #         "purchase",
        #         "MER_005",
        #         "DEV_003",
        #         "approved",
        #         "TX",
        #         "mobile",
        #     ),
        #     (
        #         "TXN_006",
        #         "ACC_003",
        #         "2026-09-25 09:04:00",
        #         450.00,
        #         "purchase",
        #         "MER_005",
        #         "DEV_003",
        #         "approved",
        #         "TX",
        #         "mobile",
        #     ),
        #     (
        #         "TXN_007",
        #         "ACC_003",
        #         "2026-09-25 09:07:00",
        #         700.00,
        #         "purchase",
        #         "MER_005",
        #         "DEV_003",
        #         "approved",
        #         "TX",
        #         "mobile",
        #     ),
        #     (
        #         "TXN_008",
        #         "ACC_003",
        #         "2026-09-25 09:10:00",
        #         900.00,
        #         "purchase",
        #         "MER_005",
        #         "DEV_003",
        #         "approved",
        #         "TX",
        #         "mobile",
        #     ),
        #     (
        #         "TXN_009",
        #         "ACC_003",
        #         "2026-09-25 09:13:00",
        #         1200.00,
        #         "purchase",
        #         "MER_005",
        #         "DEV_003",
        #         "approved",
        #         "TX",
        #         "mobile",
        #     ),
        #     (
        #         "TXN_010",
        #         "ACC_003",
        #         "2026-09-25 09:15:00",
        #         4800.00,
        #         "purchase",
        #         "MER_005",
        #         "DEV_003",
        #         "approved",
        #         "TX",
        #         "mobile",
        #     ),
        #     (
        #         "TXN_011",
        #         "ACC_004",
        #         "2025-05-01 12:00:00",
        #         45.00,
        #         "purchase",
        #         "MER_006",
        #         "DEV_004",
        #         "approved",
        #         "FL",
        #         "mobile",
        #     ),
        #     (
        #         "TXN_012",
        #         "ACC_004",
        #         "2026-09-27 18:30:00",
        #         950.00,
        #         "purchase",
        #         "MER_007",
        #         "DEV_004",
        #         "approved",
        #         "FL",
        #         "mobile",
        #     ),
        # (
        #     "TXN_013",
        #     "ACC_009",
        #     "2026-05-10 13:20:00",
        #     320.00,
        #     "purchase",
        #     "MER_010",
        #     "DEV_009",
        #     "approved",
        #     "NY",
        #     "mobile",
        # ),
        # (
        #     "TXN_014",
        #     "ACC_009",
        #     "2026-06-18 15:40:00",
        #     410.00,
        #     "purchase",
        #     "MER_011",
        #     "DEV_009",
        #     "approved",
        #     "NY",
        #     "mobile",
        # ),
        # (
        #     "TXN_015",
        #     "ACC_009",
        #     "2026-07-22 11:10:00",
        #     285.00,
        #     "purchase",
        #     "MER_012",
        #     "DEV_009",
        #     "approved",
        #     "NY",
        #     "mobile",
        # ),
        # (
        #     "TXN_016",
        #     "ACC_009",
        #     "2026-08-30 17:25:00",
        #     530.00,
        #     "purchase",
        #     "MER_013",
        #     "DEV_009",
        #     "approved",
        #     "NY",
        #     "mobile",
        # ),
        # (
        #     "TXN_017",
        #     "ACC_009",
        #     "2026-09-26 19:05:00",
        #     750.00,
        #     "purchase",
        #     "MER_014",
        #     "DEV_009",
        #     "approved",
        #     "NY",
        #     "mobile",
        # ),
        (
            "TXN_018",
            "ACC_008",
            "2026-09-28 10:00:00",
            900.00,
            "purchase",
            "MER_020",
            "DEV_008",
            "declined",
            "CA",
            "mobile",
        ),
        (
            "TXN_019",
            "ACC_008",
            "2026-09-28 10:05:00",
            900.00,
            "purchase",
            "MER_020",
            "DEV_008",
            "failed",
            "CA",
            "mobile",
        ),
        (
            "TXN_020",
            "ACC_008",
            "2026-09-28 10:10:00",
            900.00,
            "purchase",
            "MER_020",
            "DEV_008",
            "declined",
            "CA",
            "mobile",
        ),
        (
            "TXN_021",
            "ACC_008",
            "2026-09-28 10:15:00",
            900.00,
            "purchase",
            "MER_020",
            "DEV_008",
            "approved",
            "CA",
            "mobile",
        ),
    ]

    devices = [
        # (
        #     "ACC_001",
        #     "DEV_001",
        #     "2024-01-15 10:00:00",
        #     "2026-09-21 14:20:00",
        #     "mobile",
        #     1,
        # ),
        # (
        #     "ACC_002",
        #     "DEV_002",
        #     "2023-06-20 09:30:00",
        #     "2026-09-24 16:40:00",
        #     "desktop",
        #     1,
        # ),
        # (
        #     "ACC_003",
        #     "DEV_003",
        #     "2026-09-25 08:55:00",
        #     "2026-09-25 09:15:00",
        #     "mobile",
        #     0,
        # ),
        # (
        #     "ACC_004",
        #     "DEV_004",
        #     "2025-05-01 12:00:00",
        #     "2026-09-27 18:30:00",
        #     "mobile",
        #     1,
        # ),
        #     (
        #         "ACC_009",
        #         "DEV_009",
        #         "2024-02-10 08:00:00",
        #         "2026-09-26 19:05:00",
        #         "mobile",
        #         1,
        #     ),
        # ]
        # chargebacks = [
        #     (
        #         "CB_001",
        #         "TXN_013",
        #         "ACC_009",
        #         "2026-05-18 09:00:00",
        #         "fraud",
        #         320.00,
        #         "accepted",
        #     ),
        #     (
        #         "CB_002",
        #         "TXN_014",
        #         "ACC_009",
        #         "2026-06-27 10:15:00",
        #         "not_received",
        #         410.00,
        #         "accepted",
        #     ),
        #     (
        #         "CB_003",
        #         "TXN_015",
        #         "ACC_009",
        #         "2026-08-01 14:30:00",
        #         "fraud",
        #         285.00,
        #         "accepted",
        #     ),
        #     (
        #         "CB_004",
        #         "TXN_016",
        #         "ACC_009",
        #         "2026-09-08 16:45:00",
        #         "not_received",
        #         530.00,
        #         "accepted",
        #     ),
    ]
    # insert_users(conn, users)
    # insert_transactions(conn, transactions)
    # insert_devices(conn, devices)
    # insert_chargebacks(conn, chargebacks)
    # show_users(conn)
    show_transactions(conn)
    # show_devices(conn)
    # show_chargebacks(conn)

    conn.close()
