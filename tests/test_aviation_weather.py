import json
from pathlib import Path

import httpx
import pytest

from haa_safety_copilot.aviation_weather import (
    USER_AGENT,
    MetarReport,
    TafPeriod,
    TafReport,
    WeatherAPIError,
    _normalize_stations,
    clear_cache,
    get_metar,
    get_taf,
)

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


@pytest.fixture(autouse=True)
def fresh_cache():
    clear_cache()
    yield
    clear_cache()


def mock_client(handler) -> tuple[httpx.Client, list[httpx.Request]]:
    """An httpx client whose responses come from handler; records every request."""
    requests: list[httpx.Request] = []

    def recording_handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    return httpx.Client(transport=httpx.MockTransport(recording_handler)), requests


def multi_fixture() -> list[dict]:
    return json.loads((FIXTURES / "metar_multi.json").read_text(encoding="utf-8"))


def test_success_parses_reports_and_sends_user_agent():
    client, requests = mock_client(
        lambda req: httpx.Response(200, json=multi_fixture())
    )

    reports = get_metar(["kphx", "KFLG", "KPRC"], client=client)

    assert len(reports) == 3
    assert requests[0].url.params["ids"] == "KPHX,KFLG,KPRC"
    assert requests[0].headers["User-Agent"] == USER_AGENT


FETCHERS = [get_metar, get_taf]


@pytest.mark.parametrize("fetch", FETCHERS)
def test_no_data_returns_empty_list(fetch):
    client, _ = mock_client(lambda req: httpx.Response(204))

    assert fetch(["KZZZ"], client=client) == []


@pytest.mark.parametrize("fetch", FETCHERS)
def test_http_error_raises_weather_api_error(fetch):
    client, _ = mock_client(lambda req: httpx.Response(500))

    with pytest.raises(WeatherAPIError, match="HTTP 500"):
        fetch(["KPHX"], client=client)


@pytest.mark.parametrize("fetch", FETCHERS)
def test_timeout_raises_weather_api_error(fetch):
    def timeout(req: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=req)

    client, _ = mock_client(timeout)

    with pytest.raises(WeatherAPIError, match="timed out"):
        fetch(["KPHX"], client=client)


def test_repeat_call_uses_cache():
    client, requests = mock_client(
        lambda req: httpx.Response(200, json=multi_fixture())
    )

    get_metar(["KPHX", "KFLG", "KPRC"], client=client)
    get_metar(["KPHX", "KFLG", "KPRC"], client=client)

    assert len(requests) == 1


def test_errors_are_not_cached():
    client, requests = mock_client(lambda req: httpx.Response(500))

    for _ in range(2):
        with pytest.raises(WeatherAPIError):
            get_metar(["KPHX"], client=client)

    assert len(requests) == 2


def load_fixture(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_fixture_taf_parses():
    taf = TafReport.model_validate(load_fixture("taf_kphx.json")[0])

    assert taf.icao_id == "KPHX"
    assert taf.periods
    assert all(p.time_to > p.time_from for p in taf.periods)
    assert all(p.change in {None, "FM", "BECMG", "TEMPO", "PROB"} for p in taf.periods)
    assert taf.valid_from < taf.valid_to


def test_blank_visibility_becomes_none():
    period = TafPeriod.model_validate(
        {"timeFrom": 1794700800, "timeTo": 1794715200, "visib": ""}
    )

    assert period.visibility is None


def test_get_taf_calls_taf_endpoint():
    client, requests = mock_client(
        lambda req: httpx.Response(200, json=load_fixture("taf_kphx.json"))
    )

    tafs = get_taf(["kphx"], client=client)

    assert tafs[0].icao_id == "KPHX"
    assert requests[0].url.path.endswith("/taf")


def test_metar_and_taf_are_cached_separately():
    def handler(req: httpx.Request) -> httpx.Response:
        name = "taf_kphx.json" if req.url.path.endswith("/taf") else "metar_multi.json"
        return httpx.Response(200, json=load_fixture(name))

    client, requests = mock_client(handler)

    get_metar(["KPHX"], client=client)
    get_taf(["KPHX"], client=client)

    assert len(requests) == 2
