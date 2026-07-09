"""The default LLM: no network, no key, fully deterministic.

It echoes the whole prompt back, so the board visibly reacts to whatever
you type — good enough to demo the pipeline.
"""


class FakeLLMClient:
    async def complete(self, prompt: str, *, max_chars: int) -> str:
        question = prompt.strip()
        reply = f"YOU SAID {question}" if question else "HELLO FROM THE FAKE LLM"
        return reply[:max_chars]
