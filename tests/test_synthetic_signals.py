import unittest
from pathlib import Path

from src.database import create_connection
from src.risk_engine import calculate_all_risk_signals
from src.tools import (
    get_target_transaction,
    get_transaction_history,
    get_chargeback_history,
)

import sqlite3

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "fraud_synthetic.db"


class SyntheticSignalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DB_PATH.is_file():
            raise FileNotFoundError(f"Database not found: {DB_PATH}")

        cls.conn = create_connection(str(DB_PATH))
        cls.conn.execute("PRAGMA query_only = ON;")

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_expected_signals(self):
        expected = {
            "TXN_001": set(),
            "TXN_010": {"S01", "S02", "S03", "S04", "S06", "S07"},
            "TXN_004": {"S02"},
            "TXN_017": {"S08"},
        }

        for transaction_id, expected_ids in expected.items():
            with self.subTest(transaction_id=transaction_id):
                result = calculate_all_risk_signals(self.conn, transaction_id)

                self.assertIsNotNone(result)
                self.assertEqual(
                    {signal["signal_id"] for signal in result["signals"]},
                    {f"S{i:02d}" for i in range(1, 9)},
                )

                triggered_ids = {
                    signal["signal_id"]
                    for signal in result["signals"]
                    if signal["triggered"]
                }

                self.assertEqual(triggered_ids, expected_ids)
                self.assertEqual(result["triggered_signal_count"], len(expected_ids))

    def test_suspicious_sequence_counts(self):
        result = calculate_all_risk_signals(self.conn, "TXN_010")
        signals = {signal["signal_id"]: signal for signal in result["signals"]}

        self.assertEqual(signals["S03"]["feature_value"], 6)
        self.assertEqual(signals["S06"]["feature_value"], 6)
        self.assertEqual(signals["S07"]["feature_value"], 3)

    def test_history_is_strictly_before_target(self):
        from datetime import datetime

        expected_counts = {
            "TXN_001": (39, 0),
            "TXN_010": (11, 0),
            "TXN_004": (59, 0),
            "TXN_017": (34, 6),
        }

        for transaction_id, counts in expected_counts.items():
            with self.subTest(transaction_id=transaction_id):
                target = get_target_transaction(self.conn, transaction_id)
                cutoff = datetime.fromisoformat(target["transaction_time"])

                history = get_transaction_history(self.conn, transaction_id)
                chargebacks = get_chargeback_history(self.conn, transaction_id)

                self.assertEqual(len(history), counts[0])
                self.assertEqual(len(chargebacks), counts[1])

                for row in history:
                    self.assertNotEqual(row["transaction_id"], transaction_id)
                    self.assertLess(
                        datetime.fromisoformat(row["transaction_time"]),
                        cutoff,
                    )

                for row in chargebacks:
                    self.assertLess(
                        datetime.fromisoformat(row["chargeback_date"]),
                        cutoff,
                    )

    def test_future_records_do_not_change_past_investigation(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        self.conn.backup(conn)
        conn.execute("PRAGMA foreign_keys = ON;")

        transaction_id = "TXN_001"

        try:
            signals_before = calculate_all_risk_signals(conn, transaction_id)
            history_before = get_transaction_history(conn, transaction_id)
            chargebacks_before = get_chargeback_history(conn, transaction_id)

            # Add a declined attempt one minute after the target.
            conn.execute(
                """
                INSERT INTO transactions (
                    transaction_id, account_id, transaction_time,
                    amount, transaction_type, merchant_id,
                    device_id, status, state, channel
                )
                SELECT
                    'TEST_FUTURE_TXN', account_id,
                    strftime(
                        '%Y-%m-%dT%H:%M:%SZ',
                        transaction_time,
                        '+1 minute'
                    ),
                    9999.00, transaction_type, merchant_id,
                    device_id, 'declined', state, channel
                FROM transactions
                WHERE transaction_id = ?;
                """,
                (transaction_id,),
            )

            # Add a dispute reported one day after the target.
            conn.execute(
                """
                INSERT INTO chargebacks (
                    chargeback_id, transaction_id, account_id,
                    chargeback_date, reason_code, amount, status
                )
                SELECT
                    'TEST_FUTURE_CB', transaction_id, account_id,
                    strftime(
                        '%Y-%m-%dT%H:%M:%SZ',
                        transaction_time,
                        '+1 day'
                    ),
                    'unauthorized', amount, 'open'
                FROM transactions
                WHERE transaction_id = ?;
                """,
                (transaction_id,),
            )

            self.assertEqual(
                calculate_all_risk_signals(conn, transaction_id),
                signals_before,
            )
            self.assertEqual(
                get_transaction_history(conn, transaction_id),
                history_before,
            )
            self.assertEqual(
                get_chargeback_history(conn, transaction_id),
                chargebacks_before,
            )
        finally:
            conn.close()

    def test_velocity_threshold_boundary(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        self.conn.backup(conn)

        try:
            from src.risk_engine import calculate_velocity_signal

            # TXN_010 has six attempts in its 30-minute window.
            target = get_target_transaction(conn, "TXN_010")

            prior_attempts = conn.execute(
                """
                SELECT transaction_id
                FROM transactions
                WHERE account_id = ?
                  AND julianday(transaction_time)
                      >= julianday(?, '-30 minutes')
                  AND julianday(transaction_time) < julianday(?)
                ORDER BY julianday(transaction_time), transaction_id;
                """,
                (
                    target["account_id"],
                    target["transaction_time"],
                    target["transaction_time"],
                ),
            ).fetchall()

            self.assertEqual(len(prior_attempts), 5)

            # Remove one attempt: five remain, including the target.
            conn.execute(
                "DELETE FROM transactions WHERE transaction_id = ?",
                (prior_attempts[0]["transaction_id"],),
            )

            result = calculate_velocity_signal(conn, "TXN_010")
            self.assertEqual(result["feature_value"], 5)
            self.assertTrue(result["triggered"])

            # Remove another attempt: four remain.
            conn.execute(
                "DELETE FROM transactions WHERE transaction_id = ?",
                (prior_attempts[1]["transaction_id"],),
            )

            result = calculate_velocity_signal(conn, "TXN_010")
            self.assertEqual(result["feature_value"], 4)
            self.assertFalse(result["triggered"])
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
