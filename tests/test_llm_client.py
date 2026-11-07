import json
from types import SimpleNamespace

import pytest

from haa_safety_copilot.llm_client import LLMClient


class FakeMessages:
    """Stands in for client.messages; records each call instead of hitting the API."""

    def __init__(self, stop_reason: str = "end_turn") -> None:
        self.stop_reason = stop_reason
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(text="fake reply")],
            model=kwargs["model"],
            stop_reason=self.stop_reason,
            usage=SimpleNamespace(input_tokens=1000, output_tokens=2000),
        )


class FakeAnthropic:
    def __init__(self, stop_reason: str = "end_turn") -> None:
        self.messages = FakeMessages(stop_reason)


def test_complete_returns_response_and_logs_call(tmp_path):
    fake = FakeAnthropic()
    log_path = tmp_path / "calls.jsonl"
    client = LLMClient(client=fake, model="claude-haiku-5-5", log_path=log_path)

    result = client.complete("hello", system="Be brief.")

    assert result.text == "fake reply"
    # 1,000 in x $0.10/M + 2,000 out x $0.50/M = $0.0011
    assert result.cost_usd == pytest.approx(0.0011)
    assert fake.messages.calls[0]["system"] == "Be brief."

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["stop_reason"] == "end_turn"


def test_truncation_and_unknown_model_are_visible(tmp_path):
    fake = FakeAnthropic(stop_reason="max_tokens")
    client = LLMClient(
        client=fake, model="unknown-model", log_path=tmp_path / "c.jsonl"
    )

    result = client.complete("hello")

    assert result.stop_reason == "max_tokens"
    assert result.cost_usd is None
    assert "system" not in fake.messages.calls[0]
