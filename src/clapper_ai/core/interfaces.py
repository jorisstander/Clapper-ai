"""The three seams of the system.

The Brain depends only on these protocols — never on a concrete adapter.
That is what makes the ends swappable: any object with these methods works,
whether it's a keyboard or a microphone, a browser canvas or real hardware.
"""

from typing import Protocol

from clapper_ai.core.grid import Grid


class InputSource(Protocol):
    """Where prompts come from (keyboard now; mic or phone later)."""

    async def listen(self) -> str:
        """Block until the user says/types something; return the transcript."""
        ...


class DisplaySink(Protocol):
    """Where grids go (virtual board now; DIY hardware or Vestaboard later)."""

    rows: int
    cols: int

    async def render(self, grid: Grid) -> None:
        """Display the grid. The sink owns its own animation."""
        ...


class LLMClient(Protocol):
    """The model that turns a prompt into an answer."""

    async def complete(self, prompt: str, *, max_chars: int) -> str:
        """Return a completion of at most roughly max_chars characters."""
        ...
