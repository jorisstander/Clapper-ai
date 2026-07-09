"""Entrypoint: load config.yaml, wire the chosen adapters, run the loop.

The registries below are the whole plugin system. To add a device:
write one file implementing the protocol, add one line to a registry,
name it in config.yaml. The Brain never changes.
"""

import asyncio
import os
import sys
from pathlib import Path

import uvicorn
import yaml
from pydantic import BaseModel

from clapper_ai.core.brain import Brain
from clapper_ai.displays.virtual.server import create_app
from clapper_ai.displays.virtual.sink import VirtualBoard
from clapper_ai.inputs.text_input import TextInput
from clapper_ai.llm.fake import FakeLLMClient

HOST = "127.0.0.1"
# Override with PORT=8123 if something else already owns 8000.
PORT = int(os.environ.get("PORT", "8000"))


# --- config ------------------------------------------------------------------


class AdapterConfig(BaseModel):
    type: str


class BoardConfig(BaseModel):
    rows: int = 6
    cols: int = 22


class AppConfig(BaseModel):
    input: AdapterConfig = AdapterConfig(type="text")
    display: AdapterConfig = AdapterConfig(type="virtual")
    llm: AdapterConfig = AdapterConfig(type="fake")
    board: BoardConfig = BoardConfig()


def load_config(path: str | Path) -> AppConfig:
    data = yaml.safe_load(Path(path).read_text()) or {}
    return AppConfig.model_validate(data)


# --- adapter registries ------------------------------------------------------

# Each factory gets the full config so it can pick out what it needs.
INPUTS = {
    "text": lambda config: TextInput(),
}

DISPLAYS = {
    "virtual": lambda config: VirtualBoard(rows=config.board.rows, cols=config.board.cols),
}

def _make_anthropic(config: "AppConfig"):
    # Imported lazily so the base install never needs the anthropic package.
    from clapper_ai.llm.anthropic_client import AnthropicClient

    return AnthropicClient()


def _make_smart_anthropic(config: "AppConfig"):
    from clapper_ai.llm.anthropic_smart import SmartAnthropicClient

    return SmartAnthropicClient(rows=config.board.rows, cols=config.board.cols)


LLMS = {
    "fake": lambda config: FakeLLMClient(),
    "anthropic": _make_anthropic,
    "anthropic-smart": _make_smart_anthropic,
}


def _pick(registry: dict, kind: str, name: str, config: AppConfig):
    if name not in registry:
        options = ", ".join(sorted(registry))
        raise SystemExit(f"Unknown {kind} type {name!r} in config. Valid options: {options}")
    return registry[name](config)


def build_adapters(config: AppConfig):
    """Turn config names into live objects: (input source, display, llm)."""
    source = _pick(INPUTS, "input", config.input.type, config)
    display = _pick(DISPLAYS, "display", config.display.type, config)
    llm = _pick(LLMS, "llm", config.llm.type, config)
    return source, display, llm


# --- run loop ----------------------------------------------------------------


async def run(config: AppConfig) -> None:
    source, display, llm = build_adapters(config)
    brain = Brain(llm=llm, display=display)

    server = None
    server_task = None
    if isinstance(display, VirtualBoard):
        server = uvicorn.Server(
            uvicorn.Config(create_app(display), host=HOST, port=PORT, log_level="warning")
        )
        server_task = asyncio.create_task(server.serve())
        print(f"Virtual board at http://{HOST}:{PORT} — open it in a browser.")

    print("Type a prompt and press Enter. Ctrl-D quits.")
    try:
        while True:
            text = await source.listen()
            await brain.handle(text)
    except EOFError:
        print("\nBye.")
    finally:
        if server is not None:
            server.should_exit = True
            await server_task


def main() -> None:
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    try:
        asyncio.run(run(load_config(config_path)))
    except KeyboardInterrupt:
        print("\nBye.")


if __name__ == "__main__":
    main()
