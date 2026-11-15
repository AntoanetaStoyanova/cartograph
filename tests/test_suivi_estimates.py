import pytest

from cartograph.bin.suivi.estimates import Estimates, estimate
from cartograph.config import (
    ACTIONS_USD_PER_MIN,
    GRID_KG_CO2E_PER_KWH,
    RUNNER_WATTS,
)


def test_runner_watts_follow_cloud_carbon_footprint() -> None:
    assert RUNNER_WATTS == pytest.approx(18.19, abs=0.01)


def test_estimate_from_minutes() -> None:
    result = estimate(billed_minutes=600)

    assert result.actions_usd == pytest.approx(600 * ACTIONS_USD_PER_MIN)
    assert result.energy_kwh == pytest.approx(RUNNER_WATTS * 10 / 1000)
    assert result.co2e_kg == pytest.approx(
        RUNNER_WATTS * 10 / 1000 * GRID_KG_CO2E_PER_KWH
    )


def test_estimate_of_an_empty_month() -> None:
    assert estimate(billed_minutes=0) == Estimates(0.0, 0.0, 0.0)
