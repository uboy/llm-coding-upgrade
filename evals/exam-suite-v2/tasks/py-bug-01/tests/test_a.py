import sys, os, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import RingBuffer

def test_underfill():
    r = RingBuffer(3)
    r.push(1); r.push(2)
    assert r.snapshot() == [1, 2]

def test_wrap():
    r = RingBuffer(3)
    for x in [1, 2, 3, 4]:
        r.push(x)
    assert r.snapshot() == [2, 3, 4]
    assert r.last() == 4

def test_double_wrap():
    r = RingBuffer(2)
    for x in [1, 2, 3, 4, 5]:
        r.push(x)
    assert r.snapshot() == [4, 5]
    assert r.last() == 5

def test_last_on_empty():
    with pytest.raises(IndexError):
        RingBuffer(2).last()
