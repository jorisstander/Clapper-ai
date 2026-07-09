"""The Brain: turns a user's prompt into a grid on the display.

Answer mode: hand the question to the LLM client, lay the reply out, gate it
with validate_grid, render it. Each LLM client owns its own prompting; the
Brain knows nothing about keyboards, browsers, hardware — or prompt wording.
If the LLM call or its layout fails, the board still responds: it falls back
to an apology, or — if even that can't pass validation — a blank grid.
"""

from clapper_ai.core.codes import ALLOWED_CODES
from clapper_ai.core.grid import blank_grid
from clapper_ai.core.interfaces import DisplaySink, LLMClient
from clapper_ai.core.layout import render_layout
from clapper_ai.core.validate import text_to_grid, validate_grid

# Shown when the LLM call or its layout fails — the board always responds.
FALLBACK_TEXT = "SORRY, TRY AGAIN"


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
        try:
            reply = await self.llm.complete(text, max_chars=rows * cols)
            if isinstance(reply, str):
                grid = text_to_grid(reply, rows, cols)
            else:
                grid = render_layout(reply, rows, cols)
            validate_grid(grid, rows, cols, self.allowed)
        except Exception as error:
            print(f"Could not get an answer: {error}")
            grid = text_to_grid(FALLBACK_TEXT, rows, cols)
            try:
                validate_grid(grid, rows, cols, self.allowed)
            except ValueError:
                grid = blank_grid(rows, cols)
        await self.display.render(grid)
