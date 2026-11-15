"""Nombre de tests et couverture du code."""

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from cartograph.config import PROJECT_ROOT

_COLLECTED = re.compile(r"^(\d+) tests? collected", re.MULTILINE)


@dataclass(frozen=True)
class Coverage:
    """
    Couverture du code par les tests.

    Attributes
    ----------
    percent : float
        Part des instructions couvertes, arrondie à deux décimales.
    statements : int
        Nombre d'instructions mesurées.
    measured : date
        Jour du dernier passage des tests (date du fichier ``.coverage``).
    """

    percent: float
    statements: int
    measured: date


def read_coverage(path: Path, data: Path) -> Coverage | None:
    """
    Lit la couverture dans un rapport ``coverage json``.

    Parameters
    ----------
    path : Path
        Fichier ``coverage.json``.
    data : Path
        Fichier ``.coverage`` dont il est tiré ; sa date est celle de la mesure.

    Returns
    -------
    Coverage | None
        Couverture, ou ``None`` si l'un des deux fichiers manque.
    """
    if not path.exists() or not data.exists():
        return None
    totals = json.loads(path.read_text(encoding="utf-8"))["totals"]
    return Coverage(
        round(totals["percent_covered"], 2),
        totals["num_statements"],
        date.fromtimestamp(data.stat().st_mtime),
    )


def count_tests() -> int | None:
    """
    Compte les tests collectés par pytest, doctests compris.

    Returns
    -------
    int | None
        Nombre de tests, ou ``None`` si pytest ne donne pas de total.
    """
    result = subprocess.run(
        ["uv", "run", "pytest", "--collect-only", "-q", "--no-cov"],
        capture_output=True,
        text=True,
        check=False,
        cwd=PROJECT_ROOT,
    )
    match = _COLLECTED.search(result.stdout)
    return int(match[1]) if match else None
