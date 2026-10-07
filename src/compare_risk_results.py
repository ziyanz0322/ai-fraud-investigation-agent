import csv
import sqlite3
from pathlib import Path

from src.risk_engine import calculate_all_risk_signals


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "synthetic"
CSV_PATH = DATA_DIR / "snowflake_risk_results.csv"
DB_PATH = PROJECT_ROOT / "data" / "fraud_synthetic.db"
REPORT_PATH = DATA_DIR / "risk_comparison_differences.csv"

SIGNAL_IDS = [f"S{i:02d}" for i in range(1, 9)]
REPORT_COLUMNS = [
    "transaction_id",
    "field",
    "v1_value",
    "snowflake_value",
]


def parse_boolean(value):
    normalized = value.strip().lower()

    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False

    raise ValueError(f"Invalid boolean value: {value!r}")


def main():
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {
            "transaction_id",
            "triggered_signal_count",
            *SIGNAL_IDS,
        }

        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Missing CSV columns. Found: {reader.fieldnames}")

        exported = {}

        for row in reader:
            transaction_id = row["transaction_id"]

            if not transaction_id:
                raise ValueError("CSV contains an empty transaction ID.")
            if transaction_id in exported:
                raise ValueError(f"Duplicate CSV transaction ID: {transaction_id}")

            exported[transaction_id] = {
                **{
                    signal_id: parse_boolean(row[signal_id]) for signal_id in SIGNAL_IDS
                },
                "triggered_signal_count": int(row["triggered_signal_count"]),
            }

    conn = sqlite3.connect(
        DB_PATH.resolve().as_uri() + "?mode=ro",
        uri=True,
    )
    conn.row_factory = sqlite3.Row

    differences = []

    def record(transaction_id, field, v1_value, snowflake_value):
        differences.append(
            {
                "transaction_id": transaction_id,
                "field": field,
                "v1_value": v1_value,
                "snowflake_value": snowflake_value,
            }
        )

    try:
        local_ids = {
            row["transaction_id"]
            for row in conn.execute("SELECT transaction_id FROM transactions")
        }
        exported_ids = set(exported)

        print(f"SQLite transactions: {len(local_ids)}", flush=True)
        print(f"Snowflake CSV transactions: {len(exported_ids)}", flush=True)

        for transaction_id in sorted(local_ids - exported_ids):
            record(transaction_id, "presence", "present", "missing")

        for transaction_id in sorted(exported_ids - local_ids):
            record(transaction_id, "presence", "missing", "present")

        common_ids = sorted(local_ids & exported_ids)

        for index, transaction_id in enumerate(common_ids, start=1):
            result = calculate_all_risk_signals(conn, transaction_id)

            if result is None:
                raise ValueError(f"No V1 result for transaction: {transaction_id}")

            signals = result["signals"]

            if len(signals) != 8 or {s["signal_id"] for s in signals} != set(
                SIGNAL_IDS
            ):
                raise ValueError(f"Incomplete V1 signals for: {transaction_id}")

            local = {signal["signal_id"]: signal["triggered"] for signal in signals}
            local["triggered_signal_count"] = result["triggered_signal_count"]

            remote = exported[transaction_id]

            for field in SIGNAL_IDS + ["triggered_signal_count"]:
                if local[field] != remote[field]:
                    record(
                        transaction_id,
                        field,
                        local[field],
                        remote[field],
                    )

            if index % 500 == 0 or index == len(common_ids):
                print(
                    f"Compared {index}/{len(common_ids)} transactions",
                    flush=True,
                )

    finally:
        conn.close()

    with REPORT_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(differences)

    affected_ids = {row["transaction_id"] for row in differences}

    print(f"\nDifference records: {len(differences)}")
    print(f"Transactions with differences: {len(affected_ids)}")
    print(f"Difference report: {REPORT_PATH}")

    if len(local_ids) != 9000 or len(exported_ids) != 9000:
        raise SystemExit("FAIL: Expected 9,000 transactions in both sources.")

    if differences:
        raise SystemExit("FAIL: Review the difference report.")

    print("PASS: All 9,000 transactions match on eight signals and total count.")


if __name__ == "__main__":
    main()
