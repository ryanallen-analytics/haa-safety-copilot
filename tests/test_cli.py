import json
from pathlib import Path

from typer.testing import CliRunner

from haa_safety_copilot import cli
from haa_safety_copilot.aviation_weather import MetarReport, TafReport, WeatherAPIError

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


def load(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def fake_metars(stations):
    return [MetarReport.model_validate(item) for item in load("metar_multi.json")]


def fake_tafs(stations):
    return [TafReport.model_validate(item) for item in load("taf_kphx.json")]


def test_weather_prints_metar_taf_and_disclaimer(monkeypatch):
    monkeypatch.setattr(cli, "get_metar", fake_metars)
    monkeypatch.setattr(cli, "get_taf", fake_tafs)

    result = runner.invoke(cli.app, ["weather", "kphx"])

    assert result.exit_code == 0
    assert "METAR KPHX" in result.output
    assert "TAF KPHX" in result.output
    assert "pilot in command" in result.output


def test_station_without_data_says_so(monkeypatch):
    monkeypatch.setattr(cli, "get_metar", lambda stations: [])
    monkeypatch.setattr(cli, "get_taf", lambda stations: [])

    result = runner.invoke(cli.app, ["weather", "KZZZ"])

    assert result.exit_code == 0
    assert "no METAR available" in result.output
    assert "no TAF available" in result.output


def test_no_taf_flag_skips_the_taf_request(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "get_metar", fake_metars)
    monkeypatch.setattr(cli, "get_taf", lambda stations: calls.append(stations) or [])

    result = runner.invoke(cli.app, ["weather", "KPHX", "--no-taf"])

    assert result.exit_code == 0
    assert calls == []


def test_api_failure_exits_with_code_1(monkeypatch):
    def fail(stations):
        raise WeatherAPIError("weather request timed out")

    monkeypatch.setattr(cli, "get_metar", fail)

    result = runner.invoke(cli.app, ["weather", "KPHX"])

    assert result.exit_code == 1
    assert "unavailable" in result.output


def test_bad_station_code_exits_with_code_2():
    result = runner.invoke(cli.app, ["weather", "PHX"])

    assert result.exit_code == 2
