"""Tests for render_layout: LayoutSpec in, valid grid out."""

from clapper_ai.core.codes import ALLOWED_CODES, CHAR_TO_CODE
from clapper_ai.core.layout import ArtLayout, Line, TextLayout, render_layout
from clapper_ai.core.validate import validate_grid


def text_spec(*lines: Line) -> TextLayout:
    return TextLayout(type="text_layout", lines=list(lines))


def codes(word: str) -> list[int]:
    return [CHAR_TO_CODE[c] for c in word]


def test_left_align_pads_right():
    grid = render_layout(text_spec(Line(text="HI")), rows=1, cols=4)
    assert grid == [[8, 9, 0, 0]]


def test_center_align():
    grid = render_layout(text_spec(Line(text="HI", align="center")), rows=1, cols=6)
    assert grid == [[0, 0, 8, 9, 0, 0]]


def test_uneven_center_leans_left():
    grid = render_layout(text_spec(Line(text="HI", align="center")), rows=1, cols=5)
    assert grid == [[0, 8, 9, 0, 0]]


def test_right_align_pads_left():
    grid = render_layout(text_spec(Line(text="HI", align="right")), rows=1, cols=4)
    assert grid == [[0, 0, 8, 9]]


def test_long_line_is_clipped_to_cols():
    grid = render_layout(text_spec(Line(text="ABCDEF")), rows=1, cols=4)
    assert grid == [codes("ABCD")]


def test_lowercase_uppercased_and_unknown_chars_blank():
    grid = render_layout(text_spec(Line(text="a?b")), rows=1, cols=3)
    assert grid == [[1, 0, 2]]


def test_empty_text_with_color_fills_the_row():
    grid = render_layout(text_spec(Line(text="", color="orange")), rows=1, cols=3)
    assert grid == [[64, 64, 64]]


def test_text_wins_over_color():
    # A line with both text and color renders the text; color is ignored.
    grid = render_layout(text_spec(Line(text="HI", color="red")), rows=1, cols=2)
    assert grid == [codes("HI")]


def test_missing_rows_are_padded_blank():
    grid = render_layout(text_spec(Line(text="A")), rows=3, cols=2)
    assert grid == [[1, 0], [0, 0], [0, 0]]


def test_extra_lines_are_dropped():
    spec = text_spec(Line(text="A"), Line(text="B"), Line(text="C"))
    grid = render_layout(spec, rows=2, cols=1)
    assert grid == [[1], [2]]


def test_art_grid_passes_through_unchanged():
    art = ArtLayout(type="art", grid=[[63, 0], [67, 69]])
    assert render_layout(art, rows=2, cols=2) == [[63, 0], [67, 69]]


def test_text_layout_output_is_always_a_valid_grid():
    spec = text_spec(
        Line(text="POPULATION OF THE NETHERLANDS IS BIG", align="center"),
        Line(text="", color="blue"),
    )
    grid = render_layout(spec, rows=6, cols=22)
    validate_grid(grid, rows=6, cols=22, allowed=ALLOWED_CODES)  # must not raise
