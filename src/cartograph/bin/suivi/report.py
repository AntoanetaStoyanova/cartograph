"""
Rapport Markdown du tableau de suivi d'un mois.

Le rapport donne les chiffres mesurés ; la section « Commentaire » reste à
écrire à la main (écarts, décisions, indicateurs RSE).
"""

import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from cartograph.bin.suivi.actions import RunStats
from cartograph.bin.suivi.estimates import Estimates
from cartograph.bin.suivi.quality import Coverage
from cartograph.bin.suivi.roadmap import Lot, LotState

_MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)
_PRIORITIES = ("P1", "P2", "P3", None)
_UNMEASURED = "non mesuré"
_COMMENT_TITLE = "## Commentaire\n"
_STATUS = re.compile(r"^statut: .*$", re.MULTILINE)
COMMENT_PLACEHOLDER = "<!-- Écarts de délai, décisions du mois, indicateurs RSE. -->\n"


@dataclass(frozen=True)
class Report:
    """
    Chiffres d'un mois.

    Attributes
    ----------
    month : str
        Mois ``AAAA-MM``.
    generated : date
        Jour de génération ; lots et qualité sont l'état de ce jour.
    lots : list[Lot]
        Lots de la feuille de route.
    days : list[date]
        Jours travaillés du mois.
    runs : RunStats
        Exécutions de la collecte du mois.
    tests : int | None
        Nombre de tests, ``None`` si non mesuré.
    coverage : Coverage | None
        Couverture, ``None`` si non mesurée.
    estimates : Estimates
        Équivalent payant et énergie des minutes Actions.
    """

    month: str
    generated: date
    lots: list[Lot]
    days: list[date]
    runs: RunStats
    tests: int | None
    coverage: Coverage | None
    estimates: Estimates


def _number(value: int | float, decimals: int = 0) -> str:
    text = f"{value:,.{decimals}f}"
    return text.replace(",", " ").replace(".", ",")


def _long_date(day: date) -> str:
    number = "1er" if day.day == 1 else str(day.day)
    return f"{number} {_MONTHS[day.month - 1]} {day.year}"


def _lot_rows(lots: list[Lot]) -> list[str]:
    counts = Counter((lot.state, lot.priority) for lot in lots)
    rows = []
    for state in LotState:
        cells = [counts[(state, priority)] for priority in _PRIORITIES]
        values = " | ".join(str(cell) for cell in [*cells, sum(cells)])
        rows.append(f"| {state.value.capitalize()} | {values} |")
    return rows


def _days(days: list[date]) -> str:
    if not days:
        return "0"
    numbers = ", ".join("1er" if day.day == 1 else str(day.day) for day in days)
    return f"{len(days)} ({numbers})"


def _in_progress(runs: RunStats) -> str:
    if not runs.in_progress:
        return ""
    noun = "comptée" if runs.in_progress == 1 else "comptées"
    return f" ; {runs.in_progress} en cours, non {noun}"


def render(report: Report) -> str:
    """
    Écrit le rapport Markdown d'un mois.

    Parameters
    ----------
    report : Report
        Chiffres du mois.

    Returns
    -------
    str
        Rapport avec frontmatter OKF et section « Commentaire » vide.
    """
    year, number = (int(part) for part in report.month.split("-"))
    title = f"{_MONTHS[number - 1]} {year}"
    runs, est = report.runs, report.estimates
    tests = _UNMEASURED if report.tests is None else str(report.tests)
    coverage = (
        _UNMEASURED
        if report.coverage is None
        else f"{_number(report.coverage.percent, 1)} % "
        f"({_number(report.coverage.statements)} instructions,"
        f" mesurée le {_long_date(report.coverage.measured)})"
    )
    lines = [
        "---",
        "type: reference",
        "statut: brouillon",
        f"redige_le: {report.generated.isoformat()}",
        "---",
        "",
        f"# Suivi — {title}",
        "",
        f"*Généré le {_long_date(report.generated)} par `inv suivi`. Lots et qualité :"
        " état de ce jour ; temps, collecte et coûts : mois entier.*",
        "",
        "## Avancement",
        "",
        "| Lots | P1 | P2 | P3 | Sans priorité | Total |",
        "| --- | --- | --- | --- | --- | --- |",
        *_lot_rows(report.lots),
        "",
        "## Temps et collecte",
        "",
        "| Mesure | Valeur |",
        "| --- | --- |",
        f"| Jours travaillés | {_days(report.days)} |",
        f"| Exécutions | {runs.runs} ({runs.succeeded} réussies,"
        f" {runs.failed} en échec{_in_progress(runs)}) |",
        f"| Minutes facturables | {_number(runs.billed_minutes)} |",
        "",
        "## Qualité",
        "",
        "| Mesure | Valeur |",
        "| --- | --- |",
        f"| Tests | {tests} |",
        f"| Couverture | {coverage} |",
        "",
        "## Collecte : coût et énergie (estimations)",
        "",
        "| Mesure | Valeur |",
        "| --- | --- |",
        "| Équivalent Actions payant (gratuit : dépôt public) |"
        f" {_number(est.actions_usd, 2)} $ |",
        f"| Énergie des minutes Actions | {_number(est.energy_kwh, 2)} kWh |",
        f"| Émissions | {_number(est.co2e_kg, 2)} kg CO₂e |",
        "",
        "Rien n'est payé : les minutes Actions sont gratuites pour un dépôt public ;"
        " l'équivalent payant est ce qu'elles coûteraient sur un dépôt privé."
        " Hypothèses et sources : `cartograph.config`.",
        "",
        _COMMENT_TITLE.rstrip("\n"),
        "",
        COMMENT_PLACEHOLDER,
    ]
    return "\n".join(lines)


def _keep_written_parts(old: str, new: str) -> str:
    status = _STATUS.search(old)
    if status:
        new = _STATUS.sub(status.group(0), new, count=1)
    if _COMMENT_TITLE in old:
        new = (
            new.split(_COMMENT_TITLE)[0]
            + _COMMENT_TITLE
            + old.split(_COMMENT_TITLE, 1)[1]
        )
    return new


def write_report(path: Path, text: str, force: bool) -> None:
    """
    Écrit le rapport, sans écraser un rapport existant sauf avec ``force``.

    Avec ``force``, les chiffres sont remplacés mais le statut et la section
    « Commentaire » du rapport existant sont gardés.

    Parameters
    ----------
    path : Path
        Fichier du rapport ; ses dossiers sont créés au besoin.
    text : str
        Contenu Markdown.
    force : bool
        Remplace un rapport existant.

    Raises
    ------
    FileExistsError
        Si le rapport existe et que ``force`` est faux.
    """
    if path.exists() and not force:
        raise FileExistsError(f"{path} existe déjà : relancer avec --force")
    if path.exists():
        text = _keep_written_parts(path.read_text(encoding="utf-8"), text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
