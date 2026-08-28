class TokenBucket:
    def __init__(self, rate, burst):
        self.rate, self.burst = rate, burst
        self._tokens = float(burst)

    @property
    def tokens(self):
        return self._tokens

    def tick(self):
        self._tokens = min(self.burst, self._tokens + self.rate)

    def allow(self, cost=1):
        if cost <= 0:
            raise ValueError("cost must be positive")
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False
