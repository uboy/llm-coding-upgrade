import unittest
import threading
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bank_ledger import BankLedger


class BankLedgerTests(unittest.TestCase):
    def setUp(self):
        self.ledger = BankLedger()

    # === Basic CRUD ===

    def test_create_account(self):
        self.assertTrue(self.ledger.create_account("alice", 1000))
        self.assertEqual(self.ledger.get_balance("alice"), 1000)

    def test_create_duplicate_account_returns_false(self):
        self.assertTrue(self.ledger.create_account("x", 100))
        self.assertFalse(self.ledger.create_account("x", 200))
        self.assertEqual(self.ledger.get_balance("x"), 100)

    def test_deposit_increases_balance(self):
        self.ledger.create_account("alice", 1000)
        new_balance = self.ledger.deposit("alice", 500)
        self.assertEqual(new_balance, 1500)
        self.assertEqual(self.ledger.get_balance("alice"), 1500)

    def test_deposit_missing_account_raises(self):
        with self.assertRaises(ValueError):
            self.ledger.deposit("nonexistent", 100)

    def test_withdraw_decreases_balance(self):
        self.ledger.create_account("alice", 1000)
        new_balance = self.ledger.withdraw("alice", 300)
        self.assertEqual(new_balance, 700)

    def test_withdraw_insufficient_funds_raises(self):
        self.ledger.create_account("alice", 100)
        with self.assertRaises(ValueError):
            self.ledger.withdraw("alice", 200)

    def test_withdraw_missing_account_raises(self):
        with self.assertRaises(ValueError):
            self.ledger.withdraw("nonexistent", 100)

    # === Transfers ===

    def test_transfer_moves_funds(self):
        self.ledger.create_account("alice", 1000)
        self.ledger.create_account("bob", 500)
        self.ledger.transfer("alice", "bob", 300)
        self.assertEqual(self.ledger.get_balance("alice"), 700)
        self.assertEqual(self.ledger.get_balance("bob"), 800)

    def test_transfer_insufficient_funds_raises(self):
        self.ledger.create_account("alice", 100)
        self.ledger.create_account("bob", 100)
        with self.assertRaises(ValueError):
            self.ledger.transfer("alice", "bob", 200)
        self.assertEqual(self.ledger.get_balance("alice"), 100)
        self.assertEqual(self.ledger.get_balance("bob"), 100)

    def test_transfer_missing_account_raises(self):
        self.ledger.create_account("alice", 1000)
        with self.assertRaises(ValueError):
            self.ledger.transfer("alice", "ghost", 100)

    # === Concurrency ===

    def test_concurrent_transfers_no_money_loss(self):
        self.ledger.create_account("alice", 10000)
        self.ledger.create_account("bob", 0)
        self.ledger.create_account("charlie", 0)

        n = 50
        barrier = threading.Barrier(3)
        errors = []

        def transfer_loop(from_id, to_id, amount):
            try:
                barrier.wait(timeout=5)
                for _ in range(n):
                    self.ledger.transfer(from_id, to_id, amount)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=transfer_loop, args=("alice", "bob", 10)),
            threading.Thread(target=transfer_loop, args=("alice", "charlie", 10)),
        ]
        for t in threads:
            t.start()
        barrier.wait(timeout=5)
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")
        total = (self.ledger.get_balance("alice") +
                 self.ledger.get_balance("bob") +
                 self.ledger.get_balance("charlie"))
        self.assertEqual(total, 10000,
                         "Money was lost or created during concurrent transfers")

    # === Interest ===

    def test_interest_rounding_is_accurate(self):
        self.ledger.create_account("save", 1000000)
        result = self.ledger.apply_daily_interest(500)
        interest = result.get("save", 0)
        self.assertGreaterEqual(interest, 136)
        self.assertLessEqual(interest, 140)

    def test_small_account_earns_interest(self):
        self.ledger.create_account("tiny", 200)
        result = self.ledger.apply_daily_interest(10000)
        interest = result.get("tiny", 0)
        self.assertGreater(
            interest, 0,
            "Small accounts should earn non-zero daily interest with proper rounding"
        )

    # === Transaction Counting ===

    def test_transfer_counts_as_one_transaction_for_sender(self):
        self.ledger.create_account("alice", 1000)
        self.ledger.create_account("bob", 0)
        self.ledger.transfer("alice", "bob", 100)
        self.assertEqual(self.ledger.get_transaction_count("alice"), 1)

    def test_transfer_counts_as_one_transaction_for_receiver(self):
        self.ledger.create_account("alice", 1000)
        self.ledger.create_account("bob", 0)
        self.ledger.transfer("alice", "bob", 100)
        self.assertEqual(self.ledger.get_transaction_count("bob"), 1)


if __name__ == "__main__":
    unittest.main()
