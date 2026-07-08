"""Helpers between text and Grid, plus the safety gate before a display."""

from clapper_ai.core.codes import BLANK, CHAR_TO_CODE
from clapper_ai.core.grid import Grid


def text_to_grid(text: str, rows: int, cols: int, align: str = "left") -> Grid:
    """Lay text out on a rows x cols grid of tile codes.

    Uppercases, word-wraps to the column width (hard-breaking words longer
    than a line), pads short lines with blanks, and truncates anything past
    the last row. Characters without a tile code become blanks.
    """
    if align != "left":
        raise ValueError(f"Unsupported align {align!r}; only 'left' is implemented")

    lines = _word_wrap(text.upper(), cols)[:rows]

    grid: Grid = []
    for row in range(rows):
        line = lines[row] if row < len(lines) else ""
        codes = [CHAR_TO_CODE.get(char, BLANK) for char in line]
        codes += [BLANK] * (cols - len(codes))
        grid.append(codes)
    return grid


def _word_wrap(text: str, cols: int) -> list[str]:
    """Wrap text into lines of at most cols characters, breaking on spaces."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        # Hard-break words that could never fit on one line.
        while len(word) > cols:
            space_left = cols - len(current) - (1 if current else 0)
            head, word = word[:space_left], word[space_left:]
            lines.append(f"{current} {head}".strip())
            current = ""
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= cols:
            current += f" {word}"
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def validate_grid(grid: Grid, rows: int, cols: int, allowed: set[int]) -> Grid:
    """Assert a grid has exactly rows x cols tiles, all with allowed codes.

    This is the safety gate: every grid passes through here before it reaches
    a display, so a display never has to defend itself against bad data.
    Raises ValueError with a precise message on any violation.
    """
    if len(grid) != rows:
        raise ValueError(f"Grid has {len(grid)} rows, expected exactly {rows}")
    for r, row in enumerate(grid):
        if len(row) != cols:
            raise ValueError(f"Row {r} has {len(row)} columns, expected exactly {cols}")
        for c, code in enumerate(row):
            if code not in allowed:
                raise ValueError(
                    f"Tile code {code} at row {r}, column {c} is not allowed on this board"
                )
    return grid
