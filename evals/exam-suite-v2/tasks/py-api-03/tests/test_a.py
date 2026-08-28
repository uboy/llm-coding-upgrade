import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import balance

def test_dc():
    r = balance(["01.01.2024|cash|C|100", "02.01.2024|cash|D|30"])
    assert r["balances"] == {"cash": 70}
    assert r["skipped"] == []

def test_two_accounts():
    r = balance(["01.01.2024|a|C|5", "01.01.2024|b|D|5"])
    assert r["balances"] == {"a": 5, "b": -5}

def test_skip_bad():
    r = balance(["32.01.2024|a|C|1", "01.01.2024|a|X|1", "01.01.2024|a|C|-1", "01.01.2024|a|C|1.5", "broken"])
    assert r["balances"] == {}
    assert len(r["skipped"]) == 5

def test_leap():
    r = balance(["29.02.2024|a|C|1", "29.02.2023|b|C|1"])
    assert r["balances"] == {"a": 1}
    assert r["skipped"] == ["29.02.2023|b|C|1"]
