"""Smart answers: Claude answers the question AND designs the board.

One API call with three ingredients:
- a system prompt describing the board (size, tiles, colors),
- the web_search server tool for live facts (scores, news),
- a JSON schema forcing the reply into a LayoutSpec shape.

Optional: needs the `llm` extra and ANTHROPIC_API_KEY, like anthropic_client.
Select with `llm.type: anthropic-smart` in config.yaml.
"""

import json
from typing import get_args

from pydantic import TypeAdapter

from clapper_ai.core.layout import ArtLayout, ColorName, LayoutSpec, TextLayout

SYSTEM_PROMPT = (
    "You control a split-flap display of {rows} rows x {cols} columns. Each tile "
    "shows one of: blank (code 0), A-Z (codes 1-26), digits 1-9 then 0 (codes "
    "27-36), or a solid color tile: red 63, orange 64, yellow 65, green 66, "
    "blue 67, violet 68, white 69.\n"
    "Answer the user's question, then design how it should look on the board.\n"
    "- Questions: reply with type 'text_layout'. At most {rows} lines of {cols} "
    "characters. Center titles, use an empty line with a color as a divider or "
    "accent bar. Keep wording short enough to fit.\n"
    "- Art requests (e.g. 'paint the great wave'): reply with type 'art' and a "
    "grid of exactly {rows} rows x {cols} tile codes, mostly color tiles.\n"
    "Use web search when the question needs current information. If you cannot "
    "answer, say so briefly on the board."
)

_COLOR_NAMES = list(get_args(ColorName))  # schema enum can't drift from ColorName

LAYOUT_SCHEMA = {
    "type": "object",
    "properties": {
        "layout": {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "type": {"const": "text_layout"},
                        "lines": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "align": {
                                        "type": "string",
                                        "enum": ["left", "center", "right"],
                                    },
                                    "color": {
                                        "anyOf": [
                                            {"type": "string", "enum": _COLOR_NAMES},
                                            {"type": "null"},
                                        ]
                                    },
                                },
                                "required": ["text", "align", "color"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["type", "lines"],
                    "additionalProperties": False,
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {"const": "art"},
                        "grid": {
                            "type": "array",
                            "items": {"type": "array", "items": {"type": "integer"}},
                        },
                    },
                    "required": ["type", "grid"],
                    "additionalProperties": False,
                },
            ]
        }
    },
    "required": ["layout"],
    "additionalProperties": False,
}
# The schema can't pin grid dimensions or code ranges (JSON Schema numeric
# constraints aren't supported by structured outputs) — render_layout and
# validate_grid enforce those downstream.

_LAYOUT_ADAPTER: TypeAdapter = TypeAdapter(LayoutSpec)


class SmartAnthropicClient:
    MODEL = "claude-opus-4-8"

    def __init__(self, rows: int, cols: int, model: str = MODEL):
        try:
            from anthropic import AsyncAnthropic
        except ImportError as error:
            raise SystemExit(
                "The anthropic package is not installed. "
                "Run: uv sync --extra llm"
            ) from error
        self._client = AsyncAnthropic()
        self.model = model
        self.rows = rows
        self.cols = cols

    async def complete(self, prompt: str, *, max_chars: int) -> TextLayout | ArtLayout:
        # max_chars is unused here: the board size reaches the model via
        # rows/cols in the system prompt instead.
        response = await self._client.messages.create(
            model=self.model,
            max_tokens=4096,  # search summaries + a full art grid fit easily
            system=SYSTEM_PROMPT.format(rows=self.rows, cols=self.cols),
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}],
            output_config={"format": {"type": "json_schema", "schema": LAYOUT_SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
        texts = [block.text for block in response.content if block.type == "text"]
        if response.stop_reason == "refusal" or not texts:
            # The Brain catches this and shows its apology grid.
            raise RuntimeError(f"Model refused or gave no answer ({response.stop_reason})")
        data = json.loads(texts[-1])  # last text block: search blocks may precede it
        return _LAYOUT_ADAPTER.validate_python(data["layout"])
