import pytest

from haa_safety_copilot.llm_client import estimate_cost


@pytest.mark.parametrize(
    ("input_tokens", "output_tokens", "expected"),
    [
        (0, 0, 0.0),
        (1_000_000, 0, 0.10),  # input rate alone
        (0, 1_000_000, 0.50),  # output rate alone
        (41, 163, 0.0000856),  # your real hello_llm call
    ],
)
def test_estimate_cost_haiku(input_tokens, output_tokens, expected):
    assert estimate_cost(
        "claude-haiku-5-5", input_tokens, output_tokens
    ) == pytest.approx(expected)


def test_estimate_cost_unknown_model_is_none():
    assert estimate_cost("not-a-real-model", 100, 100) is None
