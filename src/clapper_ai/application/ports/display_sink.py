"""Driven port: where grids go.

AnswerQuestion calls out through this. Implementations live in adapters/displays/.
"""

from typing import Protocol

from clapper_ai.domain.grid import Grid


class DisplaySink(Protocol):
    """A board of a fixed size that can render a grid (virtual now; DIY
    hardware or Vestaboard later). The sink owns its own animation."""

    rows: int
    cols: int

    async def render(self, grid: Grid) -> None: ...
