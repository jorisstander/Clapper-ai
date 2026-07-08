# Quickstart

Two minutes, no API key, no hardware.

## 1. Install

Needs Python 3.11+.

```bash
git clone https://github.com/your-org/clapper-ai.git
cd clapper-ai
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## 2. Run

```bash
python -m clapper_ai
```

You'll see:

```
Virtual board at http://127.0.0.1:8000 — open it in a browser.
Type a prompt and press Enter. Ctrl-D quits.
>
```

(Port 8000 taken? Run `PORT=8123 python -m clapper_ai` instead.)

## 3. Flap

Open http://127.0.0.1:8000 in a browser, then type in the terminal:

```
> hello board
```

The board flips to `YOU SAID HELLO BOARD`. That's the default `fake` LLM —
a deterministic echo, so the whole pipeline runs without any key.

## 4. Real answers (optional)

```bash
pip install -e ".[llm]"
export ANTHROPIC_API_KEY=sk-ant-...
```

Edit `config.yaml` and change one value:

```yaml
llm:
  type: anthropic
```

Run it again and ask something real. Answers are kept short enough to fit the
6×22 board.

## Troubleshooting

- **Board stays blank** — check the page says "connected" under the board;
  if not, the server isn't running or you're on the wrong port.
- **`Unknown ... type` on startup** — a typo in `config.yaml`; the error lists
  the valid options.
- **`anthropic` type fails** — did you `pip install -e ".[llm]"` and export
  `ANTHROPIC_API_KEY`?
