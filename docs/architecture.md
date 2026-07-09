# Architecture

## One contract, three seams

Every component communicates through a single data structure:

```python
Grid = list[list[int]]   # rows × cols; each int is one tile code
```

Around that contract sit three protocols (`src/clapper_ai/core/interfaces.py`):

| Protocol | Job | Today's adapter |
|---|---|---|
| `InputSource` | `listen() -> str` — wait for an utterance | `TextInput` (stdin) |
| `LLMClient` | `complete(prompt, max_chars) -> str` | `FakeLLMClient`, `AnthropicClient` |
| `DisplaySink` | `render(grid)` — show it, own the animation | `VirtualBoard` (browser) |

The `Brain` (`core/brain.py`) depends **only** on these protocols. It never
imports a concrete adapter, which is what keeps the ends swappable.

## The flow

```
TextInput.listen()          "what is rust"
        │
        ▼
Brain.handle(text)          hands the question to the LLM client (each
                            client owns its own prompt)
        │
        ▼
LLMClient.complete()        "A SYSTEMS LANGUAGE ..."
        │
        ▼
text_to_grid()              uppercase, word-wrap, pad, truncate → Grid
        │
        ▼
validate_grid()             exact dimensions? every code allowed?  ← safety gate
        │
        ▼
DisplaySink.render(grid)    VirtualBoard pushes JSON over WebSocket;
                            board.js flips the changed tiles
```

`validate_grid` is deliberately the last step before the display: no matter
what an LLM or a future adapter produces, a display only ever receives a grid
that is exactly the right shape with only codes it supports.

### Smart mode (`llm.type: anthropic-smart`)

One API call answers the question (using web search when it needs live facts)
and returns a `LayoutSpec` instead of plain text: either `text_layout` (lines
with alignment and color accents) or `art` (a full grid of tile codes).
`core/layout.py` renders either shape deterministically — the model chooses
the design, our code does the tile arithmetic — and `validate_grid` still
gates the result. If the call or the layout fails, the Brain shows
`SORRY, TRY AGAIN` instead of crashing.

## Wiring

`__main__.py` reads `config.yaml` (validated by a Pydantic model), looks the
three `type` names up in small registries (`INPUTS`, `DISPLAYS`, `LLMS`), and
runs the loop:

```python
while True:
    text = await source.listen()
    await brain.handle(text)
```

When the display is the `VirtualBoard`, it also starts a Uvicorn server that
serves the static page and the `/ws` WebSocket.

## The virtual board

- `displays/virtual/sink.py` — `VirtualBoard` keeps the latest grid and a set
  of connected sockets; `render()` broadcasts `{rows, cols, grid}` as JSON.
- `displays/virtual/server.py` — FastAPI app: `GET /` serves the page,
  `/ws` attaches a browser to the board. A tab that connects late immediately
  receives the current grid.
- `static/board.js` — a `<canvas>`, no build step. Each tile that changed
  flips (scale-Y fold, slightly staggered) to its new face. Codes 63–69 fill
  the tile with a color; letters and digits draw as glyphs.

## Later phases (seams already in place)

- **Mic input** → one file in `inputs/`, registry line, `input.type: mic`.
- **Vestaboard / DIY hardware** → one folder in `displays/`, registry line.
- **Art mode** (LLM paints with color tiles) → a second Brain mode; the
  contract already carries colors.
