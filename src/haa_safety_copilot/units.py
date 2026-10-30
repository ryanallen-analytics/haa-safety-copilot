"""Unit conversions used in flight planning."""

SM_TO_NM = 0.868976


def statute_to_nautical_miles(statute_miles: float) -> float:
    """Convert statute miles to nautical miles."""
    return statute_miles * SM_TO_NM
