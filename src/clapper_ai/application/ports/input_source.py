"""Port for where prompts come from (keyboard now; mic or phone later).

Note the asymmetry with the other two ports in this package: LLMClient and
DisplaySink are driven ports of AnswerQuestion — the use case calls out
through them. InputSource is not. It is consumed by the run loop in
__main__.py, which pulls a string and hands it to the use case, so it is a
port of the driving side.

It lives here for cohesion, not because the interactor owns it. Resolving
that properly means flipping input from pull to push so the adapter calls
execute() itself — a behavioural change, deliberately out of scope here.
"""

from typing import Protocol


class InputSource(Protocol):
    async def listen(self) -> str:
        """Block until the user says or types something; return the transcript.

        Raise EOFError when the source is exhausted — the run loop treats it
        as shutdown.
        """
        ...
