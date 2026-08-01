# Architecture

## One contract, three seams

Every component communicates through a single data structure:

```python
Grid = list[list[int]]   # rows × cols; each int is one tile code
```

Around that contract sit three protocols, one file each under
`src/clapper_ai/application/ports/`:

| Protocol | Job | Today's adapter |
|---|---|---|
| `InputSource` | `listen() -> str` — wait for an utterance | `TextInput` (stdin) |
| `LLMClient` | `complete(prompt, max_chars) -> str \| LayoutSpec` | `EchoLLMClient` (config `fake`), `AnthropicClient` |
| `DisplaySink` | `render(grid)` — show it, own the animation | `VirtualBoard` (browser) |

`AnswerQuestion` (`application/interactors/answer_question.py`) depends **only**
on these protocols. It never imports a concrete adapter, which is what keeps the
ends swappable.

## Three layers, one direction

The folders under `src/clapper_ai/` are layers, and the split comes down to what
each one would still need if you deleted the rest. `domain/` holds the tile rules
— what a code means, what shape a grid may take, how text becomes one — and those
would hold even if nobody ever wired an LLM to a board. `application/` holds the
single turn the app performs, `AnswerQuestion`, plus the three ports it speaks
through: it knows there is an input, a model, and a display, but never which ones.
`adapters/` is everything that touches the outside world — a terminal, a browser
socket, an HTTP call to Anthropic.

Dependencies point inward only. An adapter may import from `domain/` and
`application/`; neither of those may ever import an adapter, and that one-way rule
is what lets you swap the ends without touching the middle. `__main__.py` sits
outside the stack as the only module allowed to name concrete adapters — which is
all the registries below really are. The rule is checkable:

```bash
grep -rn "from clapper_ai.adapters" src/clapper_ai/domain src/clapper_ai/application
```

That returns nothing today, and a change that makes it print something is a change
that broke the architecture.

## The flow

```
TextInput.listen()          "what is rust"
        │
        ▼
AnswerQuestion.execute()    hands the question to the LLM client (each
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
`domain/layout.py` renders either shape deterministically — the model chooses
the design, our code does the tile arithmetic — and `validate_grid` still
gates the result. If the call or the layout fails, the use case shows
`SORRY, TRY AGAIN` instead of crashing.

## Wiring

`__main__.py` reads `config.yaml` (validated by a Pydantic model), looks the
three `type` names up in small registries (`INPUTS`, `DISPLAYS`, `LLMS`), and
runs the loop:

```python
while True:
    question = await source.listen()
    await answer_question.execute(question)
```

When the display is the `VirtualBoard`, it also starts a Uvicorn server that
serves the static page and the `/ws` WebSocket.

## The virtual board

- `adapters/displays/virtual/sink.py` — `VirtualBoard` keeps the latest grid and
  a set of connected sockets; `render()` broadcasts `{rows, cols, grid}` as JSON.
- `adapters/displays/virtual/server.py` — FastAPI app: `GET /` serves the page,
  `/ws` attaches a browser to the board. A tab that connects late immediately
  receives the current grid.
- `static/board.js` — a `<canvas>`, no build step. Each tile that changed
  flips (scale-Y fold, slightly staggered) to its new face. Codes 63–69 fill
  the tile with a color; letters and digits draw as glyphs.

## Later phases (seams already in place)

- **Mic input** → one file in `adapters/inputs/`, registry line, `input.type: mic`.
- **Vestaboard / DIY hardware** → one folder in `adapters/displays/`, registry line.
- **Push-data sources** (Strava, calendar, weather) → a designer-only entry
  point that feeds content straight into the existing `LayoutSpec` renderer.
