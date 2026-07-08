"""The default LLM: no network, no key, fully deterministic.

It echoes the question (the last line of the prompt) so the board visibly
reacts to whatever you type — good enough to demo the whole pipeline.
"""


class FakeLLMClient:
    async def complete(self, prompt: str, *, max_chars: int) -> str:
        question = prompt.strip().splitlines()[-1].strip()
        reply = f"YOU SAID {question}" if question else "HELLO FROM THE FAKE LLM"
        return reply[:max_chars]
