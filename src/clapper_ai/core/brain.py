"""The Brain: turns a user's prompt into a grid on the display.

Answer mode only for now: ask the LLM for a concise plain-text answer,
lay it out with text_to_grid, gate it with validate_grid, render it.
The Brain knows nothing about keyboards, browsers, or hardware — only
the protocols in interfaces.py.
"""

from clapper_ai.core.codes import ALLOWED_CODES
from clapper_ai.core.interfaces import DisplaySink, LLMClient
from clapper_ai.core.validate import text_to_grid, validate_grid

# The answer-mode prompt. Kept in one constant so it's easy to find and tune.
ANSWER_PROMPT = (
    "You are answering on a tiny split-flap display. "
    "Reply in plain text only: no markdown, no line breaks, "
    "at most {max_chars} characters. Be concise and direct.\n"
    "{question}"
)


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
        """One full turn: prompt → LLM → grid → validate → display."""
        rows, cols = self.display.rows, self.display.cols
        max_chars = rows * cols
        prompt = ANSWER_PROMPT.format(max_chars=max_chars, question=text)
        reply = await self.llm.complete(prompt, max_chars=max_chars)
        grid = text_to_grid(reply, rows, cols)
        validate_grid(grid, rows, cols, self.allowed)
        await self.display.render(grid)
