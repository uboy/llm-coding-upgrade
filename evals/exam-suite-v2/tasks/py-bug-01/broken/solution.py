class RingBuffer:
    def __init__(self, cap):
        self.cap = cap
        self.buf = [None] * cap
        self.head = 0
        self.size = 0

    def push(self, x):
        self.buf[self.head] = x
        self.head = (self.head + 1) % (self.cap + 1)
        self.size += 1

    def snapshot(self):
        return [self.buf[(self.head + i) % self.cap] for i in range(self.size)]

    def last(self):
        return self.buf[self.head - 1]
