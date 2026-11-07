import pytest

from haa_safety_copilot.units import statute_to_nautical_miles


def test_statute_to_nautical_miles():
    assert statute_to_nautical_miles(10) == pytest.approx(8.68976)