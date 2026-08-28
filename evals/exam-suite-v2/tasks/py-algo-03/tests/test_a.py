import sys, os, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import cooking_order

def test_chain():
    assert cooking_order({"b": ["a"], "a": []}) == ["a", "b"]

def test_lexicographic_minimal():
    assert cooking_order({"z": [], "a": [], "m": ["a"]}) == ["a", "m", "z"]

def test_diamond():
    got = cooking_order({"d": ["b", "c"], "b": ["a"], "c": ["a"], "a": []})
    assert got.index("a") < got.index("b") and got.index("a") < got.index("c")
    assert got.index("b") < got.index("d") and got.index("c") < got.index("d")

def test_cycle():
    with pytest.raises(ValueError):
        cooking_order({"a": ["b"], "b": ["a"]})

def test_ingredient_only():
    assert cooking_order({"a": ["x"]}) == ["x", "a"]
