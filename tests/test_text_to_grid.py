"""Tests for text_to_grid: text in, grid of tile codes out."""

from clapper_ai.core.codes import CHAR_TO_CODE
from clapper_ai.core.validate import text_to_grid


def codes(word: str) -> list[int]:
    """Spell out a word as tile codes, for readable expectations."""
    return [CHAR_TO_CODE[c] for c in word]


def test_returns_exact_dimensions():
    grid = text_to_grid("HI", rows=6, cols=22)
    assert len(grid) == 6
    assert all(len(row) == 22 for row in grid)


def test_letters_map_to_codes_and_pad_with_blank():
    grid = text_to_grid("HI", rows=1, cols=4)
    assert grid == [[8, 9, 0, 0]]


def test_lowercase_is_uppercased():
    assert text_to_grid("hi", rows=1, cols=4) == text_to_grid("HI", rows=1, cols=4)


def test_digits_map_to_codes():
    # digits are 1..9 then 0 → codes 27..36
    grid = text_to_grid("190", rows=1, cols=3)
    assert grid == [[27, 35, 36]]


def test_unknown_chars_become_blank():
    grid = text_to_grid("A?B", rows=1, cols=3)
    assert grid == [[1, 0, 2]]


def test_word_wrap_at_word_boundaries():
    grid = text_to_grid("HELLO WORLD", rows=2, cols=8)
    assert grid[0] == codes("HELLO") + [0, 0, 0]
    assert grid[1] == codes("WORLD") + [0, 0, 0]


def test_word_longer_than_cols_is_hard_broken():
    grid = text_to_grid("ABCDEF", rows=2, cols=4)
    assert grid[0] == codes("ABCD")
    assert grid[1] == codes("EF") + [0, 0]


def test_hard_break_when_the_current_line_is_already_full():
    # Regression: a long word after a full line must not overflow that line.
    grid = text_to_grid("TOO MANY", rows=2, cols=3)
    assert grid[0] == codes("TOO")
    assert grid[1] == codes("MAN")


def test_truncates_to_rows():
    grid = text_to_grid("AA BB CC", rows=2, cols=2)
    assert grid == [codes("AA"), codes("BB")]


def test_empty_text_gives_blank_grid():
    assert text_to_grid("", rows=2, cols=3) == [[0, 0, 0], [0, 0, 0]]


def test_unsupported_align_raises():
    import pytest

    with pytest.raises(ValueError, match="align"):
        text_to_grid("HI", rows=1, cols=4, align="diagonal")
