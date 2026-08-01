# Package Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dissolve `core/` into `domain/`, `application/` and `adapters/` so the clean-architecture layers are readable from the directory tree.

**Architecture:** Behaviour-preserving refactor — moves, renames, and two file splits. The dependency rule already holds; this makes it visible. Ports move inside `application/` because the use case owns the interfaces it depends on.

**Tech Stack:** Python 3.14, uv, pytest, ruff, pydantic.

**Spec:** `docs/superpowers/specs/2026-08-01-package-restructure-design.md`

---

## READ THIS FIRST: this is a refactor, not a feature

**Do not write failing tests first.** Normal TDD does not apply here. Nothing about
this change alters behaviour, so there is no new behaviour to drive out with a test.

The discipline instead is:

> The existing 69 tests must pass, unchanged in count, at every single commit.

If the count changes, you have altered behaviour and something is wrong. If a test
needs editing beyond an import path or a renamed symbol, stop and re-read the spec.

Baseline before starting anything:

```bash
uv sync --all-extras --locked
uv run pytest -q
```

Expected: `69 passed`. If it is not 69, stop — the tree is not in the state this
plan assumes.

---

## File Structure

**Created:**

| File | Responsibility |
|---|---|
| `src/clapper_ai/domain/__init__.py` | empty package marker |
| `src/clapper_ai/domain/tile_codes.py` | tile alphabet — char/colour ↔ int code (was `core/codes.py`) |
| `src/clapper_ai/domain/grid.py` | the `Grid` type and `blank_grid` (moved unchanged) |
| `src/clapper_ai/domain/layout.py` | `LayoutSpec` models + `render_layout` (moved unchanged) |
| `src/clapper_ai/domain/text_layout.py` | `text_to_grid`, `_word_wrap` — text → grid transformation |
| `src/clapper_ai/domain/grid_rules.py` | `validate_grid` — the invariant gate |
| `src/clapper_ai/application/__init__.py` | empty package marker |
| `src/clapper_ai/application/interactors/__init__.py` | empty package marker |
| `src/clapper_ai/application/interactors/answer_question.py` | the use case (was `core/brain.py`) |
| `src/clapper_ai/application/ports/__init__.py` | empty package marker |
| `src/clapper_ai/application/ports/llm_client.py` | driven port — the model |
| `src/clapper_ai/application/ports/display_sink.py` | driven port — the board |
| `src/clapper_ai/application/ports/input_source.py` | port of the runner (see docstring) |
| `src/clapper_ai/adapters/__init__.py` | empty package marker |

**Moved:** `inputs/`, `displays/`, `llm/` → under `adapters/`; `llm/fake.py` → `adapters/llm/echo.py`.

**Deleted:** `src/clapper_ai/core/` entirely.

---

### Task 1: Create the domain layer

**Files:**
- Create: `src/clapper_ai/domain/__init__.py`, `src/clapper_ai/domain/grid_rules.py`
- Move: `core/codes.py` → `domain/tile_codes.py`, `core/grid.py` → `domain/grid.py`, `core/layout.py` → `domain/layout.py`, `core/validate.py` → `domain/text_layout.py`
- Modify: `core/brain.py:10-14`, `core/interfaces.py:10-11`, `displays/virtual/sink.py:8`, `llm/anthropic_smart.py:17`, and six test files

- [ ] **Step 1: Create the package and move the four modules**

```bash
mkdir -p src/clapper_ai/domain
touch src/clapper_ai/domain/__init__.py
git mv src/clapper_ai/core/codes.py    src/clapper_ai/domain/tile_codes.py
git mv src/clapper_ai/core/grid.py     src/clapper_ai/domain/grid.py
git mv src/clapper_ai/core/layout.py   src/clapper_ai/domain/layout.py
git mv src/clapper_ai/core/validate.py src/clapper_ai/domain/text_layout.py
```

- [ ] **Step 2: Cut `validate_grid` out into its own module**

Create `src/clapper_ai/domain/grid_rules.py` with exactly this content:

```python
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
```

- [ ] **Step 3: Trim `text_layout.py` to only the text transformation**

In `src/clapper_ai/domain/text_layout.py`, replace the module docstring and imports
(lines 1–4) with:

```python
"""Turn a line of text into a grid of tile codes.

Uppercases, word-wraps to the column width, pads and truncates to the board.
"""

from clapper_ai.domain.grid import Grid
from clapper_ai.domain.tile_codes import BLANK, CHAR_TO_CODE
```

Then delete the entire `validate_grid` function from the bottom of the file (it now
lives in `grid_rules.py`). `text_to_grid` and `_word_wrap` stay exactly as they are.

- [ ] **Step 4: Rewrite the mechanical import paths**

```bash
grep -rl "clapper_ai\.core\.codes"  --include=*.py src tests | xargs sed -i 's/clapper_ai\.core\.codes/clapper_ai.domain.tile_codes/g'
grep -rl "clapper_ai\.core\.grid"   --include=*.py src tests | xargs sed -i 's/clapper_ai\.core\.grid/clapper_ai.domain.grid/g'
grep -rl "clapper_ai\.core\.layout" --include=*.py src tests | xargs sed -i 's/clapper_ai\.core\.layout/clapper_ai.domain.layout/g'
```

- [ ] **Step 5: Rewrite the four single-symbol `validate` imports**

```bash
sed -i 's|from clapper_ai\.core\.validate import text_to_grid|from clapper_ai.domain.text_layout import text_to_grid|' tests/test_brain.py tests/test_text_to_grid.py
sed -i 's|from clapper_ai\.core\.validate import validate_grid|from clapper_ai.domain.grid_rules import validate_grid|' tests/test_layout.py tests/test_validate.py
```

- [ ] **Step 6: Split the one import line that takes both symbols**

In `src/clapper_ai/core/brain.py`, replace this single line:

```python
from clapper_ai.core.validate import text_to_grid, validate_grid
```

with these two:

```python
from clapper_ai.domain.grid_rules import validate_grid
from clapper_ai.domain.text_layout import text_to_grid
```

- [ ] **Step 7: Rename the test file that mirrors the split**

```bash
git mv tests/test_validate.py tests/test_grid_rules.py
```

- [ ] **Step 8: Fix import ordering and verify**

```bash
uv run ruff check --fix .
uv run ruff check .
uv run pytest -q
```

Expected: `All checks passed!` and `69 passed`. A `ModuleNotFoundError` here means a
path in step 4 or 5 was missed — re-run `grep -rn "clapper_ai.core" --include=*.py src tests`
to find it.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "refactor: extract the domain layer out of core

codes.py becomes tile_codes.py, and validate.py splits into text_layout.py
(the text-to-grid transformation) and grid_rules.py (the invariant gate) —
the old filename described the smaller half."
```

---

### Task 2: Create the ports

**Files:**
- Create: `src/clapper_ai/application/__init__.py`, `application/ports/__init__.py`, and three port modules
- Delete: `src/clapper_ai/core/interfaces.py`
- Modify: `src/clapper_ai/core/brain.py:12`

- [ ] **Step 1: Create the packages**

```bash
mkdir -p src/clapper_ai/application/ports
touch src/clapper_ai/application/__init__.py
touch src/clapper_ai/application/ports/__init__.py
```

- [ ] **Step 2: Create `llm_client.py`**

```python
"""Driven port: the model that turns a prompt into an answer.

AnswerQuestion calls out through this. Implementations live in adapters/llm/.
"""

from typing import Protocol

from clapper_ai.domain.layout import LayoutSpec


class LLMClient(Protocol):
    """Returns either plain text (laid out by text_to_grid) or a LayoutSpec
    (the model designed the board itself; rendered by render_layout)."""

    async def complete(self, prompt: str, *, max_chars: int) -> str | LayoutSpec: ...
```

- [ ] **Step 3: Create `display_sink.py`**

```python
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
```

- [ ] **Step 4: Create `input_source.py`, with the asymmetry documented**

```python
"""Port for where prompts come from (keyboard now; mic or phone later).

Note the asymmetry with the other two ports in this package: LLMClient and
DisplaySink are driven ports of AnswerQuestion — the use case calls out
through them. InputSource is not. It is consumed by the run loop in
__main__.py, which pulls a string and hands it to the use case, so it is a
port of the driving side.

It lives here for cohesion, not because the interactor owns it. Resolving
that properly means flipping input from pull to push so the adapter calls
execute() itself — a behavioural change, deliberately out of scope here.
"""

from typing import Protocol


class InputSource(Protocol):
    async def listen(self) -> str:
        """Block until the user says or types something; return the transcript."""
        ...
```

- [ ] **Step 5: Delete the old interfaces module and repoint its importer**

```bash
git rm src/clapper_ai/core/interfaces.py
```

In `src/clapper_ai/core/brain.py`, replace:

```python
from clapper_ai.core.interfaces import DisplaySink, LLMClient
```

with:

```python
from clapper_ai.application.ports.display_sink import DisplaySink
from clapper_ai.application.ports.llm_client import LLMClient
```

- [ ] **Step 6: Verify**

```bash
uv run ruff check --fix . && uv run ruff check . && uv run pytest -q
```

Expected: `All checks passed!` and `69 passed`.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: split interfaces.py into application/ports

One file per port, so the path carries the taxonomy and each protocol can
document itself. input_source.py records why it sits beside two ports that
belong to a different caller."
```

---

### Task 3: Move the use case and rename it

**Files:**
- Move: `core/brain.py` → `application/interactors/answer_question.py`
- Move: `tests/test_brain.py` → `tests/test_answer_question.py`
- Modify: `src/clapper_ai/__main__.py:17` and its call site

- [ ] **Step 1: Move both files**

```bash
mkdir -p src/clapper_ai/application/interactors
touch src/clapper_ai/application/interactors/__init__.py
git mv src/clapper_ai/core/brain.py src/clapper_ai/application/interactors/answer_question.py
git mv tests/test_brain.py tests/test_answer_question.py
```

- [ ] **Step 2: Rename the class, the method, and the module docstring**

In `src/clapper_ai/application/interactors/answer_question.py`, replace the docstring
first line and the class declaration. The docstring becomes:

```python
"""The AnswerQuestion use case: a question in, a grid on the display.

Hand the question to the LLM client, lay the reply out, gate it with
validate_grid, render it. Each LLM client owns its own prompting; the use
case knows nothing about keyboards, browsers, hardware — or prompt wording.
If the LLM call or its layout fails, the board still responds: it falls back
to an apology, or — if even that cannot pass validation — a blank grid.
"""
```

Then:

```bash
sed -i 's/^class Brain:/class AnswerQuestion:/' src/clapper_ai/application/interactors/answer_question.py
sed -i 's/    async def handle(self, text: str) -> None:/    async def execute(self, question: str) -> None:/' src/clapper_ai/application/interactors/answer_question.py
```

The method body references the parameter once, at the `self.llm.complete(text, ...)`
call. Change that occurrence to `question`:

```bash
sed -i 's/reply = await self\.llm\.complete(text, max_chars=rows \* cols)/reply = await self.llm.complete(question, max_chars=rows * cols)/' src/clapper_ai/application/interactors/answer_question.py
```

- [ ] **Step 3: Update every reference across src and tests**

```bash
grep -rl "clapper_ai\.core\.brain" --include=*.py src tests | xargs sed -i 's/from clapper_ai\.core\.brain import Brain/from clapper_ai.application.interactors.answer_question import AnswerQuestion/'
grep -rl "\bBrain\b" --include=*.py src tests | xargs sed -i 's/\bBrain\b/AnswerQuestion/g'
grep -rl "\.handle(" --include=*.py src tests | xargs sed -i 's/\.handle(/.execute(/g'
```

- [ ] **Step 4: Verify no stale names remain**

```bash
grep -rn "\bBrain\b\|\.handle(" --include=*.py src tests | grep -v __pycache__
```

Expected: no output. Any hit is a rename the previous step missed.

- [ ] **Step 5: Run the suite**

```bash
uv run ruff check --fix . && uv run ruff check . && uv run pytest -q
```

Expected: `All checks passed!` and `69 passed`.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: Brain becomes the AnswerQuestion interactor

Brain was a metaphor and handle() named nothing. The package path already
says which ring this is, so the class needs no UseCase suffix."
```

---

### Task 4: Move the adapters

**Files:**
- Move: `inputs/`, `displays/`, `llm/` → `adapters/`; `llm/fake.py` → `adapters/llm/echo.py`
- Modify: every importer in `src/` and `tests/`

- [ ] **Step 1: Move the three packages**

```bash
mkdir -p src/clapper_ai/adapters
touch src/clapper_ai/adapters/__init__.py
git mv src/clapper_ai/inputs   src/clapper_ai/adapters/inputs
git mv src/clapper_ai/displays src/clapper_ai/adapters/displays
git mv src/clapper_ai/llm      src/clapper_ai/adapters/llm
git mv src/clapper_ai/adapters/llm/fake.py src/clapper_ai/adapters/llm/echo.py
```

- [ ] **Step 2: Rewrite the import paths**

```bash
grep -rl "clapper_ai\.\(inputs\|displays\|llm\)" --include=*.py src tests \
  | xargs sed -i -e 's/clapper_ai\.inputs/clapper_ai.adapters.inputs/g' \
                 -e 's/clapper_ai\.displays/clapper_ai.adapters.displays/g' \
                 -e 's/clapper_ai\.llm/clapper_ai.adapters.llm/g'
```

- [ ] **Step 3: Rename the echo module and its class**

```bash
grep -rl "adapters\.llm\.fake\|FakeLLMClient" --include=*.py src tests \
  | xargs sed -i -e 's/adapters\.llm\.fake/adapters.llm.echo/g' \
                 -e 's/\bFakeLLMClient\b/EchoLLMClient/g'
```

Then update the docstring in `src/clapper_ai/adapters/llm/echo.py` to:

```python
"""The default LLM: no network, no key, fully deterministic.

It echoes the whole prompt back, so the board visibly reacts to whatever you
type — good enough to demo the pipeline without an API key.

Named echo rather than fake because it is a real shipped adapter, not a test
double: config.yaml selects it by default.
"""
```

- [ ] **Step 4: Confirm the config key was NOT renamed**

```bash
grep -n '"fake"' src/clapper_ai/__main__.py
grep -n "type: fake" config.yaml
```

Expected: the registry key `"fake"` and the config value `type: fake` both still
present. Per the spec, only the class and module were renamed — the config value is
public interface documented in README and QUICKSTART.

- [ ] **Step 5: Verify**

```bash
uv run ruff check --fix . && uv run ruff check . && uv run pytest -q
```

Expected: `All checks passed!` and `69 passed`.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: group the adapters under adapters/

inputs, displays and llm are the same ring, and the parent now says so.
fake.py becomes echo.py: it is the default production adapter, not a test
double, and 'fake' is test-double vocabulary."
```

---

### Task 5: Delete core and tidy the tile alphabet

**Files:**
- Delete: `src/clapper_ai/core/`
- Modify: `src/clapper_ai/domain/tile_codes.py:11-23`

- [ ] **Step 1: Confirm core is empty, then delete it**

```bash
ls -A src/clapper_ai/core/
```

Expected: only `__init__.py` (and possibly `__pycache__`). If any `.py` module
remains, a previous task is incomplete — stop and finish it.

```bash
git rm src/clapper_ai/core/__init__.py
rm -rf src/clapper_ai/core
```

- [ ] **Step 2: Capture the tile alphabet before changing it**

```bash
uv run python -c "from clapper_ai.domain.tile_codes import CHAR_TO_CODE, COLOR_CODES, ALLOWED_CODES, CODE_TO_CHAR; import json; print(json.dumps({'char': CHAR_TO_CODE, 'color': COLOR_CODES, 'allowed': sorted(ALLOWED_CODES), 'reverse': {str(k): v for k, v in CODE_TO_CHAR.items()}}, sort_keys=True))" > before.json
```

- [ ] **Step 3: Replace the import-time loops with comprehensions**

In `src/clapper_ai/domain/tile_codes.py`, delete the `TODO` paragraph from the module
docstring (lines 11–12 of the original), and replace this block:

```python
CHAR_TO_CODE: dict[str, int] = {" ": BLANK}
for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", start=1):
    CHAR_TO_CODE[letter] = i
for i, digit in enumerate("1234567890", start=27):
    CHAR_TO_CODE[digit] = i
```

with:

```python
CHAR_TO_CODE: dict[str, int] = {
    " ": BLANK,
    **{letter: i for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", start=1)},
    **{digit: i for i, digit in enumerate("1234567890", start=27)},
}
```

- [ ] **Step 4: Prove the alphabet is byte-identical**

```bash
uv run python -c "from clapper_ai.domain.tile_codes import CHAR_TO_CODE, COLOR_CODES, ALLOWED_CODES, CODE_TO_CHAR; import json; print(json.dumps({'char': CHAR_TO_CODE, 'color': COLOR_CODES, 'allowed': sorted(ALLOWED_CODES), 'reverse': {str(k): v for k, v in CODE_TO_CHAR.items()}}, sort_keys=True))" > after.json
diff before.json after.json && echo "IDENTICAL"
```

Expected: `IDENTICAL`, with no diff output. If they differ, revert step 3 — the
comprehension is wrong.

```bash
rm before.json after.json
```

- [ ] **Step 5: Verify**

```bash
uv run ruff check --fix . && uv run ruff check . && uv run pytest -q
```

Expected: `All checks passed!` and `69 passed`.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: delete core/, build the tile alphabet declaratively

The constants were assembled by loops mutating a dict at import time; the
values are unchanged, verified by diffing the built maps before and after."
```

---

### Task 6: Update the documentation

**Files:**
- Modify: `README.md`, `CONTRIBUTING.md`, `docs/architecture.md`, `docs/add-your-own-board.md`, `docs/add-your-own-input.md`, `docs/character-codes.md`

- [ ] **Step 1: Find every stale reference**

```bash
grep -rn "core/\|clapper_ai\.core\|codes\.py\|validate\.py\|fake\.py\|interfaces\.py\|\bBrain\b\|FakeLLMClient\|src/clapper_ai/\(inputs\|displays\|llm\)" \
  --include=*.md --include=*.js --include=*.html . | grep -v "docs/superpowers\|\.venv"
```

**Match symbols, not only paths.** An earlier version of this grep listed only the
files being moved, which missed renamed *classes*. `docs/architecture.md` names
`FakeLLMClient` in its port table — that class is now `EchoLLMClient`, and a
path-only pattern does not see it.

**Note the non-markdown includes.** `src/clapper_ai/adapters/displays/virtual/static/board.js`
carries the tile table and points at the old module in two comments:

```
board.js:4  // Tile codes mirror src/clapper_ai/core/codes.py:
board.js:9  // --- code table (mirror of core/codes.py) ---
```

Both must become `src/clapper_ai/domain/tile_codes.py` and `domain/tile_codes.py`.
A markdown-only sweep misses them, and they point at a file that no longer exists
after Task 5.

Every hit is a line to fix. The counts are known, so you can check yourself off:

| File | Stale references |
|---|---|
| `README.md` | 5 |
| `CONTRIBUTING.md` | 3 |
| `docs/architecture.md` | 5 |
| `docs/add-your-own-board.md` | 6 |
| `docs/add-your-own-input.md` | 2 |
| `docs/character-codes.md` | 3 |

Total 24. Steps 2–6 below cover them; step 7 proves none were missed.

- [ ] **Step 2: Update the README project-layout block**

Replace the layout block under `## Project layout` with:

```
config.yaml            pick your input / display / llm here
src/clapper_ai/
  domain/              tile codes, Grid, LayoutSpec, text layout, grid rules
  application/
    interactors/       AnswerQuestion — one turn, question to board
    ports/             the three protocols the app speaks
  adapters/
    inputs/            InputSource adapters (text_input.py today)
    displays/          DisplaySink adapters (virtual/ today)
    llm/               LLMClient adapters (echo.py, anthropic_client.py)
docs/                  architecture + how to add your own device
tests/
```

- [ ] **Step 3: Relabel the README diagram**

In the three-box diagram, change the middle box label from `BRAIN` to `ANSWER`, and
change the line `│  text → tile grid │` beneath it to `│  question → grid   │`,
keeping the box borders aligned.

- [ ] **Step 4: Update the adapter paths in prose**

The three bullets under the diagram become:

```markdown
- `src/clapper_ai/adapters/inputs/` — one file per input device
- `src/clapper_ai/adapters/displays/` — one folder per display device
- `src/clapper_ai/domain/` + `src/clapper_ai/application/` — the core; never imports an adapter
```

- [ ] **Step 5: Update CONTRIBUTING ground rules**

Replace the `interfaces.py` reference with the new port paths, and the adapter paths
in the "New device" rule:

```markdown
- **The core never imports a concrete adapter.** `AnswerQuestion` talks only to the
  `InputSource`, `DisplaySink`, and `LLMClient` protocols in
  `src/clapper_ai/application/ports/`.
- **New device = one new file + one config line.** Add an input under
  `src/clapper_ai/adapters/inputs/`, a display under
  `src/clapper_ai/adapters/displays/`, register it in `src/clapper_ai/__main__.py`,
  done. See `docs/add-your-own-board.md`.
```

- [ ] **Step 6: Update the three docs files**

In `docs/add-your-own-board.md` and `docs/add-your-own-input.md`, update every path
found in step 1 to its `adapters/` equivalent and every `interfaces.py` reference to
the matching `application/ports/` module. In `docs/architecture.md`, replace every
occurrence of "the Brain" with "AnswerQuestion" and update the module paths. In
`docs/character-codes.md`, change `codes.py` to `domain/tile_codes.py`.

- [ ] **Step 7: Confirm nothing stale is left**

Re-run step 1's pattern, character for character:

```bash
grep -rn "core/\|clapper_ai\.core\|codes\.py\|validate\.py\|fake\.py\|interfaces\.py\|\bBrain\b\|FakeLLMClient\|src/clapper_ai/\(inputs\|displays\|llm\)" \
  --include=*.md --include=*.js --include=*.html . | grep -v "docs/superpowers\|\.venv"
```

Expected: no output.

**It must be the same pattern as step 1, not a subset.** A verification grep narrower
than the search grep cannot prove the search was complete — it returns "no output" for
references it was never looking for. Note that after Task 4, `src/clapper_ai/adapters/displays/…`
no longer matches the `src/clapper_ai/\(inputs\|displays\|llm\)` alternation, so that
clause is a genuine must-be-zero check on the moved paths rather than only a find-time net.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "docs: update paths and names for the new layout"
```

---

### Task 7: Final verification

- [ ] **Step 1: Prove the dependency rule still holds**

```bash
grep -rn "adapters" src/clapper_ai/domain src/clapper_ai/application | grep -v __pycache__
```

Expected: no output. The inner rings must not name the outer one.

- [ ] **Step 2: Prove no import escaped**

```bash
grep -rn "clapper_ai\.core" --include=*.py --include=*.md . | grep -v "\.venv\|docs/superpowers\|__pycache__"
```

Expected: no output.

- [ ] **Step 3: Full clean-install run, exactly as CI does it**

```bash
uv sync --all-extras --locked
uv run ruff check .
uv run pytest -q
```

Expected: `All checks passed!` and `69 passed`.

- [ ] **Step 4: Prove the app still boots**

```bash
uv sync
timeout 25 ./.venv/Scripts/python.exe -m clapper_ai < /dev/null
uv sync --all-extras --locked
```

Expected: prints the board URL, then `Bye.` on EOF, exit 0.

- [ ] **Step 5: Push and confirm CI is green**

```bash
git push
gh run list --limit 1
```

Expected: the newest CI run reports `completed  success`. If it fails, read the log
with `gh run view <id> --log` before making further changes.
