# Case 09: Bug Fix — Bank Account Ledger (SWE-bench Style)

Fix ALL bugs in `bank_ledger.py` so that the test suite passes.

## Background

A simple bank ledger system that manages accounts, deposits, withdrawals, transfers, and calculates daily interest. The code has several subtle bugs that cause incorrect behavior under specific conditions.

## Provided Code

The file `bank_ledger.py` contains a `BankLedger` class with these methods:

```python
class BankLedger:
    def __init__(self):
        """Initialize empty ledger with accounts dict and transactions list."""
        
    def create_account(self, account_id: str, initial_balance_cents: int = 0) -> bool:
        """Create a new account. Returns False if account already exists."""
        
    def deposit(self, account_id: str, amount_cents: int) -> int:
        """Deposit funds. Returns new balance. Raises ValueError if account missing."""
        
    def withdraw(self, account_id: str, amount_cents: int) -> int:
        """Withdraw funds. Returns new balance. Raises ValueError if insufficient funds or account missing."""
        
    def transfer(self, from_id: str, to_id: str, amount_cents: int) -> bool:
        """Transfer between accounts. Returns True. Raises ValueError on any error."""
        
    def get_balance(self, account_id: str) -> int:
        """Return current balance in cents."""
        
    def apply_daily_interest(self, annual_rate_bps: int) -> dict:
        """Apply daily interest using annual rate in basis points (1 bps = 0.01%).
        Returns dict mapping account_id -> interest_earned_cents."""
        
    def get_transaction_count(self, account_id: str) -> int:
        """Return number of transactions involving this account."""
```

## Known Issues (Bug Reports)

The following issues have been reported. The model must identify and fix their root causes in the source code.

### Issue #1: Lost money during concurrent transfers
When two transfers involving the same account happen simultaneously, money occasionally disappears. Example:
```python
# Thread A: ledger.transfer("A", "B", 100)
# Thread B: ledger.transfer("A", "C", 50)
# Expected: A loses 150, B gains 100, C gains 50
# Actual: A sometimes loses only 100 or 50
```

### Issue #2: Transfer creates money out of thin air
When transferring from an account with insufficient funds, the debit fails but the credit succeeds. This creates money:
```python
# ledger.transfer("poor", "rich", 999999)
# "poor" has 100 cents, "rich" has 100 cents
# After: "poor" has -999899 cents, "rich" has 1000999 cents
```

### Issue #3: Interest rounding loses pennies
Over many days, interest calculations lose small amounts due to truncation:
```python
# Account with 10000 cents ($100.00), annual rate 500 bps (5%)
# Daily interest = 10000 * 500 / 10000 / 365 = 0.136... → 0 cents (Floored)
# Expected: should round to nearest cent: 0 cents OK
# But over 365 days: interest = 0, should be ~500 cents ($5.00)
# The issue is cumulative — small accounts earn zero interest forever
```

### Issue #4: get_transaction_count double-counts transfers for sender
For a transfer from Alice to Bob, `get_transaction_count("Alice")` returns 2 instead of 1:
```python
# ledger.create_account("Alice", 1000)
# ledger.create_account("Bob", 0)
# ledger.transfer("Alice", "Bob", 100)
# ledger.get_transaction_count("Alice") → returns 2 (wrong, should be 1)
# ledger.get_transaction_count("Bob") → returns 1 (correct)
```

### Issue #5: Consecutive create_account returns True on second call
Creating an account that already exists should return False, but it returns True:
```python
# ledger.create_account("X", 100) → True
# ledger.create_account("X", 200) → True (should be False)
# ledger.get_balance("X") → 200 (balance was overwritten, should still be 100)
```

## Constraints

- Fix the bugs in `bank_ledger.py` — do not rewrite from scratch.
- Change only the minimum code necessary to fix each bug.
- Preserve the existing public API (method signatures, exceptions).
- Use only the Python standard library.
- Do not modify tests.
- Keep the implementation in a single file: `bank_ledger.py`.
