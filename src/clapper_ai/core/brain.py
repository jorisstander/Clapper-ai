"""The Brain: turns a user's prompt into a grid on the display.

Answer mode: hand the question to the LLM client, lay the reply out, gate it
with validate_grid, render it. Each LLM client owns its own prompting; the
Brain knows nothing about keyboards, browsers, hardware — or prompt wording.
"""

from clapper_ai.core.codes import ALLOWED_CODES
from clapper_ai.core.interfaces import DisplaySink, LLMClient
from clapper_ai.core.validate import text_to_grid, validate_grid


class Brain:
    def __init__(
        self,
        llm: LLMClient,
        display: DisplaySink,
        allowed: set[int] = ALLOWED_CODES,
    ):
        self.llm = llm
        self.display = display
        self.allowed = allowed

    async def handle(self, text: str) -> None:
        """One full turn: question → LLM → grid → validate → display."""
        rows, cols = self.display.rows, self.display.cols
        reply = await self.llm.complete(text, max_chars=rows * cols)
        grid = text_to_grid(reply, rows, cols)
        validate_grid(grid, rows, cols, self.allowed)
        await self.display.render(grid)
