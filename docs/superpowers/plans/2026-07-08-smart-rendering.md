# Smart Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One API call answers a question (with web search) AND designs the board — centered text layouts with color accents, or full-board tile art — rendered deterministically and safely.

**Architecture:** A `LayoutSpec` union (`text_layout` | `art`) is the new contract between the LLM and the board. A pure `render_layout()` turns a spec into a grid. The `LLMClient` protocol widens to return `str | LayoutSpec`; the Brain branches on the type and falls back to an apology grid on any error. A new `SmartAnthropicClient` makes the single structured-output call with the `web_search` server tool. Prompt ownership moves from the Brain into the LLM clients.

**Tech Stack:** Python 3.11+, Pydantic (discriminated union + TypeAdapter), Anthropic Messages API (`claude-opus-4-8`, `output_config.format` JSON schema, `web_search_20260209`), pytest with fakes (no network in tests).

**Spec:** `docs/superpowers/specs/2026-07-08-smart-rendering-design.md`

**Conventions for every task:** run commands from the repo root with the venv:
`.venv/bin/pytest`, `.venv/bin/ruff check .`. Commit after each task with the message given. TDD: never write implementation before you have watched its test fail.

---

## File structure

| File | Responsibility |
|---|---|
| `src/clapper_ai/core/layout.py` (create) | `Line`, `TextLayout`, `ArtLayout`, `LayoutSpec` types + `render_layout()` — spec → grid, deterministic |
| `src/clapper_ai/core/brain.py` (modify) | Pass raw question to LLM; branch str vs LayoutSpec; apology fallback |
| `src/clapper_ai/core/interfaces.py` (modify) | `LLMClient.complete` returns `str \| LayoutSpec` |
| `src/clapper_ai/llm/fake.py` (modify) | Echo the raw question (prompt no longer wraps it) |
| `src/clapper_ai/llm/anthropic_client.py` (modify) | Owns `ANSWER_PROMPT` (moved from brain.py) |
| `src/clapper_ai/llm/anthropic_smart.py` (create) | `SmartAnthropicClient`: system prompt + web_search + JSON schema → `LayoutSpec` |
| `src/clapper_ai/__main__.py` (modify) | `LLMS["anthropic-smart"]` registry entry |
| `tests/test_layout.py` (create), `tests/test_brain.py` (modify), `tests/test_anthropic_client.py` (modify), `tests/test_anthropic_smart.py` (create), `tests/test_config.py` (modify) | Tests per component |

---

### Task 1: LayoutSpec types and render_layout

**Files:**
- Create: `src/clapper_ai/core/layout.py`
- Test: `tests/test_layout.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_layout.py`:

```python
"""Tests for render_layout: LayoutSpec in, valid grid out."""

from clapper_ai.core.codes import ALLOWED_CODES, CHAR_TO_CODE
from clapper_ai.core.layout import ArtLayout, Line, TextLayout, render_layout
from clapper_ai.core.validate import validate_grid


def text_spec(*lines: Line) -> TextLayout:
    return TextLayout(type="text_layout", lines=list(lines))


def codes(word: str) -> list[int]:
    return [CHAR_TO_CODE[c] for c in word]


def test_left_align_pads_right():
    grid = render_layout(text_spec(Line(text="HI")), rows=1, cols=4)
    assert grid == [[8, 9, 0, 0]]


def test_center_align():
    grid = render_layout(text_spec(Line(text="HI", align="center")), rows=1, cols=6)
    assert grid == [[0, 0, 8, 9, 0, 0]]


def test_uneven_center_leans_left():
    grid = render_layout(text_spec(Line(text="HI", align="center")), rows=1, cols=5)
    assert grid == [[0, 8, 9, 0, 0]]


def test_right_align_pads_left():
    grid = render_layout(text_spec(Line(text="HI", align="right")), rows=1, cols=4)
    assert grid == [[0, 0, 8, 9]]


def test_long_line_is_clipped_to_cols():
    grid = render_layout(text_spec(Line(text="ABCDEF")), rows=1, cols=4)
    assert grid == [codes("ABCD")]


def test_lowercase_uppercased_and_unknown_chars_blank():
    grid = render_layout(text_spec(Line(text="a?b")), rows=1, cols=3)
    assert grid == [[1, 0, 2]]


def test_empty_text_with_color_fills_the_row():
    grid = render_layout(text_spec(Line(text="", color="orange")), rows=1, cols=3)
    assert grid == [[64, 64, 64]]


def test_text_wins_over_color():
    # A line with both text and color renders the text; color is ignored.
    grid = render_layout(text_spec(Line(text="HI", color="red")), rows=1, cols=2)
    assert grid == [codes("HI")]


def test_missing_rows_are_padded_blank():
    grid = render_layout(text_spec(Line(text="A")), rows=3, cols=2)
    assert grid == [[1, 0], [0, 0], [0, 0]]


def test_extra_lines_are_dropped():
    spec = text_spec(Line(text="A"), Line(text="B"), Line(text="C"))
    grid = render_layout(spec, rows=2, cols=1)
    assert grid == [[1], [2]]


def test_art_grid_passes_through_unchanged():
    art = ArtLayout(type="art", grid=[[63, 0], [67, 69]])
    assert render_layout(art, rows=2, cols=2) == [[63, 0], [67, 69]]


def test_text_layout_output_is_always_a_valid_grid():
    spec = text_spec(
        Line(text="POPULATION OF THE NETHERLANDS IS BIG", align="center"),
        Line(text="", color="blue"),
    )
    grid = render_layout(spec, rows=6, cols=22)
    validate_grid(grid, rows=6, cols=22, allowed=ALLOWED_CODES)  # must not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_layout.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'clapper_ai.core.layout'`

- [ ] **Step 3: Write the implementation**

Create `src/clapper_ai/core/layout.py`:

```python
"""LayoutSpec: how the LLM describes a board design, and how it becomes a grid.

The model chooses WHAT the board shows (text lines with alignment and color
accents, or a full grid of tile codes for art). render_layout does the exact
tile arithmetic, so the model can never be off by one — or break the board.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from clapper_ai.core.codes import BLANK, CHAR_TO_CODE, COLOR_CODES
from clapper_ai.core.grid import Grid, blank_grid

ColorName = Literal["red", "orange", "yellow", "green", "blue", "violet", "white"]


class Line(BaseModel):
    text: str = ""
    align: Literal["left", "center", "right"] = "left"
    color: ColorName | None = None  # with empty text: a full row of this color


class TextLayout(BaseModel):
    type: Literal["text_layout"]
    lines: list[Line]


class ArtLayout(BaseModel):
    type: Literal["art"]
    grid: list[list[int]]


LayoutSpec = Annotated[TextLayout | ArtLayout, Field(discriminator="type")]


def render_layout(spec: TextLayout | ArtLayout, rows: int, cols: int) -> Grid:
    """Turn a LayoutSpec into a rows x cols grid of tile codes.

    Text is clipped and padded deterministically; art grids pass through
    untouched (validate_grid gates their shape and codes downstream).
    """
    if isinstance(spec, ArtLayout):
        return spec.grid

    grid = blank_grid(rows, cols)
    for row, line in enumerate(spec.lines[:rows]):
        if line.color is not None and not line.text.strip():
            grid[row] = [COLOR_CODES[line.color]] * cols
            continue
        codes = [CHAR_TO_CODE.get(char, BLANK) for char in line.text.upper()[:cols]]
        pad = cols - len(codes)
        if line.align == "center":
            left = pad // 2
            grid[row] = [BLANK] * left + codes + [BLANK] * (pad - left)
        elif line.align == "right":
            grid[row] = [BLANK] * pad + codes
        else:
            grid[row] = codes + [BLANK] * pad
    return grid
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_layout.py -q`
Expected: `12 passed`

- [ ] **Step 5: Lint and commit**

```bash
.venv/bin/ruff check . && git add src/clapper_ai/core/layout.py tests/test_layout.py
git commit -m "feat: add LayoutSpec types and deterministic render_layout"
```

---

### Task 2: Move prompt ownership into the LLM clients

The Brain currently wraps the question in `ANSWER_PROMPT` before calling the LLM.
The smart client (Task 5) needs the raw question — its instructions live in a
system prompt and a JSON schema, and a "reply in plain text" wrapper would
contradict them. So: the Brain passes the raw question; each client owns its
own prompting.

**Files:**
- Modify: `src/clapper_ai/core/brain.py`
- Modify: `src/clapper_ai/llm/fake.py`
- Modify: `src/clapper_ai/llm/anthropic_client.py`
- Test: `tests/test_brain.py`, `tests/test_anthropic_client.py`

- [ ] **Step 1: Update the tests to the new contract**

In `tests/test_brain.py`:

1. Change the import line `from clapper_ai.core.brain import ANSWER_PROMPT, Brain`
   to `from clapper_ai.core.brain import Brain`.
2. Replace `test_prompt_contains_the_user_text_and_the_instructions` and
   `test_answer_prompt_constant_is_the_tuning_point` with:

```python
async def test_brain_passes_the_raw_question_to_the_llm():
    llm = ScriptedLLM("OK")
    brain = Brain(llm=llm, display=FakeDisplay())

    await brain.handle("what is a split-flap display")

    assert llm.prompts == ["what is a split-flap display"]
```

3. Replace `test_fake_llm_echoes_the_question` with:

```python
async def test_fake_llm_echoes_the_question():
    fake = FakeLLMClient()
    reply = await fake.complete("HELLO BOARD", max_chars=100)
    assert reply == "YOU SAID HELLO BOARD"
```

4. In `test_fake_llm_is_deterministic_and_fits_budget`, change both
   `fake.complete("PROMPT\nHELLO", max_chars=30)` calls to
   `fake.complete("HELLO", max_chars=30)`.

In `tests/test_anthropic_client.py`, add at the end:

```python
async def test_client_wraps_the_question_in_the_answer_prompt():
    from clapper_ai.llm.anthropic_client import ANSWER_PROMPT

    client, fake = make_client("PARIS")
    await client.complete("capital of france?", max_chars=132)

    sent = fake.calls[0]["messages"][0]["content"]
    assert "capital of france?" in sent
    assert "132" in sent  # the character budget is spelled out
    assert "{max_chars}" in ANSWER_PROMPT  # the constant stays tunable
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_brain.py tests/test_anthropic_client.py -q`
Expected: FAIL —
`test_brain_passes_the_raw_question_to_the_llm` fails (the Brain still wraps
the question in ANSWER_PROMPT), and
`test_client_wraps_the_question_in_the_answer_prompt` errors with
`ImportError: cannot import name 'ANSWER_PROMPT' from 'clapper_ai.llm.anthropic_client'`.
(The updated fake-echo tests may already pass — that's fine; the contract
change they encode is enforced by the brain test.)

- [ ] **Step 3: Implement the move**

In `src/clapper_ai/core/brain.py`, delete the `ANSWER_PROMPT` constant and change
`handle` to pass the raw text (full file below — module docstring updated too):

```python
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
```

In `src/clapper_ai/llm/fake.py`, replace the class body:

```python
class FakeLLMClient:
    async def complete(self, prompt: str, *, max_chars: int) -> str:
        question = prompt.strip()
        reply = f"YOU SAID {question}" if question else "HELLO FROM THE FAKE LLM"
        return reply[:max_chars]
```

(Also update the module docstring: it echoes the question, which is now the
whole prompt.)

In `src/clapper_ai/llm/anthropic_client.py`, add below the imports/docstring:

```python
# The answer-mode prompt. Kept in one constant so it's easy to find and tune.
ANSWER_PROMPT = (
    "You are answering on a tiny split-flap display. "
    "Reply in plain text only: no markdown, no line breaks, "
    "at most {max_chars} characters. Be concise and direct.\n"
    "{question}"
)
```

and change the `messages=` line in `complete` to:

```python
messages=[
    {
        "role": "user",
        "content": ANSWER_PROMPT.format(max_chars=max_chars, question=prompt),
    }
],
```

- [ ] **Step 4: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: all pass (still 44 tests — one brain test removed, one anthropic test added).

- [ ] **Step 5: Lint and commit**

```bash
.venv/bin/ruff check . && git add -A
git commit -m "refactor: move prompt ownership from Brain into LLM clients"
```

---

### Task 3: Brain branches on str vs LayoutSpec

**Files:**
- Modify: `src/clapper_ai/core/brain.py`
- Modify: `src/clapper_ai/core/interfaces.py`
- Test: `tests/test_brain.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_brain.py` (with the other imports:
`from clapper_ai.core.layout import ArtLayout, Line, TextLayout`):

```python
class ScriptedLayoutLLM:
    """Returns a LayoutSpec instead of a string."""

    def __init__(self, spec):
        self.spec = spec

    async def complete(self, prompt: str, *, max_chars: int):
        return self.spec


async def test_text_layout_reply_is_rendered():
    display = FakeDisplay(rows=1, cols=4)
    spec = TextLayout(type="text_layout", lines=[Line(text="HI", align="right")])
    brain = Brain(llm=ScriptedLayoutLLM(spec), display=display)

    await brain.handle("hi")

    assert display.rendered == [[[0, 0, 8, 9]]]


async def test_art_reply_is_rendered():
    display = FakeDisplay(rows=1, cols=2)
    spec = ArtLayout(type="art", grid=[[63, 67]])
    brain = Brain(llm=ScriptedLayoutLLM(spec), display=display)

    await brain.handle("paint something")

    assert display.rendered == [[[63, 67]]]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_brain.py -q`
Expected: the two new tests FAIL (`text_to_grid` receives a TextLayout and
crashes on `.upper()`).

- [ ] **Step 3: Implement the branch**

In `src/clapper_ai/core/brain.py`, add the import
`from clapper_ai.core.layout import render_layout` and change the middle of
`handle` to:

```python
        reply = await self.llm.complete(text, max_chars=rows * cols)
        if isinstance(reply, str):
            grid = text_to_grid(reply, rows, cols)
        else:
            grid = render_layout(reply, rows, cols)
        validate_grid(grid, rows, cols, self.allowed)
```

In `src/clapper_ai/core/interfaces.py`, add the import
`from clapper_ai.core.layout import LayoutSpec` and update `LLMClient`:

```python
class LLMClient(Protocol):
    """The model that turns a prompt into an answer.

    Returns either plain text (laid out by text_to_grid) or a LayoutSpec
    (the model designed the board itself; rendered by render_layout).
    """

    async def complete(self, prompt: str, *, max_chars: int) -> "str | LayoutSpec": ...
```

- [ ] **Step 4: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: all pass.

- [ ] **Step 5: Lint and commit**

```bash
.venv/bin/ruff check . && git add -A
git commit -m "feat: Brain renders LayoutSpec replies via render_layout"
```

---

### Task 4: Apology fallback on any LLM/render error

**Files:**
- Modify: `src/clapper_ai/core/brain.py`
- Test: `tests/test_brain.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_brain.py` (import `text_to_grid` and `blank_grid`:
`from clapper_ai.core.validate import text_to_grid` and
`from clapper_ai.core.grid import blank_grid`):

```python
class ExplodingLLM:
    async def complete(self, prompt: str, *, max_chars: int) -> str:
        raise RuntimeError("api down")


async def test_llm_error_renders_an_apology_instead_of_crashing():
    display = FakeDisplay(rows=6, cols=22)
    brain = Brain(llm=ExplodingLLM(), display=display)

    await brain.handle("hi")

    assert display.rendered == [text_to_grid("SORRY, TRY AGAIN", 6, 22)]


async def test_invalid_art_grid_renders_the_apology():
    display = FakeDisplay(rows=1, cols=2)
    bad = ArtLayout(type="art", grid=[[999, 999]])  # illegal codes
    brain = Brain(llm=ScriptedLayoutLLM(bad), display=display)

    await brain.handle("paint")

    assert display.rendered == [text_to_grid("SORRY, TRY AGAIN", 1, 2)]
```

Also **replace** `test_brain_validates_before_rendering` (the fallback changes
its expectation — a board that can't even show the apology gets a blank grid):

```python
async def test_restricted_board_falls_back_to_blank_grid():
    # allowed={0} can't show letters — not the reply, not the apology.
    display = FakeDisplay(rows=1, cols=2)
    brain = Brain(llm=ScriptedLLM("AB"), display=display, allowed={0})

    await brain.handle("hi")

    assert display.rendered == [blank_grid(1, 2)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_brain.py -q`
Expected: the three tests FAIL (exceptions propagate out of `handle`).

- [ ] **Step 3: Implement the fallback**

In `src/clapper_ai/core/brain.py`, add imports
`from clapper_ai.core.grid import blank_grid` and add the constant below
`ALLOWED_CODES` import block:

```python
# Shown when the LLM call or its layout fails — the board always responds.
FALLBACK_TEXT = "SORRY, TRY AGAIN"
```

Replace the body of `handle` with:

```python
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
```

- [ ] **Step 4: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: all pass.

- [ ] **Step 5: Lint and commit**

```bash
.venv/bin/ruff check . && git add -A
git commit -m "feat: Brain falls back to an apology grid when the LLM or layout fails"
```

---

### Task 5: SmartAnthropicClient — one call, web search, structured output

**Files:**
- Create: `src/clapper_ai/llm/anthropic_smart.py`
- Test: `tests/test_anthropic_smart.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_anthropic_smart.py`:

```python
"""Tests for SmartAnthropicClient (needs the `llm` extra installed)."""

import json

import pytest

pytest.importorskip("anthropic", reason="install the `llm` extra to test this")

from clapper_ai.core.layout import ArtLayout, TextLayout  # noqa: E402
from clapper_ai.llm.anthropic_smart import SmartAnthropicClient  # noqa: E402


class FakeMessages:
    def __init__(self, reply_text: str, stop_reason: str = "end_turn"):
        self.reply_text = reply_text
        self.stop_reason = stop_reason
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)

        class Block:
            type = "text"

        block = Block()
        block.text = self.reply_text

        class Response:
            content = [block]
            stop_reason = self.stop_reason

        return Response()


def make_client(reply: dict, stop_reason: str = "end_turn"):
    client = SmartAnthropicClient.__new__(SmartAnthropicClient)  # skip __init__
    client.model = SmartAnthropicClient.MODEL
    client.rows, client.cols = 6, 22
    fake = FakeMessages(json.dumps(reply), stop_reason)

    class FakeSDK:
        messages = fake

    client._client = FakeSDK()
    return client, fake


TEXT_REPLY = {
    "layout": {
        "type": "text_layout",
        "lines": [{"text": "18 MILLION", "align": "center", "color": None}],
    }
}
ART_REPLY = {"layout": {"type": "art", "grid": [[67] * 22 for _ in range(6)]}}


async def test_parses_a_text_layout_reply():
    client, _ = make_client(TEXT_REPLY)
    spec = await client.complete("population of the netherlands", max_chars=132)
    assert isinstance(spec, TextLayout)
    assert spec.lines[0].text == "18 MILLION"
    assert spec.lines[0].align == "center"


async def test_parses_an_art_reply():
    client, _ = make_client(ART_REPLY)
    spec = await client.complete("paint the great wave", max_chars=132)
    assert isinstance(spec, ArtLayout)
    assert len(spec.grid) == 6


async def test_request_describes_the_board_and_enables_search():
    client, fake = make_client(TEXT_REPLY)
    await client.complete("hello", max_chars=132)

    call = fake.calls[0]
    assert call["model"] == "claude-opus-4-8"
    assert "6" in call["system"] and "22" in call["system"]
    assert call["tools"][0]["name"] == "web_search"
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert call["messages"] == [{"role": "user", "content": "hello"}]


async def test_refusal_raises_so_the_brain_can_apologize():
    client, _ = make_client(TEXT_REPLY, stop_reason="refusal")
    with pytest.raises(RuntimeError, match="refus"):
        await client.complete("hello", max_chars=132)


async def test_malformed_layout_raises_so_the_brain_can_apologize():
    client, _ = make_client({"layout": {"type": "nonsense"}})
    with pytest.raises(Exception):
        await client.complete("hello", max_chars=132)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_anthropic_smart.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'clapper_ai.llm.anthropic_smart'`

- [ ] **Step 3: Write the implementation**

Create `src/clapper_ai/llm/anthropic_smart.py`:

```python
"""Smart answers: Claude answers the question AND designs the board.

One API call with three ingredients:
- a system prompt describing the board (size, tiles, colors),
- the web_search server tool for live facts (scores, news),
- a JSON schema forcing the reply into a LayoutSpec shape.

Optional: needs the `llm` extra and ANTHROPIC_API_KEY, like anthropic_client.
Select with `llm.type: anthropic-smart` in config.yaml.
"""

import json

from pydantic import TypeAdapter

from clapper_ai.core.layout import ArtLayout, LayoutSpec, TextLayout

SYSTEM_PROMPT = (
    "You control a split-flap display of {rows} rows x {cols} columns. Each tile "
    "shows one of: blank (code 0), A-Z (codes 1-26), digits 1-9 then 0 (codes "
    "27-36), or a solid color tile: red 63, orange 64, yellow 65, green 66, "
    "blue 67, violet 68, white 69.\n"
    "Answer the user's question, then design how it should look on the board.\n"
    "- Questions: reply with type 'text_layout'. At most {rows} lines of {cols} "
    "characters. Center titles, use an empty line with a color as a divider or "
    "accent bar. Keep wording short enough to fit.\n"
    "- Art requests (e.g. 'paint the great wave'): reply with type 'art' and a "
    "grid of exactly {rows} rows x {cols} tile codes, mostly color tiles.\n"
    "Use web search when the question needs current information. If you cannot "
    "answer, say so briefly on the board."
)

_COLOR_NAMES = ["red", "orange", "yellow", "green", "blue", "violet", "white"]

LAYOUT_SCHEMA = {
    "type": "object",
    "properties": {
        "layout": {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "type": {"const": "text_layout"},
                        "lines": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "align": {
                                        "type": "string",
                                        "enum": ["left", "center", "right"],
                                    },
                                    "color": {
                                        "anyOf": [
                                            {"type": "string", "enum": _COLOR_NAMES},
                                            {"type": "null"},
                                        ]
                                    },
                                },
                                "required": ["text", "align", "color"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["type", "lines"],
                    "additionalProperties": False,
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {"const": "art"},
                        "grid": {
                            "type": "array",
                            "items": {"type": "array", "items": {"type": "integer"}},
                        },
                    },
                    "required": ["type", "grid"],
                    "additionalProperties": False,
                },
            ]
        }
    },
    "required": ["layout"],
    "additionalProperties": False,
}
# The schema can't pin grid dimensions or code ranges (JSON Schema numeric
# constraints aren't supported by structured outputs) — render_layout and
# validate_grid enforce those downstream.

_LAYOUT_ADAPTER: TypeAdapter = TypeAdapter(LayoutSpec)


class SmartAnthropicClient:
    MODEL = "claude-opus-4-8"

    def __init__(self, rows: int, cols: int, model: str = MODEL):
        try:
            from anthropic import AsyncAnthropic
        except ImportError as error:
            raise SystemExit(
                "The anthropic package is not installed. "
                'Run: pip install "clapper-ai[llm]"'
            ) from error
        self._client = AsyncAnthropic()
        self.model = model
        self.rows = rows
        self.cols = cols

    async def complete(self, prompt: str, *, max_chars: int) -> TextLayout | ArtLayout:
        response = await self._client.messages.create(
            model=self.model,
            max_tokens=4096,  # search summaries + a full art grid fit easily
            system=SYSTEM_PROMPT.format(rows=self.rows, cols=self.cols),
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}],
            output_config={"format": {"type": "json_schema", "schema": LAYOUT_SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
        texts = [block.text for block in response.content if block.type == "text"]
        if response.stop_reason == "refusal" or not texts:
            # The Brain catches this and shows its apology grid.
            raise RuntimeError(f"Model refused or gave no answer ({response.stop_reason})")
        data = json.loads(texts[-1])  # last text block: search blocks may precede it
        return _LAYOUT_ADAPTER.validate_python(data["layout"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_anthropic_smart.py -q`
Expected: `5 passed`

- [ ] **Step 5: Lint and commit**

```bash
.venv/bin/ruff check . && git add -A
git commit -m "feat: add SmartAnthropicClient — web search + structured LayoutSpec output"
```

---

### Task 6: Config wiring — `llm.type: anthropic-smart`

**Files:**
- Modify: `src/clapper_ai/__main__.py`
- Modify: `config.example.yaml`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
def test_smart_anthropic_gets_board_dimensions_from_config(tmp_path, monkeypatch):
    pytest.importorskip("anthropic", reason="install the `llm` extra to test this")
    from clapper_ai.llm.anthropic_smart import SmartAnthropicClient

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-real")
    path = write_config(
        tmp_path,
        """
        llm: {type: anthropic-smart}
        board: {rows: 3, cols: 11}
        """,
    )

    _, _, llm = build_adapters(load_config(path))

    assert isinstance(llm, SmartAnthropicClient)
    assert (llm.rows, llm.cols) == (3, 11)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_config.py -q`
Expected: FAIL — `SystemExit: Unknown llm type 'anthropic-smart' ...`

- [ ] **Step 3: Implement**

In `src/clapper_ai/__main__.py`, add below `_make_anthropic`:

```python
def _make_smart_anthropic(config: "AppConfig"):
    from clapper_ai.llm.anthropic_smart import SmartAnthropicClient

    return SmartAnthropicClient(rows=config.board.rows, cols=config.board.cols)
```

and extend the registry:

```python
LLMS = {
    "fake": lambda config: FakeLLMClient(),
    "anthropic": _make_anthropic,
    "anthropic-smart": _make_smart_anthropic,
}
```

In `config.example.yaml`, update the llm comment block:

```yaml
llm:
  # Valid types: fake, anthropic, anthropic-smart
  #   fake            — deterministic echo, no API key needed (default)
  #   anthropic       — real answers as plain text; needs `pip install ".[llm]"`
  #                     and the ANTHROPIC_API_KEY environment variable
  #   anthropic-smart — real answers AND the AI designs the board layout
  #                     (centered text, color accents, tile art); can search
  #                     the web for live facts. Same requirements as anthropic.
  type: fake
```

- [ ] **Step 4: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: all pass.

- [ ] **Step 5: Lint and commit**

```bash
.venv/bin/ruff check . && git add -A
git commit -m "feat: wire anthropic-smart LLM type through config"
```

---

### Task 7: Docs touch-up and final verification

**Files:**
- Modify: `README.md` (Real answers section)
- Modify: `docs/architecture.md` (flow section)

- [ ] **Step 1: Update README**

In `README.md`, replace the last sentence of the "Real answers" section
("then set `llm.type: anthropic` ... only change.") with:

```markdown
then set `llm.type: anthropic` in `config.yaml` for plain-text answers, or
`llm.type: anthropic-smart` to let the AI also design the board — centered
layouts with color accents, web search for live facts, and full-tile art
("paint the great wave"). Either way, that's the only change.
```

- [ ] **Step 2: Update architecture doc**

In `docs/architecture.md`, add after the "The flow" diagram section:

```markdown
### Smart mode (`llm.type: anthropic-smart`)

One API call answers the question (using web search when it needs live facts)
and returns a `LayoutSpec` instead of plain text: either `text_layout` (lines
with alignment and color accents) or `art` (a full grid of tile codes).
`core/layout.py` renders either shape deterministically — the model chooses
the design, our code does the tile arithmetic — and `validate_grid` still
gates the result. If the call or the layout fails, the Brain shows
`SORRY, TRY AGAIN` instead of crashing.
```

- [ ] **Step 3: Full verification**

```bash
.venv/bin/pytest -q          # expected: all pass
.venv/bin/ruff check .       # expected: All checks passed!
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "docs: document anthropic-smart mode"
```

- [ ] **Step 5: Manual live check (only if a real key is available)**

Not automatable without credentials. With a key exported and
`pip install -e ".[llm]"` done, set `llm.type: anthropic-smart` in
`config.yaml`, run `PORT=8123 python -m clapper_ai`, and try:

1. `what is the population of the netherlands` — expect a designed text layout
2. `what was the score of the last netherlands football game` — expect web
   search to fire and a score layout
3. `create the art piece the great wave` — expect a blue/white tile painting

If the model misbehaves (cramped layouts, wrong shapes), tune `SYSTEM_PROMPT`
in `src/clapper_ai/llm/anthropic_smart.py` — that's the intended tuning point.
