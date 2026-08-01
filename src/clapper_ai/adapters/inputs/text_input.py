"""The default input: read a line from the terminal. Zero dependencies.

Swap it for a microphone or phone client later by implementing the same
InputSource protocol — one file here, one line in config.yaml.
"""

import asyncio


class TextInput:
    async def listen(self) -> str:
        """Wait for a non-empty line on stdin and return it stripped.

        Raises EOFError when stdin closes (Ctrl-D), which ends the app loop.
        """
        while True:
            line = await asyncio.to_thread(input, "> ")
            if line.strip():
                return line.strip()
