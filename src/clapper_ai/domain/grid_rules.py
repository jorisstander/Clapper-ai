"""The safety gate: the invariants every grid must satisfy before it is shown.

Every grid passes through here on its way to a display, so a display never has
to defend itself against bad data.
"""

from clapper_ai.domain.grid import Grid


def validate_grid(grid: Grid, rows: int, cols: int, allowed: set[int]) -> Grid:
    """Assert a grid has exactly rows x cols tiles, all with allowed codes.

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
