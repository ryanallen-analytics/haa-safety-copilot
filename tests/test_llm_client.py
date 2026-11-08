import json

import pytest


def test_complete_returns_response_and_logs_call(llm_client, fake_anthropic):
    result = llm_client.complete("hello", system="Be brief.")

    assert result.text == "fake reply"
    # 1,000 in x $0.10/M + 2,000 out x $0.50/M = $0.0011
    assert result.cost_usd == pytest.approx(0.0011)
    assert fake_anthropic.messages.calls[0]["system"] == "Be brief."

    lines = llm_client.log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["stop_reason"] == "end_turn"


def test_truncation_is_reported(llm_client, fake_anthropic):
    fake_anthropic.messages.stop_reason = "max_tokens"

    result = llm_client.complete("hello")

    assert result.stop_reason == "max_tokens"
    assert "system" not in fake_anthropic.messages.calls[0]


def test_thinking_blocks_are_skipped(llm_client, fake_anthropic):
    fake_anthropic.messages.thinking = "Let me reason about this..."

    result = llm_client.complete("hello")

    assert result.text == "fake reply"
