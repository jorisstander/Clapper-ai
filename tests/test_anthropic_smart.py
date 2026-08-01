"""Tests for SmartAnthropicClient (needs the `llm` extra installed)."""

import json

import pytest

pytest.importorskip("anthropic", reason="install the `llm` extra to test this")

from clapper_ai.domain.layout import ArtLayout, TextLayout  # noqa: E402
from clapper_ai.llm.anthropic_smart import SmartAnthropicClient  # noqa: E402


class FakeMessages:
    def __init__(self, reply_text: str, stop_reason: str = "end_turn"):
        self.reply_text = reply_text
        self.stop_reason = stop_reason
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)

        class Block:
            type = "text"

        block = Block()
        block.text = self.reply_text

        class Response:
            content = [block]
            stop_reason = self.stop_reason

        return Response()


def make_client(reply: dict, stop_reason: str = "end_turn"):
    client = SmartAnthropicClient.__new__(SmartAnthropicClient)  # skip __init__
    client.model = SmartAnthropicClient.MODEL
    client.rows, client.cols = 6, 22
    fake = FakeMessages(json.dumps(reply), stop_reason)

    class FakeSDK:
        messages = fake

    client._client = FakeSDK()
    return client, fake


TEXT_REPLY = {
    "layout": {
        "type": "text_layout",
        "lines": [{"text": "18 MILLION", "align": "center", "color": None}],
    }
}
ART_REPLY = {"layout": {"type": "art", "grid": [[67] * 22 for _ in range(6)]}}


async def test_parses_a_text_layout_reply():
    client, _ = make_client(TEXT_REPLY)
    spec = await client.complete("population of the netherlands", max_chars=132)
    assert isinstance(spec, TextLayout)
    assert spec.lines[0].text == "18 MILLION"
    assert spec.lines[0].align == "center"


async def test_parses_an_art_reply():
    client, _ = make_client(ART_REPLY)
    spec = await client.complete("paint the great wave", max_chars=132)
    assert isinstance(spec, ArtLayout)
    assert len(spec.grid) == 6


async def test_request_describes_the_board_and_enables_search():
    client, fake = make_client(TEXT_REPLY)
    await client.complete("hello", max_chars=132)

    call = fake.calls[0]
    assert call["model"] == "claude-opus-5"
    assert "6" in call["system"] and "22" in call["system"]
    assert call["tools"][0]["name"] == "web_search"
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert call["messages"] == [{"role": "user", "content": "hello"}]


async def test_refusal_raises_so_the_brain_can_apologize():
    client, _ = make_client(TEXT_REPLY, stop_reason="refusal")
    with pytest.raises(RuntimeError, match="refus"):
        await client.complete("hello", max_chars=132)


async def test_malformed_layout_raises_so_the_brain_can_apologize():
    client, _ = make_client({"layout": {"type": "nonsense"}})
    with pytest.raises(Exception):  # noqa: B017
        await client.complete("hello", max_chars=132)


def test_color_names_match_the_tile_codes():
    # The real drift risk: render_layout does COLOR_CODES[line.color], so every
    # ColorName must exist in codes.py (and vice versa, so the schema stays
    # in sync with the renderer).
    from clapper_ai.domain.tile_codes import COLOR_CODES
    from clapper_ai.llm.anthropic_smart import _COLOR_NAMES

    assert _COLOR_NAMES == list(COLOR_CODES)
