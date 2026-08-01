"""Tests for the optional AnthropicClient (needs the `llm` extra installed)."""

import pytest

anthropic = pytest.importorskip("anthropic", reason="install the `llm` extra to test this")

from clapper_ai.adapters.llm.anthropic_client import AnthropicClient  # noqa: E402


class FakeMessages:
    def __init__(self, text: str, stop_reason: str = "end_turn"):
        self.text = text
        self.stop_reason = stop_reason
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)

        class Block:
            type = "text"

        block = Block()
        block.text = self.text

        class Response:
            content = [block]
            stop_reason = self.stop_reason

        return Response()


def make_client(reply: str, stop_reason: str = "end_turn") -> tuple[AnthropicClient, FakeMessages]:
    client = AnthropicClient.__new__(AnthropicClient)  # skip __init__: no key needed
    client.model = AnthropicClient.MODEL
    fake = FakeMessages(reply, stop_reason)

    class FakeSDK:
        messages = fake

    client._client = FakeSDK()
    return client, fake


async def test_complete_returns_the_reply_text():
    client, _ = make_client("PARIS")
    reply = await client.complete("capital of france?", max_chars=132)
    assert reply == "PARIS"


async def test_reply_is_clamped_to_max_chars():
    client, _ = make_client("A" * 500)
    reply = await client.complete("hi", max_chars=10)
    assert len(reply) == 10


async def test_uses_the_current_opus_model():
    client, fake = make_client("OK")
    await client.complete("hi", max_chars=132)
    assert fake.calls[0]["model"] == "claude-opus-5"


async def test_token_budget_leaves_room_for_thinking():
    # Opus 5 thinks by default and max_tokens covers thinking + answer, so a
    # budget the size of the board would come back empty.
    client, fake = make_client("OK")
    await client.complete("hi", max_chars=132)
    assert fake.calls[0]["max_tokens"] >= 2048


async def test_refusal_raises_so_the_caller_can_apologize():
    client, _ = make_client("", stop_reason="refusal")
    with pytest.raises(RuntimeError, match="refus"):
        await client.complete("hi", max_chars=132)


async def test_client_wraps_the_question_in_the_answer_prompt():
    from clapper_ai.adapters.llm.anthropic_client import ANSWER_PROMPT

    client, fake = make_client("PARIS")
    await client.complete("capital of france?", max_chars=132)

    sent = fake.calls[0]["messages"][0]["content"]
    assert "capital of france?" in sent
    assert "132" in sent  # the character budget is spelled out
    assert "{max_chars}" in ANSWER_PROMPT  # the constant stays tunable
