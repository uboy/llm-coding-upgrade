import sys, os, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import transaction

def test_all_ok():
    log = []
    with transaction([(lambda: log.append("a"), lambda: log.append("u"))]):
        pass
    assert log == ["a"]

def test_rollback_reverse():
    log = []
    def boom():
        raise KeyError("x")
    with pytest.raises(KeyError):
        with transaction([(lambda: log.append("a"), lambda: log.append("u1")),
                          (lambda: log.append("b"), lambda: log.append("u2")),
                          (boom, None)]):
            pass
    assert log == ["a", "b", "u2", "u1"]

def test_no_undo():
    with pytest.raises(ValueError):
        with transaction([(lambda: (_ for _ in ()).throw(ValueError()), None)]):
            pass

def test_rollback_errors_attached():
    def boom():
        raise KeyError("orig")
    def bad_undo():
        raise RuntimeError("undo fail")
    with pytest.raises(KeyError) as e:
        with transaction([(lambda: None, bad_undo), (boom, None)]):
            pass
    assert str(getattr(e.value, "rollback_errors")[0]) == "undo fail"
