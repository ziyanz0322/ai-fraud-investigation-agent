import csv
from pathlib import Path

from src.database import create_connection, create_tables


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_DIR = PROJECT_ROOT / "data" / "synthetic"
DB_PATH = PROJECT_ROOT / "data" / "fraud_synthetic.db"

# Load referenced tables before the tables that depend on them.
TABLE_COUNTS = {
    "users": 500,
    "devices": 700,
    "transactions": 9000,
    "chargebacks": 100,
}


def load_csv(conn, table_name, expected_count):
    csv_path = CSV_DIR / f"{table_name}.csv"

    # Read database columns to validate the CSV schema.
    columns = [row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})")]

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames != columns:
            raise ValueError(
                f"{table_name}: CSV columns or column order do not "
                f"match the database schema.\n"
                f"Expected: {columns}\n"
                f"Actual: {reader.fieldnames}"
            )

        rows = []
        for line_number, row in enumerate(reader, start=2):
            if None in row or any(row[column] in (None, "") for column in columns):
                raise ValueError(
                    f"{table_name}: Missing or extra fields on line {line_number}."
                )

            rows.append(tuple(row[column] for column in columns))

    if len(rows) != expected_count:
        raise ValueError(
            f"{table_name}: Expected {expected_count} rows, but found {len(rows)}."
        )

    placeholders = ", ".join("?" for _ in columns)
    column_names = ", ".join(columns)

    conn.executemany(
        f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})",
        rows,
    )


def main():
    conn = create_connection(str(DB_PATH))

    try:
        create_tables(conn)

        # Prevent duplicate imports or overwriting existing data.
        for table_name in TABLE_COUNTS:
            count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

            if count:
                raise ValueError(
                    f"{table_name} already contains {count} rows. "
                    "Import stopped. Check whether this database "
                    "has already been populated."
                )

        # Commit all four tables together.
        # Roll back all inserts if any step fails.
        with conn:
            for table_name, expected_count in TABLE_COUNTS.items():
                load_csv(conn, table_name, expected_count)

            if conn.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("Foreign key validation failed.")

            # The schema has no transaction-to-device foreign key,
            # so validate device ownership explicitly.
            missing_devices = conn.execute("""
                SELECT COUNT(*)
                FROM transactions AS t
                LEFT JOIN devices AS d
                    ON t.account_id = d.account_id
                    AND t.device_id = d.device_id
                WHERE d.device_id IS NULL
            """).fetchone()[0]

            if missing_devices:
                raise ValueError(
                    f"{missing_devices} transactions have no "
                    "matching device for their account."
                )

        print(f"Import completed successfully: {DB_PATH}")

        for table_name in TABLE_COUNTS:
            count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            print(f"{table_name}: {count}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
