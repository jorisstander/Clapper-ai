"""Tests for validate_grid — the safety gate before anything reaches a display."""

import pytest

from clapper_ai.domain.grid_rules import validate_grid
from clapper_ai.domain.tile_codes import ALLOWED_CODES, CHAR_TO_CODE, COLOR_CODES


def test_valid_grid_is_returned_unchanged():
    grid = [[1, 2], [3, 0]]
    assert validate_grid(grid, rows=2, cols=2, allowed=ALLOWED_CODES) is grid


def test_wrong_row_count_raises():
    with pytest.raises(ValueError, match="rows"):
        validate_grid([[0, 0]], rows=2, cols=2, allowed=ALLOWED_CODES)


def test_wrong_col_count_raises():
    with pytest.raises(ValueError, match="columns"):
        validate_grid([[0, 0, 0], [0, 0]], rows=2, cols=3, allowed=ALLOWED_CODES)


def test_illegal_code_raises_and_names_the_code():
    with pytest.raises(ValueError, match="99"):
        validate_grid([[0, 99]], rows=1, cols=2, allowed=ALLOWED_CODES)


def test_board_specific_subset_is_enforced():
    # A board may allow fewer codes than the full map; 2 is legal globally but not here.
    with pytest.raises(ValueError, match="2"):
        validate_grid([[0, 2]], rows=1, cols=2, allowed={0, 1})


def test_code_map_anchors():
    assert CHAR_TO_CODE[" "] == 0
    assert CHAR_TO_CODE["A"] == 1
    assert CHAR_TO_CODE["Z"] == 26
    assert CHAR_TO_CODE["1"] == 27
    assert CHAR_TO_CODE["9"] == 35
    assert CHAR_TO_CODE["0"] == 36
    assert set(COLOR_CODES.values()) == {63, 64, 65, 66, 67, 68, 69}
    assert set(COLOR_CODES.values()) <= ALLOWED_CODES
