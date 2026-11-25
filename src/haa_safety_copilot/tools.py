"""Tools the weather research agent can call."""

from collections.abc import Callable
from dataclasses import dataclass

from haa_safety_copilot.aviation_weather import MetarReport, get_metar
from haa_safety_copilot.flight_conditions import assess


@dataclass(frozen=True)
class Tool:
    definition: dict  # what the model sees
    run: Callable[..., dict]  # what your code executes


GET_METAR = {
    "name": "get_metar",
    "description": (
        "Get the latest METAR (current observed weather) for one or more airports. "
        "For each station it returns the raw METAR text, the observation time in "
        "UTC, decoded wind, visibility, ceiling, reported weather, and a flight "
        "category (VFR, MVFR, IFR, LIFR) computed by code from the decoded data. "
        "It also flags automated reports and stations whose sensors need "
        "maintenance. Use it for current conditions only; it does not forecast. "
        "Stations with no recent report are listed under 'no_data'. Use 4-character "
        "ICAO codes; most US airports are 'K' plus the 3-letter code (PHX -> KPHX)."
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


def summarize_metar(report: MetarReport) -> dict:
    """Decoded, code-computed fields plus the raw text the answer must quote."""
    conditions = assess(report)
    vis = conditions.visibility
    return {
        "station": report.icao_id,
        "raw": report.raw,
        "observed_utc": report.obs_time.isoformat(),
        "flight_category": conditions.flight_category,
        "ceiling_ft_agl": conditions.ceiling_ft,
        "visibility_sm": vis.statute_miles if vis else None,
        "visibility_or_more": vis.at_least if vis else False,
        "wind_direction": report.wind_dir,
        "wind_speed_kt": report.wind_speed_kt,
        "wind_gust_kt": report.wind_gust_kt,
        "reported_weather": list(conditions.reported_weather),
        "automated_report": "AUTO" in report.raw.split(),
        "maintenance_flag": report.raw.rstrip().endswith("$"),
    }


def run_get_metar(stations: list[str]) -> dict:
    reports = get_metar(stations)
    found = {r.icao_id for r in reports}
    return {
        "reports": [summarize_metar(r) for r in reports],
        "no_data": [
            s.strip().upper() for s in stations if s.strip().upper() not in found
        ],
    }


TOOLS: dict[str, Tool] = {"get_metar": Tool(GET_METAR, run_get_metar)}
