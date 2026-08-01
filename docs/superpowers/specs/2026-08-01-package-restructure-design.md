# Package restructure: make the clean-architecture layers legible

**Date:** 2026-08-01
**Status:** approved, ready for implementation planning

## Problem

The dependency rule already holds. `core/` imports nothing from `llm/`, `inputs/`,
or `displays/` — verifiable in one grep, and it is why the domain functions are
pure and the suite runs in about a second.

What is missing is legibility. `core/` holds three architectural rings under one
name: domain (`codes`, `grid`, `layout`, `validate`), the use case (`brain`), and
the ports (`interfaces`). A reader cannot recover the layering from the tree, and
`Brain` is a metaphor rather than a name from the domain.

This is a communication defect, not a structural one. The fix is naming and
placement, not rewiring.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Layer style | Textbook: `domain/`, `application/`, `adapters/` | Layers unmistakable to a reader opening the repo cold. Chosen knowingly over shorter adapter paths. |
| Ports location | Inside `application/ports/` | Uncle-Bob-strict: the use case owns the interfaces it depends on. Gives `application/` a second category, which is what earns `interactors/` its keep. |
| Ports granularity | Three files, one per port | Consistent with letting the path carry the taxonomy. Each port gets its own docstring — which is where the `InputSource` asymmetry is documented. |
| Use case name | `AnswerQuestion.execute()` | `Brain` is a metaphor; `handle` names nothing. Package `application/interactors/` already says which ring it is, so no `UseCase`/`Interactor` suffix on the class. |
| Module naming | `snake_case` | PEP 8. `AnswerQuestionUseCase.py` would be the only non-conforming module, and CamelCase modules break on case-sensitive CI while working on Windows. |
| `layout.py` | Kept whole, pydantic stays in `domain/` | The no-frameworks rule targets *lifecycle* coupling (ORMs, web frameworks). Pydantic here validates a value object — closer to a strict dataclass. Splitting a 60-line module to avoid one import costs cohesion. |
| Scope | Moves and renames only | Behaviour-preserving, so the existing suite proves correctness. Design changes are deferred (below). |

## Target tree

```
src/clapper_ai/
├── domain/
│   ├── tile_codes.py       ← core/codes.py       (renamed)
│   ├── grid.py             ← core/grid.py
│   ├── layout.py           ← core/layout.py
│   ├── text_layout.py      ← core/validate.py    (text_to_grid, _word_wrap)
│   └── grid_rules.py       ← core/validate.py    (validate_grid)
├── application/
│   ├── interactors/
│   │   └── answer_question.py   ← core/brain.py
│   └── ports/
│       ├── llm_client.py        ┐
│       ├── display_sink.py      ├─ core/interfaces.py, split three ways
│       └── input_source.py      ┘
├── adapters/
│   ├── inputs/text_input.py
│   ├── displays/virtual/{server.py, sink.py, static/}
│   └── llm/{anthropic_client.py, anthropic_smart.py, echo.py}
└── __main__.py                  unchanged — the composition root belongs at the root
```

`core/` is deleted. All `__init__.py` files are empty, so every move is a pure
`git mv`.

## Renames

| From | To |
|---|---|
| `class Brain` | `class AnswerQuestion` |
| `Brain.handle(text)` | `AnswerQuestion.execute(question)` |
| `class FakeLLMClient` | `class EchoLLMClient` |
| `llm/fake.py` | `adapters/llm/echo.py` |
| `core/codes.py` | `domain/tile_codes.py` |

`fake` is test-double vocabulary (dummy/fake/stub/spy/mock), but this class is the
*default production adapter* — `config.yaml` ships `llm.type: fake` and it is what
makes the keyless demo work. `Echo` says "real adapter that does not phone home."

**The `llm.type: fake` config value is NOT renamed.** It is the documented public
interface in `README.md`, `QUICKSTART.md`, and `config.example.yaml`. Renaming the
class is internal; renaming the config key would break every existing user's file.

## The InputSource asymmetry

`LLMClient` and `DisplaySink` are driven ports of the interactor — `AnswerQuestion`
calls out through them. `InputSource` is not: it is consumed by the `run()` loop in
`__main__.py`, which pulls a string and passes it to the interactor.

So `InputSource` is a port of the *driving side*, and placing it in
`application/ports/` is a knowing simplification rather than a strict-correctness
claim. This is recorded in the `input_source.py` module docstring so the deviation
is visible to a reader instead of looking like an oversight.

Resolving it properly means flipping input from pull to push, so the input adapter
calls `execute()` itself and the inbound port becomes the method. That is a
behavioural change and is deferred.

## Tidy-ups included

- `tile_codes.py`: replace the import-time `for` loops that mutate a dict
  (`codes.py:20-23`) with dict comprehensions. Same values, declarative, matching
  the style of the rest of the codebase.
- Delete the punctuation `TODO` from the public module docstring and record it in
  the deferred list below instead — a docstring is documentation for callers, not
  a backlog.

## What does not change

- Any behaviour. This refactor is moves, renames, and one file split.
- Test **count**: 69 before, 69 after. Test files change only by imports and
  renamed symbols (`test_config.py` asserts `isinstance(llm, FakeLLMClient)`).
- Public config surface: `config.yaml` keys and values are untouched.
- `pyproject.toml` packaging — `packages = ["src/clapper_ai"]` still correct.
- Ruff config — `src = ["src", "tests"]` still correct.
- `displays/virtual/static/` assets: `server.py:11` resolves via
  `Path(__file__).parent`, so the directory moves with its module.

## Docs impact

Five files reference the old paths or the Brain:

| File | Change |
|---|---|
| `README.md` | Project-layout block, the `src/clapper_ai/inputs/` bullets, and the `INPUT → BRAIN → DISPLAY` diagram label |
| `CONTRIBUTING.md` | Ground rules naming `core/interfaces.py` and the adapter paths |
| `docs/architecture.md` | Refers to "the Brain" throughout |
| `docs/add-your-own-board.md` | Step-by-step paths |
| `docs/add-your-own-input.md` | Step-by-step paths |

`docs/character-codes.md` references `codes.py` and needs the rename.

The claim "new device = one new file + one config line" stays true — only the
directory it lands in gets one segment longer.

## Migration order

1. Create the new package directories with empty `__init__.py`.
2. `git mv` every module to its new home (preserves history).
3. Split `core/validate.py` into `domain/text_layout.py` and `domain/grid_rules.py`.
4. Split `core/interfaces.py` into the three port modules.
5. Rename the classes and methods.
6. Update all **47** internal import sites across `src/` and `tests/`
   (`clapper_ai.core` 27, `clapper_ai.llm` 11, `clapper_ai.displays` 6,
   `clapper_ai.inputs` 3). Ruff's `I` rules fix ordering afterwards.
7. Apply the `tile_codes.py` comprehension tidy-up.
8. Delete the empty `core/`.
9. Update the six documentation files.

## Verification

The refactor is behaviour-preserving, so the existing suite is the proof:

```bash
uv sync --all-extras --locked
uv run ruff check .
uv run pytest -q          # must report exactly 69 passed
```

Plus two checks the suite cannot make:

- **Dependency rule still holds** — `domain/` and `application/` must import
  nothing from `adapters/`:
  `grep -rn "from clapper_ai.adapters" src/clapper_ai/domain src/clapper_ai/application`
  must return nothing. Match the import, not the word "adapters" — the port
  docstrings legitimately point readers at `adapters/displays/` and `adapters/llm/`,
  and a bare word match fails on that correct signposting.
- **The demo still boots** — `uv sync && uv run python -m clapper_ai` prints the
  board URL and exits cleanly on EOF.

A green suite with an unchanged test count is the signal that only placement moved.

## Deferred — captured so the findings are not lost

Each needs its own tests and its own commit.

1. **Tile alphabet is closed.** `ColorName` in `layout.py:15` is a
   `Literal[...]` of Vestaboard's seven colours, and `COLOR_CODES` is a module
   constant. A board with an eighth colour cannot express it. Subsetting works
   (`validate_grid` takes `allowed` as a parameter); supersetting requires editing
   the domain. The fix is a tile-alphabet value object the display owns.
2. **`Grid` is primitive-obsessed.** `Grid = list[list[int]]` guarantees nothing,
   which is why `validate_grid` must exist as a gate every caller remembers to
   call. A `Grid` value object enforcing its invariants at construction would
   absorb it.
3. **Value objects are mutable.** Pydantic models default to mutable;
   `model_config = ConfigDict(frozen=True)` makes them true value objects.
4. **Error hierarchy.** Both LLM adapters raise bare `RuntimeError`, and
   `AnswerQuestion` catches `Exception`, so a `KeyError` in `render_layout` is
   indistinguishable from an API refusal — the app's own bugs are converted into
   "SORRY, TRY AGAIN". A `ClapperError` base with `LLMError` / `LayoutError` lets
   genuine programming errors propagate while the loop still survives adapter
   failures.
5. **`isinstance(display, VirtualBoard)` in `run()`.** The composition root
   type-sniffs an adapter to decide whether to start a web server. A lifecycle
   port (`start()`/`stop()`, or async context managers) replaces type inspection
   with polymorphism.
6. **`InputSource` pull vs push**, per the asymmetry section above. To be explored
   together with the shape of the adapter factory in `__main__.py`.
7. **Punctuation tile codes.** Vestaboard codes 37–62 are unmapped; only letters,
   digits and colours exist today. The how-to already lives in
   `docs/character-codes.md`, including the official Vestaboard Character Codes
   link and the two files a contributor must update — `domain/tile_codes.py` and
   the display's own code table. Moved here from that module's docstring.
8. **The board still says FAKE.** `adapters/llm/echo.py` greets an empty prompt
   with `"HELLO FROM THE FAKE LLM"`. That literal is user-visible board output, so
   changing it is behavioural and stayed out of the rename commit — but it names a
   class that no longer exists, and unlike the `fake` config value (which is public
   interface and deliberately kept), this string has no reason to survive.
   Successor: `"HELLO FROM THE ECHO LLM"`. Note that
   branch has no test today, so the change has no regression net; add one with it.
9. **`text_layout.py` sits beside a class called `TextLayout`.** The module holds
   `text_to_grid` (plain-string word-wrap); the class in `domain/layout.py` is the
   structured LLM spec with alignment and colour. Different concepts, near-identical
   names, imported on adjacent lines in `answer_question.py`. Kept as specified for
   this pass. If revisited, `plain_text.py` or `text_wrapping.py` says what the
   module does without colliding.

No DDD entities are introduced. Nothing in this system has identity or a
lifecycle; every model is a value object. That is a correct reflection of a
stateless transformation pipeline, not a gap to be filled.
