import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import flatten

def test_nested():
    assert flatten([1, [2, (3, 4)], 5]) == [1, 2, 3, 4, 5]

def test_strings_atomic():
    assert flatten(["ab", ["cd"]]) == ["ab", "cd"]

def test_self_reference():
    a = [1]
    a.append(a)
    assert flatten(a) == [1]

def test_transitive_cycle():
    a = [1]; b = [2, a]; a.append(b)
    assert flatten(b) == [2, 1]

def test_empty():
    assert flatten([]) == []
    assert flatten([[], [[]]]) == []
