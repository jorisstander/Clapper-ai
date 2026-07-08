"""Tests for the Brain, using the FakeLLMClient and a fake DisplaySink.

No network, no browser — the Brain only ever sees the three protocols,
so fakes are all we need to test it end to end.
"""

import pytest

from clapper_ai.core.brain import ANSWER_PROMPT, Brain
from clapper_ai.core.grid import Grid
from clapper_ai.llm.fake import FakeLLMClient


class FakeDisplay:
    """Records rendered grids instead of showing them."""

    def __init__(self, rows: int = 6, cols: int = 22):
        self.rows = rows
        self.cols = cols
        self.rendered: list[Grid] = []

    async def render(self, grid: Grid) -> None:
        self.rendered.append(grid)


class ScriptedLLM:
    """Returns a fixed reply and records what it was asked."""

    def __init__(self, reply: str):
        self.reply = reply
        self.prompts: list[str] = []
        self.max_chars: list[int] = []

    async def complete(self, prompt: str, *, max_chars: int) -> str:
        self.prompts.append(prompt)
        self.max_chars.append(max_chars)
        return self.reply


async def test_handle_renders_the_llm_reply_as_a_grid():
    display = FakeDisplay(rows=1, cols=5)
    brain = Brain(llm=ScriptedLLM("HI"), display=display)

    await brain.handle("greet me")

    assert display.rendered == [[[8, 9, 0, 0, 0]]]


async def test_handle_passes_board_capacity_as_max_chars():
    display = FakeDisplay(rows=6, cols=22)
    llm = ScriptedLLM("OK")
    brain = Brain(llm=llm, display=display)

    await brain.handle("anything")

    assert llm.max_chars == [6 * 22]


async def test_prompt_contains_the_user_text_and_the_instructions():
    llm = ScriptedLLM("OK")
    brain = Brain(llm=llm, display=FakeDisplay())

    await brain.handle("what is a split-flap display")

    (prompt,) = llm.prompts
    assert "what is a split-flap display" in prompt
    assert str(6 * 22) in prompt  # the character budget is spelled out


async def test_answer_prompt_constant_is_the_tuning_point():
    # The prompt lives in one findable constant with a max_chars slot.
    assert "{max_chars}" in ANSWER_PROMPT


async def test_oversized_reply_still_renders_a_valid_grid():
    # text_to_grid truncates; the Brain must not crash or ship a bad grid.
    display = FakeDisplay(rows=1, cols=3)
    brain = Brain(llm=ScriptedLLM("TOO MANY WORDS HERE"), display=display)

    await brain.handle("hi")

    (grid,) = display.rendered
    assert len(grid) == 1 and len(grid[0]) == 3


async def test_fake_llm_is_deterministic_and_fits_budget():
    fake = FakeLLMClient()
    first = await fake.complete("PROMPT\nHELLO", max_chars=30)
    second = await fake.complete("PROMPT\nHELLO", max_chars=30)
    assert first == second
    assert len(first) <= 30
    assert first  # never empty — the board should always show something


async def test_fake_llm_echoes_the_question():
    # The question sits on the prompt's last line; the echo makes the demo
    # visibly react to what you type.
    fake = FakeLLMClient()
    reply = await fake.complete("instructions...\nHELLO BOARD", max_chars=100)
    assert "HELLO BOARD" in reply


async def test_brain_with_fake_llm_end_to_end():
    display = FakeDisplay(rows=6, cols=22)
    brain = Brain(llm=FakeLLMClient(), display=display)

    await brain.handle("ping")

    assert len(display.rendered) == 1
    grid = display.rendered[0]
    assert len(grid) == 6 and all(len(row) == 22 for row in grid)
    assert any(code != 0 for row in grid for code in row)


async def test_brain_validates_before_rendering():
    # A display that only allows blanks must reject any lettered grid
    # before render is called.
    display = FakeDisplay(rows=1, cols=2)
    brain = Brain(llm=ScriptedLLM("AB"), display=display, allowed={0})

    with pytest.raises(ValueError):
        await brain.handle("hi")
    assert display.rendered == []
