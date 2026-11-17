import json
from pathlib import Path

import httpx
import pytest

from haa_safety_copilot.aviation_weather import (
    USER_AGENT,
    MetarReport,
    WeatherAPIError,
    _normalize_stations,
    clear_cache,
    get_metar,
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


def test_no_data_returns_empty_list():
    client, _ = mock_client(lambda req: httpx.Response(204))

    assert get_metar(["KZZZ"], client=client) == []


def test_http_error_raises_weather_api_error():
    client, _ = mock_client(lambda req: httpx.Response(500))

    with pytest.raises(WeatherAPIError, match="HTTP 500"):
        get_metar(["KPHX"], client=client)


def test_timeout_raises_weather_api_error():
    def timeout(req: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=req)

    client, _ = mock_client(timeout)

    with pytest.raises(WeatherAPIError, match="timed out"):
        get_metar(["KPHX"], client=client)


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
