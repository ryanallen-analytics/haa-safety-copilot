"""Tools the weather research agent can call."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from haa_safety_copilot.aviation_weather import MetarReport, get_metar
from haa_safety_copilot.flight_conditions import assess

HPA_PER_INHG = 33.8639


@dataclass(frozen=True)
class Tool:
    definition: dict  # what the model sees
    run: Callable[..., dict]  # what your code executes


GET_METAR = {
    "name": "get_metar",
    "description": (
        "Get the latest METAR (current observed weather) for one or more airports. "
        "For each station it returns the raw METAR text and decoded fields "
        "computed by code: observation time (UTC) and age in minutes, flight "
        "category (VFR, MVFR, IFR, LIFR), ceiling, cloud layers, visibility, "
        "wind, temperature, dewpoint and their spread, altimeter in inches of "
        "mercury, and reported weather. report_source states whether a human "
        "observer augmented the report; repeat it as written. maintenance_flag is "
        "true when the raw report ends with '$', meaning the station's sensors "
        "need maintenance. Use it for current conditions only; it does not "
        "forecast. Stations with no recent report are listed under "
        "'no_data'. Use 4-character ICAO codes; most US airports are 'K' plus "
        "the 3-letter code (PHX -> KPHX)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "stations": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 10,
                "description": 'ICAO station codes, e.g. ["KPHX", "KFLG"].',
            }
        },
        "required": ["stations"],
    },
}


def summarize_metar(report: MetarReport, now: datetime) -> dict:
    """Every value the answer may state, decoded and computed by code."""
    conditions = assess(report)
    vis = conditions.visibility
    tokens = report.raw.split()

    spread = None
    if report.temp_c is not None and report.dewpoint_c is not None:
        spread = round(report.temp_c - report.dewpoint_c, 1)
    altimeter = None
    if report.altimeter_hpa is not None:
        altimeter = round(report.altimeter_hpa / HPA_PER_INHG, 2)

    return {
        "station": report.icao_id,
        "raw": report.raw,
        "observed_utc": report.obs_time.isoformat(),
        "observed_minutes_ago": round((now - report.obs_time).total_seconds() / 60),
        "flight_category": conditions.flight_category,
        "ceiling_ft_agl": conditions.ceiling_ft,
        "cloud_layers": [
            {"cover": c.cover, "base_ft_agl": c.base} for c in report.clouds
        ],
        "visibility_sm": vis.statute_miles if vis else None,
        "visibility_or_more": vis.at_least if vis else False,
        "wind_direction": report.wind_dir,
        "wind_speed_kt": report.wind_speed_kt,
        "wind_gust_kt": report.wind_gust_kt,
        "temperature_c": report.temp_c,
        "dewpoint_c": report.dewpoint_c,
        "temp_dewpoint_spread_c": spread,
        "altimeter_inhg": altimeter,
        "reported_weather": list(conditions.reported_weather),
        "report_source": (
            "fully automated (AUTO): no human observer checked this report"
            if "AUTO" in tokens
            else "augmented by a human observer"
        ),
        "maintenance_flag": report.raw.rstrip().endswith("$"),
    }


def run_get_metar(stations: list[str], now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    reports = get_metar(stations)
    found = {r.icao_id for r in reports}
    return {
        "reports": [summarize_metar(r, now) for r in reports],
        "no_data": [
            s.strip().upper() for s in stations if s.strip().upper() not in found
        ],
    }


TOOLS: dict[str, Tool] = {"get_metar": Tool(GET_METAR, run_get_metar)}
