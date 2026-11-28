from datetime import UTC, datetime

import pytest

from haa_safety_copilot import tools
from haa_safety_copilot.aviation_weather import MetarReport

NOW = datetime(2026, 11, 25, 5, 34, tzinfo=UTC)


def make_report(raw: str, **fields) -> MetarReport:
    data = {
        "icaoId": raw.split()[1],
        "rawOb": raw,
        "obsTime": "2026-11-25T04:57:00Z",
        "wdir": 70,
        "wspd": 5,
        "visib": "10+",
        "clouds": [],
    }
    data.update(fields)
    return MetarReport.model_validate(data)


KFLG = "METAR KFLG 250457Z 07005KT 10SM CLR 01/M07 A3033 RMK AO2 SLP250 T00061072 $"


def test_decoded_values_are_computed_in_code():
    report = make_report(KFLG, temp=0.6, dewp=-7.2, altim=1027.1)

    summary = tools.summarize_metar(report, NOW)

    assert summary["altimeter_inhg"] == 30.33  # matches A3033 in the raw text
    assert summary["temp_dewpoint_spread_c"] == 7.8
    assert summary["observed_minutes_ago"] == 37
    assert summary["maintenance_flag"] is True


def test_missing_values_stay_none():
    summary = tools.summarize_metar(make_report(KFLG), NOW)

    assert summary["altimeter_inhg"] is None
    assert summary["temp_dewpoint_spread_c"] is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (KFLG, "augmented by a human observer"),
        (
            "METAR KPRC 250453Z AUTO 21004KT 10SM CLR 03/M04 A3026 RMK AO2",
            "fully automated (AUTO): no human observer checked this report",
        ),
    ],
)
def test_report_source_is_written_by_code(raw, expected):
    summary = tools.summarize_metar(make_report(raw), NOW)

    assert summary["report_source"] == expected


def test_cloud_layers_are_decoded():
    report = make_report(KFLG, clouds=[{"cover": "SCT", "base": 25000}])

    layers = tools.summarize_metar(report, NOW)["cloud_layers"]

    assert layers == [{"cover": "SCT", "base_ft_agl": 25000}]


def test_stations_without_reports_are_listed(monkeypatch):
    monkeypatch.setattr(tools, "get_metar", lambda stations: [make_report(KFLG)])

    result = tools.run_get_metar(["kflg", "KZZZ"], now=NOW)

    assert [r["station"] for r in result["reports"]] == ["KFLG"]
    assert result["no_data"] == ["KZZZ"]
