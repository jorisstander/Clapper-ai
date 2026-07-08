"""Real answers from Claude. Optional: needs the `llm` extra and an API key.

    pip install "clapper-ai[llm]"
    export ANTHROPIC_API_KEY=sk-ant-...   # see .env.example

Then set `llm.type: anthropic` in config.yaml. Nothing else changes.
"""


class AnthropicClient:
    MODEL = "claude-opus-4-8"

    def __init__(self, model: str = MODEL):
        try:
            from anthropic import AsyncAnthropic
        except ImportError as error:
            raise SystemExit(
                "The anthropic package is not installed. "
                'Run: pip install "clapper-ai[llm]"'
            ) from error
        # Reads ANTHROPIC_API_KEY (or other Anthropic credentials) from the
        # environment — keys never live in code or config.
        self._client = AsyncAnthropic()
        self.model = model

    async def complete(self, prompt: str, *, max_chars: int) -> str:
        response = await self._client.messages.create(
            model=self.model,
            # Plain text is roughly one token per 3-4 chars; a small floor
            # keeps the model from being cut off mid-word on tiny boards.
            max_tokens=max(256, max_chars),
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return text.strip()[:max_chars]
