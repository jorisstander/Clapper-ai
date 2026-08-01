# Smart rendering: the AI designs the board

**Date:** 2026-07-08 · **Status:** approved for planning

## Goal

Today the LLM's answer is always laid out the same way: uppercase text, left-aligned,
wrapped to the board. This design lets the model *decide how the board should look* —
centered layouts with color accents for answers ("NETHERLANDS 2 - 1" with an orange
divider), or full-board color-tile art ("The Great Wave") — and lets it answer
live-world questions (sports scores, news) via web search.

End vision (out of scope here): a physical phone as voice input. That is a separate
`InputSource` project; nothing in this design depends on it. Keyboard remains the input.

## Approach (decided)

**Single API call with self-classifying structured output** (Approach A). One call
answers the question *and* designs the board. Rejected alternatives: a two-stage
answer→designer pipeline (reusable for push-data sources like Strava, but double
latency/cost per question — can be added later because the renderer is shared), and
a mode-router (more moving parts for no gain at this scale).

## Architecture

```
listen() → Brain → SmartAnthropicClient (one call: web_search tool + JSON schema)
                        │ returns LayoutSpec (typed union)
                        ▼
                render_layout()   deterministic, our code
                        ▼
                validate_grid → display.render()
```

Input and display layers are untouched. `FakeLLMClient` and the plain `anthropic`
client keep the existing `text → text_to_grid` path, so the keyless demo and all
current tests are unaffected. Config selects the new mode with one value:
`llm.type: anthropic-smart`.

## The LayoutSpec contract

The model must reply with JSON matching exactly one of two shapes, enforced by the
API's structured-output feature (`output_config.format` with a JSON schema — not
prompt hope):

**Shape 1 — `text_layout`** (questions/answers). High-level intent; our code does
the tile math.

```json
{ "type": "text_layout",
  "lines": [
    { "text": "POPULATION",  "align": "center" },
    { "text": "",            "color": "orange" },
    { "text": "18 MILLION",  "align": "center" }
  ] }
```

- `align`: `left | center | right` (default `left`)
- `color`: one of the 7 color-tile names; an empty `text` + `color` renders a full
  row of that color (divider/bar)
- Max 6 lines; text clipped/padded to 22 columns by the renderer

**Shape 2 — `art`** (tile paintings). Lowest level: every tile specified.

```json
{ "type": "art", "grid": [[67, 67, 69, ...], ...] }
```

- Exactly 6 rows × 22 columns, values restricted to `ALLOWED_CODES`
  (schema-pinned where possible, `validate_grid` re-checks)

## Components

- **`core/layout.py`** — `LayoutSpec` types (Pydantic) + `render_layout(spec, rows, cols) -> Grid`.
  Deterministic: clip/pad text via existing `CHAR_TO_CODE`, unknown chars → blank,
  color rows fill, art grids pass through. Always returns a valid `rows × cols` grid
  or raises.
- **`llm/anthropic_smart.py`** — `SmartAnthropicClient`. One `messages.create` call:
  system prompt describing the board (dimensions, tile set, color names), server-side
  `web_search` tool enabled, structured output = the LayoutSpec union schema.
  Returns a parsed `LayoutSpec`. Model: `claude-opus-4-8`.
- **Brain / interfaces** — the `LLMClient` protocol's return type widens to
  `str | LayoutSpec`. The Brain branches on the type: a string goes through
  `text_to_grid` (existing path, used by `fake` and plain `anthropic`); a
  `LayoutSpec` goes through `render_layout`. Board dimensions are passed into the
  prompt, never hardcoded.
- **Config/registry** — `LLMS["anthropic-smart"]` entry; lazy import behind the
  existing `llm` extra.

## Error handling

- **API error / refusal / invalid grid from art shape** → Brain catches, renders
  `SORRY, TRY AGAIN` via the plain-text path, logs the error to the terminal. The
  board always responds.
- **Sloppy-but-valid layouts** (long lines, too many lines) → renderer clips/pads
  deterministically; the model can choose the layout but never break the board.
- **No useful search results** → handled inside the call: the prompt instructs the
  model to answer from knowledge or say it can't, still in a valid shape.

## Testing

- **Renderer** (bulk): alignment, clipping, padding, color rows, art pass-through,
  always-valid output. Pure functions.
- **Brain**: scripted LLM per shape → correct grid at the fake display; raising LLM
  → apology grid.
- **Schema**: accepts both example shapes, rejects malformed.
- **Manual live check** (needs a real key): a fact question, a web-search question,
  and The Great Wave.

## Out of scope

Phone/voice input, push-data sources (Strava — the renderer is deliberately reusable
for a later two-stage designer), animation choreography, punctuation tile codes.
