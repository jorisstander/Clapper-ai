# Add your own input

An input is any object that satisfies `InputSource`
(`src/clapper_ai/application/ports/input_source.py`):

```python
class InputSource(Protocol):
    async def listen(self) -> str: ...
```

`listen()` blocks until the user has said/typed/sent something, then returns
the transcript as plain text. Raise `EOFError` when your source is exhausted
and the app should shut down.

## Worked example: canned demo input

Save as `src/clapper_ai/adapters/inputs/demo_input.py`:

```python
"""Plays a scripted demo: one canned prompt every few seconds."""

import asyncio


class DemoInput:
    PROMPTS = ["hello world", "what time is it", "goodbye"]

    def __init__(self) -> None:
        self._index = 0

    async def listen(self) -> str:
        if self._index >= len(self.PROMPTS):
            raise EOFError  # demo over — ends the app loop cleanly
        await asyncio.sleep(3)
        prompt = self.PROMPTS[self._index]
        self._index += 1
        return prompt
```

## Register and select it

```python
# src/clapper_ai/__main__.py
from clapper_ai.adapters.inputs.demo_input import DemoInput  # add with the other imports

INPUTS = {
    "text": lambda config: TextInput(),
    "demo": lambda config: DemoInput(),
}
```

```yaml
# config.yaml
input:
  type: demo
```

## Notes for microphone input (later phase)

The seam is ready: a `MicInput` would record audio, run speech-to-text, and
return the transcript from `listen()`. Its dependencies belong behind the
`mic` extra in `pyproject.toml` so keyboard users never install them.
