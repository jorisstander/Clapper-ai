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
    MODEL = "claude-opus-5"

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
            # Deliberately far above what the board can show. Opus 5 thinks by
            # default and max_tokens caps thinking + answer together, so a
            # board-sized budget can be spent entirely on thinking. Measured at
            # 256: "what is 7^23" came back as a thinking block, stop_reason
            # max_tokens, and no text at all — a blank board. Headroom is free
            # (billing is per token generated; short answers stay short), and
            # the reply is truncated to max_chars below.
            max_tokens=max(2048, max_chars),
            messages=[
                {
                    "role": "user",
                    "content": ANSWER_PROMPT.format(max_chars=max_chars, question=prompt),
                }
            ],
        )
        texts = [block.text for block in response.content if block.type == "text"]
        if response.stop_reason == "refusal" or not texts:
            # The AnswerQuestion catches this and shows its apology grid.
            raise RuntimeError(f"Model refused or gave no answer ({response.stop_reason})")
        return "".join(texts).strip()[:max_chars]
