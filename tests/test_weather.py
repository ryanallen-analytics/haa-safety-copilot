import pytest
from pydantic import ValidationError

from haa_safety_copilot.weather import WeatherSummary

VALID = {
    "station": "KPHX",
    "observed_at": "2026-11-07T18:51:00Z",
    "wind": {"direction_deg": 270, "speed_kt": 8},
    "visibility_sm": 10,
    "ceiling_ft_agl": None,
    "hazards": [],
}


def test_valid_summary_parses():
    summary = WeatherSummary.model_validate(VALID)

    assert summary.observed_at.tzinfo is not None
    assert summary.wind.gust_kt is None
    assert summary.ceiling_ft_agl is None


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("station", "phx"),
        ("visibility_sm", -1),
        ("ceiling_ft_agl", -500),
        ("wind", {"direction_deg": 400, "speed_kt": 8}),
        ("wind", {"direction_deg": 270, "speed_kt": 20, "gust_kt": 15}),
    ],
)
def test_invalid_values_are_rejected(field, bad_value):
    data = {**VALID, field: bad_value}

    with pytest.raises(ValidationError):
        WeatherSummary.model_validate(data)
