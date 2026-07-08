# Contributing

Thanks for helping! clapper-ai is built for DIY hobbyists — clarity beats cleverness.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Before opening a PR

```bash
ruff check .
pytest
```

Both must pass.

## Ground rules

- **The core never imports a concrete adapter.** The `Brain` talks only to the
  `InputSource`, `DisplaySink`, and `LLMClient` protocols in
  `src/clapper_ai/core/interfaces.py`.
- **New device = one new file + one config line.** Add an input under
  `src/clapper_ai/inputs/`, a display under `src/clapper_ai/displays/`, register it
  in `src/clapper_ai/__main__.py`, done. See `docs/add-your-own-board.md`.
- **Keep the base install tiny.** Anything with extra dependencies goes behind an
  optional extra in `pyproject.toml`.
- **Never commit secrets.** API keys come from environment variables; see `.env.example`.
- Commits follow conventional style: `feat:`, `fix:`, `docs:`, `test:`, `chore:` —
  one logical change each.
