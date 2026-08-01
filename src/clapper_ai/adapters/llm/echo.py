"""The default LLM: no network, no key, fully deterministic.

It echoes the whole prompt back, so the board visibly reacts to whatever you
type — good enough to demo the pipeline without an API key.

Named echo rather than fake because it is a real shipped adapter, not a test
double: config.yaml selects it by default, under the value `fake` — the
config name is public interface and was deliberately left alone.
"""


class EchoLLMClient:
    async def complete(self, prompt: str, *, max_chars: int) -> str:
        question = prompt.strip()
        reply = f"YOU SAID {question}" if question else "HELLO FROM THE FAKE LLM"
        return reply[:max_chars]
