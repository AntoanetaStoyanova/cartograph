"""
Tâche ``inv suivi`` : écrit le rapport de suivi d'un mois.

``python -m cartograph.bin.suivi.run [--mois AAAA-MM] [--force]``
"""

import argparse
import logging
import re
import subprocess
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from cartograph.bin.suivi.actions import collect_runs
from cartograph.bin.suivi.estimates import estimate
from cartograph.bin.suivi.journal import worked_days
from cartograph.bin.suivi.quality import count_tests, read_coverage
from cartograph.bin.suivi.report import Report, render, write_report
from cartograph.bin.suivi.roadmap import read_lots
from cartograph.config import LOG_DIR, PROJECT_ROOT
from cartograph.log import setup_logging

logger = logging.getLogger(__name__)

ROADMAP = PROJECT_ROOT / "docs" / "plans" / "roadmap-lots.md"
JOURNAL = PROJECT_ROOT / ".ai-context" / "JOURNAL.md"
LOG = PROJECT_ROOT / ".ai-context" / "LOG.md"
COVERAGE_DATA = PROJECT_ROOT / ".coverage"
OUT_DIR = PROJECT_ROOT / "docs" / "gouvernance" / "suivi"
_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def today() -> date:
    """Renvoie la date du jour, remplacée en test."""
    return date.today()


def _month(value: str) -> str:
    if not _MONTH.match(value):
        raise argparse.ArgumentTypeError(f"mois attendu au format AAAA-MM : {value!r}")
    return value


def _coverage_json() -> Path:
    report = COVERAGE_DATA.parent / "coverage.json"
    report.unlink(missing_ok=True)
    if not COVERAGE_DATA.exists():
        logger.warning("Pas de .coverage : couverture non mesurée (lancer inv ci)")
        return report
    result = subprocess.run(
        ["uv", "run", "coverage", "json", "-q", "-o", report.name],
        cwd=COVERAGE_DATA.parent,
        check=False,
    )
    if result.returncode != 0:
        report.unlink(missing_ok=True)
        logger.warning("coverage json en échec : couverture non mesurée")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """
    Écrit ``docs/gouvernance/suivi/AAAA-MM.md``.

    Parameters
    ----------
    argv : Sequence[str] | None
        Arguments de la ligne de commande ; ``sys.argv`` par défaut.

    Returns
    -------
    int
        0 si le rapport est écrit, 1 s'il existe déjà sans ``--force``.
    """
    parser = argparse.ArgumentParser(
        prog="python -m cartograph.bin.suivi.run",
        description="Écrit le rapport de suivi mensuel.",
    )
    parser.add_argument("--mois", type=_month, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    setup_logging("cartograph", log_dir=LOG_DIR)

    generated = today()
    month = args.mois or generated.strftime("%Y-%m")
    days = worked_days([JOURNAL, LOG], month)
    runs = collect_runs(month)
    report = Report(
        month=month,
        generated=generated,
        lots=read_lots(ROADMAP),
        days=days,
        runs=runs,
        tests=count_tests(),
        coverage=read_coverage(_coverage_json(), COVERAGE_DATA),
        estimates=estimate(runs.billed_minutes),
    )
    path = OUT_DIR / f"{month}.md"
    try:
        write_report(path, render(report), args.force)
    except FileExistsError as exc:
        logger.error("%s", exc)
        return 1
    logger.info("Rapport écrit : %s", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
