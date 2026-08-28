import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import first_free_slot

def test_simple_gap():
    assert first_free_slot([(60, 120)], 30, 0, 240) == (0, 30)

def test_gap_between():
    assert first_free_slot([(0, 60), (90, 240)], 30, 0, 240) == (60, 90)

def test_overlap_merge():
    assert first_free_slot([(0, 100), (50, 150)], 50, 0, 240) == (150, 200)

def test_no_room():
    assert first_free_slot([(0, 240)], 10, 0, 240) is None

def test_zero_len_ignored():
    assert first_free_slot([(30, 30)], 40, 0, 100) == (0, 40)

def test_bad_duration():
    import pytest
    with pytest.raises(ValueError):
        first_free_slot([], 0, 0, 100)
