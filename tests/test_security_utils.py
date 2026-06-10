"""Security utility tests."""

from app.utils.search import escape_ilike, ilike_contains


def test_escape_ilike_wildcards() -> None:
    assert escape_ilike("100%_off") == "100\\%\\_off"


def test_ilike_contains_builds_pattern() -> None:
    pattern, escape = ilike_contains("  cocoa  ")
    assert pattern == "%cocoa%"
    assert escape == "\\"


def test_ilike_contains_escapes_user_wildcards() -> None:
    pattern, escape = ilike_contains("a_b%")
    assert pattern == "%a\\_b\\%%"
    assert escape == "\\"
