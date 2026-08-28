import sys, os, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import decode

def test_basic():
    assert decode("3a2b#5") == "aaabb"

def test_bang_flag():
    assert decode("3a!#4") == "aaaa"

def test_multidigit():
    assert decode("12x#12") == "x" * 12

def test_no_checksum():
    with pytest.raises(ValueError):
        decode("3a")

def test_bad_checksum():
    with pytest.raises(ValueError):
        decode("3a#4")

def test_multi_bang():
    assert decode("1a!!#3") == "aaa"
