import threading


class BankLedger:
    def __init__(self):
        self.accounts = {}
        self.transactions = []
        self._lock = threading.Lock()

    def create_account(self, account_id, initial_balance_cents=0):
        if account_id in self.accounts:
            return False
        self.accounts[account_id] = initial_balance_cents
        return True

    def deposit(self, account_id, amount_cents):
        if amount_cents <= 0:
            raise ValueError("Deposit amount must be positive")
        if account_id not in self.accounts:
            raise ValueError(f"Account {account_id} not found")
        self.accounts[account_id] += amount_cents
        self.transactions.append(("deposit", account_id, amount_cents))
        return self.accounts[account_id]

    def withdraw(self, account_id, amount_cents):
        if amount_cents <= 0:
            raise ValueError("Withdraw amount must be positive")
        if account_id not in self.accounts:
            raise ValueError(f"Account {account_id} not found")
        if self.accounts[account_id] < amount_cents:
            raise ValueError("Insufficient funds")
        self.accounts[account_id] -= amount_cents
        self.transactions.append(("withdraw", account_id, amount_cents))
        return self.accounts[account_id]

    def transfer(self, from_id, to_id, amount_cents):
        if amount_cents <= 0:
            raise ValueError("Transfer amount must be positive")
        if from_id not in self.accounts:
            raise ValueError(f"Source account {from_id} not found")
        if to_id not in self.accounts:
            raise ValueError(f"Destination account {to_id} not found")
        self.accounts[from_id] -= amount_cents
        self.accounts[to_id] += amount_cents
        self.transactions.append(("transfer", from_id, to_id, amount_cents))
        return True

    def get_balance(self, account_id):
        if account_id not in self.accounts:
            raise ValueError(f"Account {account_id} not found")
        return self.accounts[account_id]

    def apply_daily_interest(self, annual_rate_bps):
        result = {}
        for acc_id in list(self.accounts.keys()):
            balance = self.accounts[acc_id]
            interest = balance * annual_rate_bps // 10000 // 365
            if interest > 0:
                self.accounts[acc_id] += interest
            result[acc_id] = interest
        return result

    def get_transaction_count(self, account_id):
        count = 0
        for txn in self.transactions:
            if txn[0] == "deposit" and txn[1] == account_id:
                count += 1
            elif txn[0] == "withdraw" and txn[1] == account_id:
                count += 1
            elif txn[0] == "transfer":
                if txn[1] == account_id:
                    count += 2
                if txn[2] == account_id:
                    count += 1
        return count
