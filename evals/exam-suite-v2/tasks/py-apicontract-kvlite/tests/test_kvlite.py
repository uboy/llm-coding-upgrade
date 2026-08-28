import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kvlite import parse


def test_comments_and_empty_lines():
    assert parse("# hi\n\n   # indented comment\nkey = 1\n") == {"key": 1}


def test_toplevel_keys_before_section():
    assert parse("a = 1\nb = two\n[s]\nc = 3\n") == {"a": 1, "b": "two", "s": {"c": 3}}


def test_section_nesting_single_level():
    assert parse("[db]\nhost = \"h\"\n[log]\nlevel = 5\n") == {
        "db": {"host": "h"},
        "log": {"level": 5},
    }


def test_quoted_string_escapes():
    assert parse('k = "a\\nb\\tc\\\\d\\"e"\n') == {"k": 'a\nb\tc\\d"e'}


def test_int_float_bool():
    assert parse("a = -5\nb = 3.14\nc = TRUE\nd = Off\n") == {
        "a": -5, "b": 3.14, "c": True, "d": False,
    }


def test_bool_case_insensitive():
    assert parse("a = false\nb = ON\n") == {"a": False, "b": True}


def test_array_mixed_and_empty():
    assert parse('a = [1, "x", 2.5, true]\nb = []\n') == {
        "a": [1, "x", 2.5, True], "b": [],
    }


def test_bare_string_until_eol():
    assert parse("k = 127.0.0.1:8080 extra\n") == {"k": "127.0.0.1:8080 extra"}


def test_duplicate_key_last_wins():
    assert parse("k = 1\nk = \"two\"\n") == {"k": "two"}


def test_unknown_escape_is_error_with_line_number():
    with pytest.raises(ValueError) as e:
        parse('k = "a\\qb"\n')
    assert "1" in str(e.value)


def test_garbage_line_error_reports_line_number():
    with pytest.raises(ValueError) as e:
        parse("a = 1\nthis is garbage\n")
    assert "2" in str(e.value)


def test_duplicate_section_is_error():
    with pytest.raises(ValueError):
        parse("[a]\nx = 1\n[a]\ny = 2\n")


def test_empty_value_is_error():
    with pytest.raises(ValueError):
        parse("k =\n")
