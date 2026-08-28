import sys, os, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import Elevator

def test_ride_and_open():
    e = Elevator(10, 4)
    e.call(3)
    e.step(); e.step()
    assert e.current == 3 and e.doors_open

def test_move_requires_closed():
    e = Elevator(10, 4)
    e.call(2)
    e.step()
    with pytest.raises(RuntimeError):
        e.step()

def test_board_and_overload():
    e = Elevator(10, 2)
    e.call(1)
    e.step()
    e.board(2)
    with pytest.raises(ValueError):
        e.board(1)
    assert e.passengers == 2

def test_board_closed_doors():
    e = Elevator(10, 2)
    with pytest.raises(RuntimeError):
        e.board(1)

def test_no_targets_stay():
    e = Elevator(10, 2)
    e.step()
    assert e.current == 1

def test_tie_break_down():
    e = Elevator(10, 4)
    e.call(2); e.call(4)
    e.step()  # с 1: до 2 и 4 одинаково (1 этаж); при равенстве - вниз
    assert e.current == 2
