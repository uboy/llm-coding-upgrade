import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import apply_rate

def test_half_even_down():
    assert apply_rate(5, 500) == 2

def test_half_even_up():
    assert apply_rate(15, 100) == 2

def test_exact():
    assert apply_rate(1000, 500) == 500

def test_big_no_float_error():
    n = 123456789012
    # 123456789012 * 15 / 1000 = 1851851835.18 -> 1851851835
    assert apply_rate(n, 15) == 1851851835

def test_negative_amount():
    assert apply_rate(-5, 500) == -2

def test_beyond_double_precision():
    # 2^53+1 не представимо в double: float-версия обязана ошибиться
    n = 9007199254740993
    assert apply_rate(n, 1000) == 9007199254740993
