"""Client for the aviationweather.gov Data API."""

import time
from datetime import datetime

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

BASE_URL = "https://aviationweather.gov/api/data"
USER_AGENT = (
    "haa-safety-copilot/0.1 "
    "(+https://github.com/ryanallen-analytics/haa-safety-copilot)"
)
TIMEOUT_S = 10.0


class WeatherAPIError(Exception):
    """The weather API could not be reached or returned an error."""


class CloudLayer(BaseModel):
    cover: str
    base: int | None = None  # feet AGL


class Conditions(BaseModel):
    """Fields shared by METARs and TAF forecast periods."""

    model_config = ConfigDict(extra="ignore")

    wind_dir: int | str | None = Field(None, alias="wdir")  # degrees or "VRB"
    wind_speed_kt: int | None = Field(None, alias="wspd")
    wind_gust_kt: int | None = Field(None, alias="wgst")
    visibility: str | float | None = Field(None, alias="visib")  # "10+", "6+", 3
    wx_string: str | None = Field(None, alias="wxString")
    clouds: list[CloudLayer] = Field(default_factory=list)

    @field_validator("visibility", mode="before")
    @classmethod
    def blank_visibility_is_none(cls, value):
        """The TAF sometimes sends "" for no visibility group; treat it as missing."""
        return None if value == "" else value


class MetarReport(Conditions):
    """One METAR as the API returns it."""

    icao_id: str = Field(alias="icaoId")
    raw: str = Field(alias="rawOb")
    obs_time: datetime = Field(alias="obsTime")  # epoch seconds -> UTC datetime


class TafPeriod(Conditions):
    """One forecast period inside a TAF."""

    time_from: datetime = Field(alias="timeFrom")
    time_to: datetime = Field(alias="timeTo")
    change: str | None = Field(None, alias="fcstChange")  # None, FM, BECMG, TEMPO, PROB
    probability: int | None = None


class TafReport(BaseModel):
    """One TAF as the API returns it."""

    model_config = ConfigDict(extra="ignore")

    icao_id: str = Field(alias="icaoId")
    raw: str = Field(alias="rawTAF")
    periods: list[TafPeriod] = Field(alias="fcsts")

    @property
    def valid_from(self) -> datetime:
        return min(p.time_from for p in self.periods)

    @property
    def valid_to(self) -> datetime:
        return max(p.time_to for p in self.periods)


def _normalize_stations(stations: list[str]) -> str:
    """Uppercase and check ICAO codes before any request is made."""
    cleaned = [s.strip().upper() for s in stations]
    bad = [s for s in cleaned if len(s) != 4 or not s.isalnum()]
    if not cleaned or bad:
        raise ValueError(f"Expected 4-character ICAO station codes, got: {stations}")
    return ",".join(cleaned)


CACHE_TTL_S = 300  # 5 minutes; METARs update about hourly
_cache: dict[tuple, tuple[float, list[dict]]] = {}


def clear_cache() -> None:
    _cache.clear()


def _get_json(endpoint: str, params: dict, client: httpx.Client | None) -> list[dict]:
    key = (endpoint, tuple(sorted(params.items())))
    cached = _cache.get(key)
    if cached is not None and time.monotonic() - cached[0] < CACHE_TTL_S:
        return cached[1]

    owns_client = client is None
    if client is None:
        client = httpx.Client()
    try:
        response = client.get(
            f"{BASE_URL}/{endpoint}",
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_S,
        )
        if response.status_code == 204:  # valid request, no data available
            data: list[dict] = []
        else:
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as err:
        raise WeatherAPIError(
            f"{endpoint} request timed out after {TIMEOUT_S}s"
        ) from err
    except httpx.HTTPStatusError as err:
        status = err.response.status_code
        raise WeatherAPIError(f"{endpoint} request failed with HTTP {status}") from err
    except httpx.RequestError as err:
        raise WeatherAPIError(f"Could not reach the weather API: {err}") from err
    finally:
        if owns_client:
            client.close()

    _cache[key] = (time.monotonic(), data)
    return data


def get_metar(
    stations: list[str], client: httpx.Client | None = None
) -> list[MetarReport]:
    """Latest METAR for each station. Stations with no data are simply absent."""
    params = {"ids": _normalize_stations(stations), "format": "json"}
    return [
        MetarReport.model_validate(item) for item in _get_json("metar", params, client)
    ]


def get_taf(stations: list[str], client: httpx.Client | None = None) -> list[TafReport]:
    """Latest TAF for each station. Stations with no TAF are simply absent."""
    params = {"ids": _normalize_stations(stations), "format": "json"}
    return [TafReport.model_validate(item) for item in _get_json("taf", params, client)]
