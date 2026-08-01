"""Turn a line of text into a grid of tile codes.

Uppercases, word-wraps to the column width, pads and truncates to the board.
"""

from clapper_ai.domain.grid import Grid
from clapper_ai.domain.tile_codes import BLANK, CHAR_TO_CODE


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
        while word:
            if not current:
                if len(word) <= cols:
                    current = word
                    break
                # Hard-break a word that could never fit on one line.
                lines.append(word[:cols])
                word = word[cols:]
            elif len(current) + 1 + len(word) <= cols:
                current += f" {word}"
                break
            else:
                lines.append(current)
                current = ""
    if current:
        lines.append(current)
    return lines
