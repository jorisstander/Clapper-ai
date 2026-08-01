# Contributing

Thanks for helping! clapper-ai is built for DIY hobbyists — clarity beats cleverness.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
uv sync --all-extras
```

That builds the venv, installs the project with every extra plus the `dev`
dependency group, and pins versions from `uv.lock` — same resolution for you as
for CI. Later `uv sync --extra llm` calls keep the dev tools: `dev` is a group,
not an extra, so syncing an extra doesn't prune it.

## Before opening a PR

```bash
uv run ruff check .
uv run pytest
```

Both must pass. CI runs the same two commands on every push, against Python
3.14 — the one version `requires-python` claims. `uv` will fetch it for you.

If you change a dependency in `pyproject.toml`, run `uv lock` and commit the
updated `uv.lock`. CI syncs with `--locked` and fails if the two disagree.

## Ground rules

- **The core never imports a concrete adapter.** `AnswerQuestion` talks only to the
  `InputSource`, `DisplaySink`, and `LLMClient` protocols in
  `src/clapper_ai/application/ports/`.
- **New device = one new file + one config line.** Add an input under
  `src/clapper_ai/adapters/inputs/`, a display under
  `src/clapper_ai/adapters/displays/`, register it in `src/clapper_ai/__main__.py`,
  done. See `docs/add-your-own-board.md`.
- **Keep the base install tiny.** Anything with extra dependencies goes behind an
  optional extra in `pyproject.toml`.
- **Never commit secrets.** API keys come from environment variables; see `.env.example`.
- Commits follow conventional style: `feat:`, `fix:`, `docs:`, `test:`, `chore:` —
  one logical change each.
