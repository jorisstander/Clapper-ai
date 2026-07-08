"""Tests for the optional AnthropicClient (needs the `llm` extra installed)."""

import pytest

anthropic = pytest.importorskip("anthropic", reason="install the `llm` extra to test this")

from clapper_ai.llm.anthropic_client import AnthropicClient  # noqa: E402


class FakeMessages:
    def __init__(self, text: str):
        self.text = text
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)

        class Block:
            type = "text"

        block = Block()
        block.text = self.text

        class Response:
            content = [block]

        return Response()


def make_client(reply: str) -> tuple[AnthropicClient, FakeMessages]:
    client = AnthropicClient.__new__(AnthropicClient)  # skip __init__: no key needed
    client.model = AnthropicClient.MODEL
    fake = FakeMessages(reply)

    class FakeSDK:
        messages = fake

    client._client = FakeSDK()
    return client, fake


async def test_complete_returns_the_reply_text():
    client, fake = make_client("PARIS")
    reply = await client.complete("capital of france?", max_chars=132)
    assert reply == "PARIS"
    assert fake.calls[0]["messages"] == [{"role": "user", "content": "capital of france?"}]


async def test_reply_is_clamped_to_max_chars():
    client, _ = make_client("A" * 500)
    reply = await client.complete("hi", max_chars=10)
    assert len(reply) == 10


async def test_uses_the_current_opus_model():
    client, fake = make_client("OK")
    await client.complete("hi", max_chars=132)
    assert fake.calls[0]["model"] == "claude-opus-4-8"
