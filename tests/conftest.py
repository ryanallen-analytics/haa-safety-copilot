from types import SimpleNamespace

import pytest

from haa_safety_copilot.llm_client import LLMClient


class FakeMessages:
    """Stands in for client.messages; records each call instead of hitting the API."""

    def __init__(self, stop_reason: str = "end_turn") -> None:
        self.stop_reason = stop_reason
        self.calls: list[dict] = []
        self.replies: list[str] = []  # queued replies; falls back to "fake reply"
        self.thinking: str | None = None  # if set, a thinking block comes first

    def create(self, **kwargs):
        self.calls.append(kwargs)
        text = self.replies.pop(0) if self.replies else "fake reply"
        content = [SimpleNamespace(type="text", text=text)]
        if self.thinking is not None:
            content.insert(0, SimpleNamespace(type="thinking", thinking=self.thinking))
        return SimpleNamespace(
            content=content,
            model=kwargs["model"],
            stop_reason=self.stop_reason,
            usage=SimpleNamespace(input_tokens=1000, output_tokens=2000),
        )


class FakeAnthropic:
    def __init__(self) -> None:
        self.messages = FakeMessages()


@pytest.fixture
def fake_anthropic():
    return FakeAnthropic()


@pytest.fixture
def llm_client(fake_anthropic, tmp_path):
    return LLMClient(
        client=fake_anthropic,
        model="claude-haiku-5-5",
        log_path=tmp_path / "calls.jsonl",
    )
