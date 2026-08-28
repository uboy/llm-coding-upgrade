import sys, os, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import TokenBucket

def test_initial_burst():
    b = TokenBucket(2, 5)
    assert b.tokens == 5

def test_allow_drains():
    b = TokenBucket(2, 3)
    assert b.allow() and b.allow() and b.allow()
    assert not b.allow()

def test_refill_capped():
    b = TokenBucket(5, 4)
    b.allow(4)
    b.tick(); b.tick()
    assert b.tokens == 4

def test_partial_cost():
    b = TokenBucket(0, 10)
    assert b.allow(7)
    assert not b.allow(7)
    assert b.allow(3)

def test_bad_cost():
    with pytest.raises(ValueError):
        TokenBucket(1, 5).allow(0)
