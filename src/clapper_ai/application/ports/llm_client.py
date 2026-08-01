"""Driven port: the model that turns a prompt into an answer.

AnswerQuestion calls out through this. Implementations live in adapters/llm/.
"""

from typing import Protocol

from clapper_ai.domain.layout import LayoutSpec


class LLMClient(Protocol):
    """Returns either plain text (laid out by text_to_grid) or a LayoutSpec
    (the model designed the board itself; rendered by render_layout)."""

    async def complete(self, prompt: str, *, max_chars: int) -> str | LayoutSpec: ...
