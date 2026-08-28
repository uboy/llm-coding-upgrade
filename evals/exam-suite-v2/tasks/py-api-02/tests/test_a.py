import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import validate

def test_ok():
    r = validate(["G123-45"])
    assert r["valid"] == ["G123-45"]
    assert r["normalized"] == {"G123-45": "g12345"}
    assert r["errors"] == {}

def test_format_error():
    assert validate(["X1-2", "G1", "G1-"])["errors"] == {"X1-2": "format", "G1": "format", "G1-": "format"}

def test_group_error():
    assert validate(["G123-01"])["errors"] == {"G123-01": "group"}

def test_lowercase_letter_is_format_error():
    assert validate(["g1-2"])["errors"] == {"g1-2": "format"}

def test_empty():
    assert validate([]) == {"valid": [], "normalized": {}, "errors": {}}
