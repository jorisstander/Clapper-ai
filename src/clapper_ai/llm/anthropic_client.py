"""Real answers from Claude. Optional: needs the `llm` extra and an API key.

    uv sync --extra llm
    export ANTHROPIC_API_KEY=sk-ant-...   # see .env.example

Then set `llm.type: anthropic` in config.yaml. Nothing else changes.
"""

# The answer-mode prompt. Kept in one constant so it's easy to find and tune.
ANSWER_PROMPT = (
    "You are answering on a tiny split-flap display. "
    "Reply in plain text only: no markdown, no line breaks, "
    "at most {max_chars} characters. Be concise and direct.\n"
    "{question}"
)


class AnthropicClient:
    MODEL = "claude-opus-4-8"

    def __init__(self, model: str = MODEL):
        try:
            from anthropic import AsyncAnthropic
        except ImportError as error:
            raise SystemExit(
                "The anthropic package is not installed. "
                "Run: uv sync --extra llm"
            ) from error
        self._client = AsyncAnthropic()
        self.model = model

    async def complete(self, prompt: str, *, max_chars: int) -> str:
        response = await self._client.messages.create(
            model=self.model,
            # Plain text is roughly one token per 3-4 chars; a small floor
            # keeps the model from being cut off mid-word on tiny boards.
            max_tokens=max(256, max_chars),
            messages=[
                {
                    "role": "user",
                    "content": ANSWER_PROMPT.format(max_chars=max_chars, question=prompt),
                }
            ],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return text.strip()[:max_chars]
