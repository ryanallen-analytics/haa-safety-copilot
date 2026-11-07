"""Thin wrapper around the Anthropic client that logs every call."""

import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from anthropic import Anthropic

FALLBACK_MODEL = "claude-haiku-5-5"
DEFAULT_LOG_PATH = Path("logs/llm_calls.jsonl")

# USD per million tokens: (input, output). Fill in from docs/notes/anthropic-api.md.
PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-haiku-5-5": (0.10, 0.50),
}


@dataclass
class LLMResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    stop_reason: str
    latency_s: float
    cost_usd: float | None


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Estimated cost in USD, or None if the model has no price entry."""
    prices = PRICES_PER_MTOK.get(model)
    if prices is None:
        return None
    input_price, output_price = prices
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000


class LLMClient:
    def __init__(
        self,
        client=None,
        model: str | None = None,
        log_path: Path = DEFAULT_LOG_PATH,
    ) -> None:
        # Tests pass in a fake client; real code uses the Anthropic SDK.
        self.client = client or Anthropic()
        self.model = model or os.getenv("ANTHROPIC_MODEL", FALLBACK_MODEL)
        self.log_path = Path(log_path)

    def complete(
        self, prompt: str, system: str | None = None, max_tokens: int = 500
    ) -> LLMResponse:
        kwargs = {"system": system} if system else {}
        start = time.perf_counter()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        latency_s = time.perf_counter() - start

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        result = LLMResponse(
            text=response.content[0].text,
            model=response.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            stop_reason=response.stop_reason,
            latency_s=round(latency_s, 3),
            cost_usd=estimate_cost(self.model, input_tokens, output_tokens),
        )
        self._log(result)
        return result

    def _log(self, result: LLMResponse) -> None:
        record = {"timestamp": datetime.now(UTC).isoformat(), **asdict(result)}
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
