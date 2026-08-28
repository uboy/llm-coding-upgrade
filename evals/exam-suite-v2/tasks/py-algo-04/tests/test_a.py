import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import min_window

def test_basic():
    assert min_window(["a","x","b","y","a","b"], ["a","b"]) == (4, 6)

def test_empty_required():
    assert min_window(["a"], []) == (0, 0)

def test_no_cover():
    assert min_window(["a","b"], ["a","c"]) is None

def test_tie_leftmost():
    assert min_window(["a","b","a","b"], ["a","b"]) == (0, 2)

def test_single():
    assert min_window(["z","q","z"], ["z"]) == (0, 1)
