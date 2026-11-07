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
