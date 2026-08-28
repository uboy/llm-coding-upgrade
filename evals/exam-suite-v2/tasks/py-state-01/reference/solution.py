class Elevator:
    def __init__(self, floors, capacity):
        self.floors, self.capacity = floors, capacity
        self.current, self.passengers = 1, 0
        self.doors_open = False
        self.targets = set()

    def call(self, floor):
        self.targets.add(floor)

    def step(self):
        if self.doors_open:
            raise RuntimeError("doors open")
        if not self.targets:
            return
        target = min(self.targets, key=lambda f: (abs(f - self.current), -f))
        if target > self.current:
            self.current += 1
        elif target < self.current:
            self.current -= 1
        if self.current == target:
            self.targets.discard(target)
            self.doors_open = True

    def board(self, n):
        if not self.doors_open:
            raise RuntimeError("doors closed")
        if self.passengers + n > self.capacity:
            raise ValueError("overload")
        self.passengers += n

    def open_door(self):
        self.doors_open = True

    def close_door(self):
        self.doors_open = False
