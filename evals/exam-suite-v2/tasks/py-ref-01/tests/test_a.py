import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import validate_form

def test_ok():
    assert validate_form({"name": "Ann", "age": 30, "email": "a@b.co"}) == []

def test_missing():
    assert validate_form({}) == ["no_name", "no_age", "no_email"]

def test_age_rules():
    assert validate_form({"name": "A", "age": 17, "email": "a@b.co"}) == ["age_minor"]
    assert validate_form({"name": "A", "age": 151, "email": "a@b.co"}) == ["age_impossible"]

def test_email_rule():
    assert validate_form({"name": "A", "age": 30, "email": "bob"}) == ["email_bad"]

def test_multi_errors_order():
    assert validate_form({"age": 10, "email": "x"}) == ["no_name", "age_minor", "email_bad"]
