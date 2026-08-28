class RingBuffer:
    def __init__(self, cap):
        self.cap = cap
        self.buf = [None] * cap
        self.head = 0
        self.size = 0

    def push(self, x):
        self.buf[self.head] = x
        self.head = (self.head + 1) % self.cap
        self.size = min(self.size + 1, self.cap)

    def snapshot(self):
        start = (self.head - self.size) % self.cap
        return [self.buf[(start + i) % self.cap] for i in range(self.size)]

    def last(self):
        if self.size == 0:
            raise IndexError("empty")
        return self.buf[(self.head - 1) % self.cap]
