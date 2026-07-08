"""The one data structure everything speaks: a grid of tile codes.

A Grid is rows x cols of ints; each int is one tile code (see codes.py).
Inputs produce text, the Brain turns it into a Grid, displays render Grids.
"""

Grid = list[list[int]]


def blank_grid(rows: int, cols: int) -> Grid:
    """A grid of the given size with every tile blank."""
    return [[0] * cols for _ in range(rows)]
