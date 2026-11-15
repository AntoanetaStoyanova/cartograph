"""
Exécutions du workflow de collecte, lues par ``gh api``.

GitHub facture chaque job à la minute entière supérieure : les minutes
facturables sont la somme, par job, de sa durée arrondie au-dessus.
"""

import calendar
import json
import math
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from cartograph.config import COLLECT_WORKFLOW, DATA_REPO

Fetch = Callable[[str, str], list[dict[str, Any]]]


@dataclass(frozen=True)
class RunStats:
    """
    Exécutions d'un mois.

    Attributes
    ----------
    runs : int
        Nombre d'exécutions.
    succeeded : int
        Exécutions réussies.
    failed : int
        Exécutions qui ne sont pas réussies (échec, annulation, délai).
    billed_minutes : int
        Minutes de runner, arrondies à la minute par job.
    """

    runs: int
    succeeded: int
    failed: int
    billed_minutes: int


def gh_api(path: str, key: str) -> list[dict[str, Any]]:
    """
    Lit toutes les pages d'une liste de l'API GitHub avec ``gh``.

    Parameters
    ----------
    path : str
        Chemin de l'API, paramètres compris.
    key : str
        Clé de la liste dans chaque page (``workflow_runs``, ``jobs``).

    Returns
    -------
    list[dict[str, Any]]
        Éléments de toutes les pages.
    """
    result = subprocess.run(
        ["gh", "api", "--paginate", "--jq", f".{key}[]", path],
        capture_output=True,
        text=True,
        check=True,
    )
    return [json.loads(line) for line in result.stdout.splitlines() if line]


def _minutes(job: dict[str, Any]) -> int:
    if not job.get("started_at") or not job.get("completed_at"):
        return 0
    start = datetime.fromisoformat(job["started_at"])
    end = datetime.fromisoformat(job["completed_at"])
    return max(1, math.ceil((end - start).total_seconds() / 60))


def collect_runs(month: str, fetch: Fetch = gh_api) -> RunStats:
    """
    Compte les exécutions de la collecte d'un mois et leurs minutes.

    Parameters
    ----------
    month : str
        Mois ``AAAA-MM``.
    fetch : Fetch
        Lecture d'une liste de l'API ; ``gh_api`` par défaut, remplacée en test.

    Returns
    -------
    RunStats
        Exécutions, réussites, échecs et minutes facturables.
    """
    year, number = (int(part) for part in month.split("-"))
    last = calendar.monthrange(year, number)[1]
    runs = fetch(
        f"repos/{DATA_REPO}/actions/workflows/{COLLECT_WORKFLOW}/runs"
        f"?created={month}-01..{month}-{last:02d}&per_page=100",
        "workflow_runs",
    )
    succeeded = sum(run["conclusion"] == "success" for run in runs)
    minutes = sum(
        _minutes(job)
        for run in runs
        for job in fetch(f"repos/{DATA_REPO}/actions/runs/{run['id']}/jobs", "jobs")
    )
    return RunStats(len(runs), succeeded, len(runs) - succeeded, minutes)
