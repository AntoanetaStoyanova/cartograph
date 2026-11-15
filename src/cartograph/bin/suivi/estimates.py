"""Équivalent payant et énergie estimée des minutes Actions d'un mois."""

from dataclasses import dataclass

from cartograph.config import (
    ACTIONS_USD_PER_MIN,
    GRID_KG_CO2E_PER_KWH,
    RUNNER_WATTS,
)


@dataclass(frozen=True)
class Estimates:
    """
    Estimations d'un mois, ordres de grandeur.

    Attributes
    ----------
    actions_usd : float
        Prix des minutes Actions sur un runner payant de même taille.
    energy_kwh : float
        Énergie des minutes Actions.
    co2e_kg : float
        Émissions associées à cette énergie.
    """

    actions_usd: float
    energy_kwh: float
    co2e_kg: float


def estimate(billed_minutes: int) -> Estimates:
    """
    Calcule les estimations d'un mois.

    Parameters
    ----------
    billed_minutes : int
        Minutes de runner facturables.

    Returns
    -------
    Estimates
        Équivalent payant, énergie et émissions.

    Examples
    --------
    >>> estimate(billed_minutes=60).actions_usd
    0.72
    """
    energy = RUNNER_WATTS * billed_minutes / 60 / 1000
    return Estimates(
        actions_usd=billed_minutes * ACTIONS_USD_PER_MIN,
        energy_kwh=energy,
        co2e_kg=energy * GRID_KG_CO2E_PER_KWH,
    )
