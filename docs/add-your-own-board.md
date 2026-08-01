# Add your own board

A display is any object that satisfies `DisplaySink`
(`src/clapper_ai/application/ports/display_sink.py`):

```python
class DisplaySink(Protocol):
    rows: int
    cols: int

    async def render(self, grid: Grid) -> None: ...
```

`render` receives a grid that has **already passed `validate_grid`** — exactly
`rows × cols`, only codes your board allows. Your job is purely: show it.
How you animate (or don't) is entirely yours.

## Worked example: a terminal board

A complete, working display in ~20 lines. Save as
`src/clapper_ai/adapters/displays/terminal.py`:

```python
"""Prints each grid to the terminal. The simplest possible DisplaySink."""

from clapper_ai.domain.tile_codes import CODE_TO_CHAR
from clapper_ai.domain.grid import Grid


class TerminalBoard:
    def __init__(self, rows: int = 6, cols: int = 22):
        self.rows = rows
        self.cols = cols

    async def render(self, grid: Grid) -> None:
        print("┌" + "─" * self.cols + "┐")
        for row in grid:
            line = "".join(CODE_TO_CHAR.get(code, "▪") for code in row)
            print(f"│{line}│")
        print("└" + "─" * self.cols + "┘")
```

## Register it

Add one line to the `DISPLAYS` registry in `src/clapper_ai/__main__.py`:

```python
DISPLAYS = {
    "virtual": lambda config: VirtualBoard(rows=config.board.rows, cols=config.board.cols),
    "terminal": lambda config: TerminalBoard(rows=config.board.rows, cols=config.board.cols),
}
```

## Select it

```yaml
# config.yaml
display:
  type: terminal
```

Run `python -m clapper_ai`. That's the whole procedure: one file, one registry
line, one config value. The use case, inputs, and LLMs are untouched.

## Notes for hardware boards

- Talk to your hardware inside `render()` — serial write, HTTP call to a
  Vestaboard, whatever. It's `async`, so use `asyncio.to_thread(...)` for
  blocking I/O.
- If your board supports fewer tile codes than the full map, pass your own
  `allowed` set to `AnswerQuestion(...)` so `validate_grid` protects you.
- Need extra dependencies? Put them behind an optional extra in
  `pyproject.toml` (see the `vestaboard` placeholder) so the base install
  stays tiny.
