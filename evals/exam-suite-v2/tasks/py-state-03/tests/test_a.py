import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solution import DepCache

def test_basic():
    c = DepCache()
    c.put("a.b", 1)
    assert c.get("a.b") == 1
    assert c.keys() == ["a.b"]

def test_prefix_invalidate():
    c = DepCache()
    c.put("a.x", 1); c.put("a.y", 2); c.put("b.z", 3)
    c.invalidate("a.")
    assert c.keys() == ["b.z"]

def test_transitive():
    c = DepCache()
    c.put("cfg.base", 1)
    c.put("app", 2, deps=["cfg.base"])
    c.put("cluster", 3, deps=["app"])
    c.invalidate("cfg.")
    assert c.keys() == []

def test_cycle_safe():
    c = DepCache()
    c.put("p", 1, deps=["q"]); c.put("q", 2, deps=["p"])
    c.invalidate("p")
    assert c.keys() == []

def test_reput():
    c = DepCache()
    c.put("x", 1); c.put("y", 2, deps=["x"])
    c.invalidate("x")
    c.put("y", 5)
    assert c.get("y") == 5
