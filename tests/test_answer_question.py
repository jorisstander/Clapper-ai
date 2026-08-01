"""Tests for the AnswerQuestion, using the FakeLLMClient and a fake DisplaySink.

No network, no browser — the AnswerQuestion only ever sees the three protocols,
so fakes are all we need to test it end to end.
"""

from clapper_ai.application.interactors.answer_question import AnswerQuestion
from clapper_ai.domain.grid import Grid, blank_grid
from clapper_ai.domain.layout import ArtLayout, Line, TextLayout
from clapper_ai.domain.text_layout import text_to_grid
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
    brain = AnswerQuestion(llm=ScriptedLLM("HI"), display=display)

    await brain.execute("greet me")

    assert display.rendered == [[[8, 9, 0, 0, 0]]]


async def test_handle_passes_board_capacity_as_max_chars():
    display = FakeDisplay(rows=6, cols=22)
    llm = ScriptedLLM("OK")
    brain = AnswerQuestion(llm=llm, display=display)

    await brain.execute("anything")

    assert llm.max_chars == [6 * 22]


async def test_brain_passes_the_raw_question_to_the_llm():
    llm = ScriptedLLM("OK")
    brain = AnswerQuestion(llm=llm, display=FakeDisplay())

    await brain.execute("what is a split-flap display")

    assert llm.prompts == ["what is a split-flap display"]


async def test_oversized_reply_still_renders_a_valid_grid():
    # text_to_grid truncates; the AnswerQuestion must not crash or ship a bad grid.
    display = FakeDisplay(rows=1, cols=3)
    brain = AnswerQuestion(llm=ScriptedLLM("TOO MANY WORDS HERE"), display=display)

    await brain.execute("hi")

    (grid,) = display.rendered
    assert len(grid) == 1 and len(grid[0]) == 3


async def test_fake_llm_is_deterministic_and_fits_budget():
    fake = FakeLLMClient()
    first = await fake.complete("HELLO", max_chars=30)
    second = await fake.complete("HELLO", max_chars=30)
    assert first == second
    assert len(first) <= 30
    assert first  # never empty — the board should always show something


async def test_fake_llm_echoes_the_question():
    fake = FakeLLMClient()
    reply = await fake.complete("HELLO BOARD", max_chars=100)
    assert reply == "YOU SAID HELLO BOARD"


async def test_brain_with_fake_llm_end_to_end():
    display = FakeDisplay(rows=6, cols=22)
    brain = AnswerQuestion(llm=FakeLLMClient(), display=display)

    await brain.execute("ping")

    assert len(display.rendered) == 1
    grid = display.rendered[0]
    assert len(grid) == 6 and all(len(row) == 22 for row in grid)
    assert any(code != 0 for row in grid for code in row)


async def test_restricted_board_falls_back_to_blank_grid():
    # allowed={0} can't show letters — not the reply, not the apology.
    display = FakeDisplay(rows=1, cols=2)
    brain = AnswerQuestion(llm=ScriptedLLM("AB"), display=display, allowed={0})

    await brain.execute("hi")

    assert display.rendered == [blank_grid(1, 2)]


class ScriptedLayoutLLM:
    """Returns a LayoutSpec instead of a string."""

    def __init__(self, spec):
        self.spec = spec

    async def complete(self, prompt: str, *, max_chars: int):
        return self.spec


async def test_text_layout_reply_is_rendered():
    display = FakeDisplay(rows=1, cols=4)
    spec = TextLayout(type="text_layout", lines=[Line(text="HI", align="right")])
    brain = AnswerQuestion(llm=ScriptedLayoutLLM(spec), display=display)

    await brain.execute("hi")

    assert display.rendered == [[[0, 0, 8, 9]]]


async def test_art_reply_is_rendered():
    display = FakeDisplay(rows=1, cols=2)
    spec = ArtLayout(type="art", grid=[[63, 67]])
    brain = AnswerQuestion(llm=ScriptedLayoutLLM(spec), display=display)

    await brain.execute("paint something")

    assert display.rendered == [[[63, 67]]]


class ExplodingLLM:
    async def complete(self, prompt: str, *, max_chars: int) -> str:
        raise RuntimeError("api down")


async def test_llm_error_renders_an_apology_instead_of_crashing():
    display = FakeDisplay(rows=6, cols=22)
    brain = AnswerQuestion(llm=ExplodingLLM(), display=display)

    await brain.execute("hi")

    assert display.rendered == [text_to_grid("SORRY, TRY AGAIN", 6, 22)]


async def test_invalid_art_grid_renders_the_apology():
    display = FakeDisplay(rows=1, cols=2)
    bad = ArtLayout(type="art", grid=[[999, 999]])  # illegal codes
    brain = AnswerQuestion(llm=ScriptedLayoutLLM(bad), display=display)

    await brain.execute("paint")

    assert display.rendered == [text_to_grid("SORRY, TRY AGAIN", 1, 2)]
