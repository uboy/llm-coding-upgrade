import sys, os, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import Cached

class Box:
    total = Cached("load")
    def __init__(self):
        self.calls = 0
    def load(self):
        self.calls += 1
        return self.calls * 10

def test_caches():
    b = Box()
    assert b.total == 10 and b.total == 10
    assert b.calls == 1

def test_invalidate():
    b = Box()
    _ = b.total
    Box.total.invalidate(b)
    assert b.total == 20
    assert b.calls == 2

def test_per_instance():
    b1, b2 = Box(), Box()
    _ = b1.total
    assert b2.total == 10
    assert b2.calls == 1

def test_readonly():
    with pytest.raises(AttributeError):
        Box().total = 5
