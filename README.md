# clapper-ai

[![CI](https://github.com/jorisstander/Clapper-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/jorisstander/Clapper-ai/actions/workflows/ci.yml)

Ask an LLM a question, watch the answer flap onto a split-flap display.

## The mental model: swap the ends, keep the middle

clapper-ai is three boxes. The middle one never changes; the ends are plug-in
adapters you swap in `config.yaml`:

```
   INPUT                      BRAIN                       DISPLAY
┌───────────┐        ┌───────────────────┐        ┌──────────────────┐
│ keyboard  │  text  │  ask LLM          │  grid  │ virtual board    │
│ mic*      │ ─────► │  text → tile grid │ ─────► │ Vestaboard*      │
│ phone*    │        │  validate         │        │ DIY hardware*    │
└───────────┘        └───────────────────┘        └──────────────────┘
                          * = later phase
```

Everything speaks one contract: a **grid of tile codes** — `rows × cols` ints
where `0` is blank, `1–26` are `A–Z`, `27–36` are digits, `63–69` are color
tiles (see [docs/character-codes.md](docs/character-codes.md)). Any input that
produces text and any display that renders a grid can join, which is why the
folders are laid out the way they are:

- `src/clapper_ai/inputs/` — one file per input device
- `src/clapper_ai/displays/` — one folder per display device
- `src/clapper_ai/core/` — the Brain and the contract; never imports an adapter

**Adding a device later = one new file + one config line.** No core changes.
See [docs/add-your-own-board.md](docs/add-your-own-board.md) and
[docs/add-your-own-input.md](docs/add-your-own-input.md).

## Try it (no API key needed)

Needs [uv](https://docs.astral.sh/uv/getting-started/installation/) — it fetches
Python 3.14 for you if you don't have it.

```bash
uv sync
uv run python -m clapper_ai
```

Open http://127.0.0.1:8000, type a line in the terminal, watch it flap.
Full walkthrough in [QUICKSTART.md](QUICKSTART.md).

## Real answers

The default `fake` LLM echoes what you type. For real answers:

```bash
uv sync --extra llm
export ANTHROPIC_API_KEY=sk-ant-...   # PowerShell: $env:ANTHROPIC_API_KEY = "sk-ant-..."
```

then set `llm.type: anthropic` in `config.yaml` for plain-text answers, or
`llm.type: anthropic-smart` to let the AI also design the board — centered
layouts with color accents, web search for live facts, and full-tile art
("paint the great wave"). Either way, that's the only change.

## Project layout

```
config.yaml            pick your input / display / llm here
src/clapper_ai/
  core/                the contract: codes, grid, validate, interfaces, brain
  inputs/              InputSource adapters (text_input.py today)
  displays/            DisplaySink adapters (virtual/ today)
  llm/                 LLMClient adapters (fake.py, anthropic_client.py)
docs/                  architecture + how to add your own device
tests/
```

More depth in [docs/architecture.md](docs/architecture.md).

## Contributing & license

PRs welcome — read [CONTRIBUTING.md](CONTRIBUTING.md) first.
MIT licensed; see [LICENSE](LICENSE).
