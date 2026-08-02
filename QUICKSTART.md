# Quickstart

Two minutes, no API key, no hardware.

## 1. Install

Needs Python 3.14+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).
(Don't have 3.14? You don't need to install it — `uv sync` fetches it.)

```bash
git clone https://github.com/jorisstander/Clapper-ai.git
cd Clapper-ai
uv sync
```

`uv sync` makes the venv and installs the pinned dependencies in one step —
no activation needed, `uv run` uses it automatically.

## 2. Run

```bash
uv run python -m clapper_ai
```

You'll see:

```
Virtual board at http://127.0.0.1:8000 - open it in a browser.
Type a prompt and press Enter. Ctrl-D quits.
>
```

(Port 8000 taken? Run `PORT=8123 uv run python -m clapper_ai` instead — in
PowerShell that's `$env:PORT=8123; uv run python -m clapper_ai`.)

## 3. Flap

Open http://127.0.0.1:8000 in a browser, then type in the terminal:

```
> hello board
```

The board flips to `YOU SAID HELLO BOARD`. That's the default `fake` LLM —
a deterministic echo, so the whole pipeline runs without any key.

## 4. Real answers (optional)

```bash
uv sync --extra llm
export ANTHROPIC_API_KEY=sk-ant-...   # PowerShell: $env:ANTHROPIC_API_KEY = "sk-ant-..."
```

Edit `config.yaml` and change one value:

```yaml
llm:
  type: anthropic
```

Run it again and ask something real. Answers are kept short enough to fit the
6×22 board.

Want the AI to also *design* the board — centered layouts, color accents,
web search for live facts, even tile art? Use `type: anthropic-smart` instead.

## Troubleshooting

- **Board stays blank** — check the page says "connected" under the board;
  if not, the server isn't running or you're on the wrong port.
- **`Unknown ... type` on startup** — a typo in `config.yaml`; the error lists
  the valid options.
- **`anthropic` type fails** — did you `uv sync --extra llm` and set
  `ANTHROPIC_API_KEY` in the shell you're running from? Nothing reads a `.env`
  file; the variable has to be exported.
