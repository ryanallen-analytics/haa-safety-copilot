import json
from datetime import date

import pytest

from haa_safety_copilot.metar_parser import MetarParseError, parse_metar

METAR = "KFLG 071856Z 23018G27KT 3SM -SN BR BKN008 OVC015 M02/M04 A2992"
REF_DATE = date(2026, 11, 7)

VALID_JSON = json.dumps(
    {
        "station": "KFLG",
        "observed_at": "2026-11-07T18:56:00Z",
        "wind": {"direction_deg": 230, "speed_kt": 18, "gust_kt": 27},
        "visibility_sm": 3,
        "ceiling_ft_agl": 800,
        "hazards": ["light snow", "mist"],
    }
)
INVALID_JSON = VALID_JSON.replace('"gust_kt": 27', '"gust_kt": 10')  # gust < speed


def test_valid_reply_parses_on_first_try(llm_client, fake_anthropic):
    fake_anthropic.messages.replies = [VALID_JSON]

    summary = parse_metar(METAR, llm_client, REF_DATE)

    assert summary.ceiling_ft_agl == 800
    assert len(fake_anthropic.messages.calls) == 1


def test_invalid_reply_triggers_one_retry_with_errors(llm_client, fake_anthropic):
    fake_anthropic.messages.replies = [INVALID_JSON, VALID_JSON]

    summary = parse_metar(METAR, llm_client, REF_DATE)

    assert summary.wind.gust_kt == 27
    assert len(fake_anthropic.messages.calls) == 2
    retry_prompt = fake_anthropic.messages.calls[1]["messages"][0]["content"]
    assert "failed validation" in retry_prompt


def test_two_invalid_replies_raise(llm_client, fake_anthropic):
    fake_anthropic.messages.replies = [INVALID_JSON, "not json at all"]

    with pytest.raises(MetarParseError):
        parse_metar(METAR, llm_client, REF_DATE)
    assert len(fake_anthropic.messages.calls) == 2


def test_code_fences_are_tolerated(llm_client, fake_anthropic):
    fake_anthropic.messages.replies = [f"```json\n{VALID_JSON}\n```"]

    assert parse_metar(METAR, llm_client, REF_DATE).station == "KFLG"
