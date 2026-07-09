"""LayoutSpec: how the LLM describes a board design, and how it becomes a grid.

The model chooses WHAT the board shows (text lines with alignment and color
accents, or a full grid of tile codes for art). render_layout does the exact
tile arithmetic, so the model can never be off by one — or break the board.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from clapper_ai.core.codes import BLANK, CHAR_TO_CODE, COLOR_CODES
from clapper_ai.core.grid import Grid, blank_grid

ColorName = Literal["red", "orange", "yellow", "green", "blue", "violet", "white"]


class Line(BaseModel):
    text: str = ""
    align: Literal["left", "center", "right"] = "left"
    color: ColorName | None = None  # with empty text: a full row of this color


class TextLayout(BaseModel):
    type: Literal["text_layout"]
    lines: list[Line]


class ArtLayout(BaseModel):
    type: Literal["art"]
    grid: list[list[int]]


LayoutSpec = Annotated[TextLayout | ArtLayout, Field(discriminator="type")]


def render_layout(spec: TextLayout | ArtLayout, rows: int, cols: int) -> Grid:
    """Turn a LayoutSpec into a rows x cols grid of tile codes.

    Text is clipped and padded deterministically; art grids pass through
    untouched (validate_grid gates their shape and codes downstream).
    """
    if isinstance(spec, ArtLayout):
        return spec.grid

    grid = blank_grid(rows, cols)
    for row, line in enumerate(spec.lines[:rows]):
        if line.color is not None and not line.text.strip():
            grid[row] = [COLOR_CODES[line.color]] * cols
            continue
        codes = [CHAR_TO_CODE.get(char, BLANK) for char in line.text.upper()[:cols]]
        pad = cols - len(codes)
        if line.align == "center":
            left = pad // 2
            grid[row] = [BLANK] * left + codes + [BLANK] * (pad - left)
        elif line.align == "right":
            grid[row] = [BLANK] * pad + codes
        else:
            grid[row] = codes + [BLANK] * pad
    return grid
