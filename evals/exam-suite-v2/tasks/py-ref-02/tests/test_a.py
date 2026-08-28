import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import vend, COIN_VALUES

def test_ok():
    assert vend([5, 2, 2], 9) == "ok"

def test_short():
    assert vend([1], 5) == "need:4"

def test_exact():
    assert vend([10], 10) == "ok"

def test_empty():
    assert vend([], 3) == "need:3"

def test_coin_values():
    assert sorted(COIN_VALUES) == [1, 2, 5, 10]
