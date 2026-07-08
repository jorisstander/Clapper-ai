"""Tests for config loading and the adapter factory in __main__."""

import pytest

from clapper_ai.__main__ import build_adapters, load_config
from clapper_ai.displays.virtual.sink import VirtualBoard
from clapper_ai.inputs.text_input import TextInput
from clapper_ai.llm.fake import FakeLLMClient


def write_config(tmp_path, text: str):
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return path


def test_default_config_wires_text_virtual_fake(tmp_path):
    path = write_config(
        tmp_path,
        """
        input: {type: text}
        display: {type: virtual}
        llm: {type: fake}
        board: {rows: 6, cols: 22}
        """,
    )
    config = load_config(path)
    source, display, llm = build_adapters(config)

    assert isinstance(source, TextInput)
    assert isinstance(display, VirtualBoard)
    assert isinstance(llm, FakeLLMClient)


def test_board_dimensions_come_from_config(tmp_path):
    path = write_config(
        tmp_path,
        """
        input: {type: text}
        display: {type: virtual}
        llm: {type: fake}
        board: {rows: 3, cols: 11}
        """,
    )
    _, display, _ = build_adapters(load_config(path))
    assert (display.rows, display.cols) == (3, 11)


def test_missing_sections_fall_back_to_defaults(tmp_path):
    config = load_config(write_config(tmp_path, ""))
    assert config.input.type == "text"
    assert config.display.type == "virtual"
    assert config.llm.type == "fake"
    assert (config.board.rows, config.board.cols) == (6, 22)


def test_anthropic_llm_is_one_config_value_away(tmp_path, monkeypatch):
    pytest.importorskip("anthropic", reason="install the `llm` extra to test this")
    from clapper_ai.llm.anthropic_client import AnthropicClient

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-real")
    path = write_config(tmp_path, "llm: {type: anthropic}")

    _, _, llm = build_adapters(load_config(path))

    assert isinstance(llm, AnthropicClient)


def test_unknown_type_errors_and_lists_valid_options(tmp_path):
    path = write_config(tmp_path, "display: {type: hologram}")
    with pytest.raises(SystemExit, match="hologram") as excinfo:
        build_adapters(load_config(path))
    assert "virtual" in str(excinfo.value)  # the error teaches you what is valid


def test_unknown_input_type_lists_options(tmp_path):
    path = write_config(tmp_path, "input: {type: telepathy}")
    with pytest.raises(SystemExit, match="text"):
        build_adapters(load_config(path))
