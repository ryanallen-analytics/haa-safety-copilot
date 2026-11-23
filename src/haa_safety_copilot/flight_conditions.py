"""Flight conditions computed in code from decoded weather data.

Uses the standard NWS flight categories. These describe conditions; they are
not go/no-go minimums. HAA minimums come from the regulations in Phase 2.
"""

from dataclasses import dataclass
from fractions import Fraction
from typing import NamedTuple

from haa_safety_copilot.aviation_weather import CloudLayer, Conditions

CEILING_COVERS = {"BKN", "OVC", "OVX", "VV"}
CATEGORY_ORDER = ["LIFR", "IFR", "MVFR", "VFR"]  # worst first


class Visibility(NamedTuple):
    statute_miles: float
    at_least: bool  # True for "10+" / "6+" / P6SM: the real value may be higher


def parse_visibility(value: str | float | None) -> Visibility | None:
    """Turn the API's visibility ("10+", "1 1/2", 3) into statute miles."""
    if value is None:
        return None
    if isinstance(value, int | float):
        return Visibility(float(value), at_least=False)

    text = value.strip().upper().removesuffix("SM")
    at_least = text.endswith("+") or text.startswith("P")
    # "M1/4" means less than 1/4 SM; 0.25 is an upper bound, which still
    # lands in the worst category, so it is safe to use as the value.
    text = text.rstrip("+").removeprefix("P").removeprefix("M").strip()
    if not text:
        raise ValueError(f"Unrecognized visibility: {value!r}")
    try:
        miles = sum(Fraction(part) for part in text.split())
    except (ValueError, ZeroDivisionError) as err:
        raise ValueError(f"Unrecognized visibility: {value!r}") from err
    return Visibility(float(miles), at_least)


def ceiling_ft(clouds: list[CloudLayer]) -> int | None:
    """Lowest broken, overcast, or obscured layer. None means no ceiling."""
    bases = [c.base for c in clouds if c.cover in CEILING_COVERS and c.base is not None]
    return min(bases, default=None)


def _ceiling_category(ceiling: int | None) -> str:
    if ceiling is None or ceiling > 3000:
        return "VFR"
    if ceiling >= 1000:
        return "MVFR"
    if ceiling >= 500:
        return "IFR"
    return "LIFR"


def _visibility_category(miles: float) -> str:
    if miles > 5:
        return "VFR"
    if miles >= 3:
        return "MVFR"
    if miles >= 1:
        return "IFR"
    return "LIFR"


def flight_category(ceiling: int | None, visibility: Visibility | None) -> str | None:
    """The worse of the ceiling and visibility categories.

    Returns None when visibility is missing: unknown is never assumed to be VFR.
    """
    if visibility is None:
        return None
    categories = [
        _ceiling_category(ceiling),
        _visibility_category(visibility.statute_miles),
    ]
    return min(categories, key=CATEGORY_ORDER.index)


@dataclass(frozen=True)
class FlightConditions:
    ceiling_ft: int | None
    visibility: Visibility | None
    flight_category: str | None
    reported_weather: tuple[str, ...]  # raw codes from the report, e.g. ("-SN", "BR")


def assess(conditions: Conditions) -> FlightConditions:
    """Derive flight conditions from a METAR or a TAF period."""
    ceiling = ceiling_ft(conditions.clouds)
    visibility = parse_visibility(conditions.visibility)
    return FlightConditions(
        ceiling_ft=ceiling,
        visibility=visibility,
        flight_category=flight_category(ceiling, visibility),
        reported_weather=tuple(conditions.wx_string.split())
        if conditions.wx_string
        else (),
    )
