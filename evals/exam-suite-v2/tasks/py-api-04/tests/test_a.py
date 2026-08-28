import sys, os, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import render

def test_plain():
    assert render("hello {{name}}", {"name": "bob"}) == "hello bob"

def test_filters_chain():
    assert render("{{t|trunc:3|up}}", {"t": "spring"}) == "SPR"

def test_default_used():
    assert render("{{x|default:hi}}", {}) == "hi"

def test_default_ignored_when_present():
    assert render("{{x|default:hi|up}}", {"x": "yo"}) == "YO"

def test_missing_key():
    with pytest.raises(ValueError):
        render("{{x}}", {})

def test_default_not_first():
    with pytest.raises(ValueError):
        render("{{x|up|default:q}}", {})

def test_unknown_filter():
    with pytest.raises(ValueError):
        render("{{x|boom}}", {"x": "1"})

def test_spaces():
    assert render("{{ n | low }}", {"n": "ABC"}) == "abc"
