"""Tests for the stdin input source."""

import builtins

import pytest

from clapper_ai.adapters.inputs.text_input import TextInput


async def test_listen_returns_the_typed_line(monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda _prompt="": "  hello board  ")
    assert await TextInput().listen() == "hello board"


async def test_listen_skips_empty_lines(monkeypatch):
    lines = iter(["", "   ", "finally"])
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(lines))
    assert await TextInput().listen() == "finally"


async def test_listen_propagates_eof(monkeypatch):
    def raise_eof(_prompt=""):
        raise EOFError

    monkeypatch.setattr(builtins, "input", raise_eof)
    with pytest.raises(EOFError):
        await TextInput().listen()
