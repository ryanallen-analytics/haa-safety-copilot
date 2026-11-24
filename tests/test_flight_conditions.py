import json
from pathlib import Path

import pytest

from haa_safety_copilot.aviation_weather import CloudLayer, MetarReport
from haa_safety_copilot.flight_conditions import (
    Visibility,
    assess,
    ceiling_ft,
    flight_category,
    parse_visibility,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        (10, Visibility(10.0, False)),
        (1.5, Visibility(1.5, False)),
        ("10+", Visibility(10.0, True)),
        ("6+", Visibility(6.0, True)),
        ("P6SM", Visibility(6.0, True)),
        ("1/2", Visibility(0.5, False)),
        ("1 1/2", Visibility(1.5, False)),
    ],
)
def test_parse_visibility(raw, expected):
    assert parse_visibility(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "1/0"])
def test_unparseable_visibility_raises(raw):
    with pytest.raises(ValueError):
        parse_visibility(raw)


@pytest.mark.parametrize(
    ("layers", "expected"),
    [
        ([], None),
        ([("FEW", 250)], None),  # FEW is not a ceiling
        ([("SCT", 800), ("BKN", 1500)], 1500),  # SCT is not a ceiling either
        ([("BKN", 800), ("OVC", 1500)], 800),  # the lowest qualifying layer
        ([("OVX", 200)], 200),  # sky obscured: vertical visibility
    ],
)
def test_ceiling_is_lowest_broken_or_overcast_layer(layers, expected):
    clouds = [CloudLayer(cover=cover, base=base) for cover, base in layers]
    assert ceiling_ft(clouds) == expected


@pytest.mark.parametrize(
    ("ceiling", "miles", "expected"),
    [
        (None, 10, "VFR"),
        (3100, 6, "VFR"),
        (3000, 10, "MVFR"),  # a 3,000 ft ceiling is MVFR, not VFR
        (None, 5, "MVFR"),  # exactly 5 SM is MVFR
        (999, 10, "IFR"),
        (5000, 2.5, "IFR"),
        (499, 10, "LIFR"),
        (800, 0.5, "LIFR"),  # the worse of the two wins
    ],
)
def test_flight_category_boundaries(ceiling, miles, expected):
    assert flight_category(ceiling, Visibility(miles, False)) == expected


def test_missing_visibility_is_not_assumed_vfr():
    assert flight_category(None, None) is None


def test_fixture_metars_get_a_category():
    data = json.loads((FIXTURES / "metar_multi.json").read_text(encoding="utf-8"))

    for item in data:
        result = assess(MetarReport.model_validate(item))
        assert result.flight_category in {"VFR", "MVFR", "IFR", "LIFR"}
