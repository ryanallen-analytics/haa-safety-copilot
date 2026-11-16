import json
from pathlib import Path

import pytest

from haa_safety_copilot.aviation_weather import MetarReport, _normalize_stations

FIXTURES = Path(__file__).parent / "fixtures"


def test_fixture_metars_parse():
    data = json.loads((FIXTURES / "metar_multi.json").read_text(encoding="utf-8"))

    reports = [MetarReport.model_validate(item) for item in data]

    assert {r.icao_id for r in reports} == {"KPHX", "KFLG", "KPRC"}
    assert all(r.obs_time.tzinfo is not None for r in reports)
    assert all(r.raw.startswith(("METAR", "SPECI")) for r in reports)


@pytest.mark.parametrize("bad", [[], ["PHX"], ["KPHX", "K-FL"], ["KPHXX"]])
def test_bad_station_codes_are_rejected(bad):
    with pytest.raises(ValueError):
        _normalize_stations(bad)
