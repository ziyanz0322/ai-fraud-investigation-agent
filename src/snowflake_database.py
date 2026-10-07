import os
from pathlib import Path

import snowflake.connector
from snowflake.connector import DictCursor


def create_snowflake_connection():
    passphrase = os.getenv("DBT_ENV_SECRET_SNOWFLAKE_KEY_PASSPHRASE")

    if not passphrase:
        raise ValueError("Missing DBT_ENV_SECRET_SNOWFLAKE_KEY_PASSPHRASE.")

    key_path = Path.home() / ".dbt" / "keys" / "fraud_snowflake_v2.p8"

    if not key_path.is_file():
        raise FileNotFoundError(f"Private key not found: {key_path}")

    return snowflake.connector.connect(
        account="FBBCQWX-FA73675",
        user="ZIYANZ0322",
        authenticator="SNOWFLAKE_JWT",
        private_key_file=str(key_path),
        private_key_file_pwd=passphrase,
        role="SYSADMIN",
        warehouse="FRAUD_WH",
        database="FRAUD_DB",
        schema="DBT_DEV",
        login_timeout=30,
        session_parameters={
            "TIMEZONE": "UTC",
            "QUERY_TAG": "fraud_investigation_agent",
            "STATEMENT_TIMEOUT_IN_SECONDS": 60,
        },
    )


if __name__ == "__main__":
    print("Connecting to Snowflake...", flush=True)
    conn = create_snowflake_connection()

    try:
        with conn.cursor(DictCursor) as cursor:
            cursor.execute(
                """
                SELECT
                    TRANSACTION_ID,
                    ACCOUNT_ID,
                    AMOUNT,
                    TRIGGERED_SIGNAL_COUNT
                FROM FRAUD_DB.DBT_DEV.FCT_TRANSACTION_RISK
                WHERE TRANSACTION_ID = %s
                """,
                ("TXN_010",),
            )

            row = cursor.fetchone()

            if row is None:
                raise ValueError("Transaction not found: TXN_010")

            print(f"Transaction: {row['TRANSACTION_ID']}")
            print(f"Account: {row['ACCOUNT_ID']}")
            print(f"Amount: {row['AMOUNT']}")
            print(f"Triggered signals: {row['TRIGGERED_SIGNAL_COUNT']}")
    finally:
        conn.close()
