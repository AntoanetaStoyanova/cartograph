"""
Résumé Markdown d'une collecte pour la page d'exécution GitHub.

Lit seulement ``collect-AAAA-MM-JJ.json``, qui ne contient aucun prix. Lancé
par ``python -m cartograph.bin.collect.report <résumé.json>`` ; le Markdown
part sur la sortie standard.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from cartograph.bin.collect import CollectSummary, StepSummary

MAX_FAILED = 20
_STEP_NAMES = {"catalogue": "Catalogue", "prices": "Prix"}
_STATUSES = {"ok": "✅ ok", "failed": "❌ échec"}


def render_markdown(summary: CollectSummary) -> str:
    """
    Met en forme le résumé d'une collecte.

    Parameters
    ----------
    summary : CollectSummary
        Contenu de ``collect-AAAA-MM-JJ.json``.

    Returns
    -------
    str
        Markdown : durée, tableau des étapes, détails des étapes, fichiers écrits.

    Examples
    --------
    >>> summary = {
    ...     "date": "2026-10-28",
    ...     "started_at": "2026-10-28T03:17:00+00:00",
    ...     "finished_at": "2026-10-28T04:30:00+00:00",
    ...     "steps": {},
    ... }
    >>> render_markdown(summary).splitlines()[0]
    '## Collecte du 2026-10-28'
    """
    lines = [
        f"## Collecte du {summary['date']}",
        "",
        f"Durée : {_duration(summary['started_at'], summary['finished_at'])}",
        "",
        "| Étape | Statut | Récupérées | En échec | Sans idProduct |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    steps = summary["steps"]
    for name, step in steps.items():
        label = _STEP_NAMES.get(name, name)
        if step["status"] == "skipped":
            lines.append(f"| {label} | sautée | | | |")
            continue
        lines.append(
            f"| {label} | {_STATUSES[step['status']]} | {_count(step['fetched'])}"
            f" | {_count(len(step['failed']))}"
            f" | {_count(step['skipped_without_id_product'])} |"
        )
    for name, step in steps.items():
        lines += _details(_STEP_NAMES.get(name, name), step)
    files = [file for step in steps.values() for file in step["files"]]
    if files:
        lines += ["", "### Fichiers", "", "| Fichier | Lignes | Taille |"]
        lines.append("| --- | ---: | ---: |")
        for file in files:
            rows, size = _count(file["rows"]), _megabytes(file["bytes"])
            lines.append(f"| `{file['name']}` | {rows} | {size} |")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """
    Écrit sur la sortie standard le Markdown d'un résumé de collecte.

    Parameters
    ----------
    argv : Sequence[str] | None, optional
        Arguments, par défaut ceux de la ligne de commande.

    Returns
    -------
    int
        Toujours 0.
    """
    parser = argparse.ArgumentParser(
        prog="python -m cartograph.bin.collect.report",
        description="Met en forme le résumé d'une collecte en Markdown.",
    )
    parser.add_argument("summary", type=Path, help="collect-AAAA-MM-JJ.json")
    args = parser.parse_args(argv)
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    sys.stdout.write(render_markdown(summary))
    return 0


def _details(label: str, step: StepSummary) -> list[str]:
    """Lignes de détail d'une étape : catalogue source, langues, erreur, échecs."""
    details = []
    if step.get("source"):
        details.append(f"- Catalogue utilisé : `{step['source']}`")
    if step.get("missing_languages"):
        languages = ", ".join(step["missing_languages"])
        details.append(f"- Langues absentes du catalogue : {languages}")
    if step.get("error"):
        details.append(f"- Erreur : `{step['error']}`")
    failed = step["failed"]
    if failed:
        shown = ", ".join(f"`{card}`" for card in failed[:MAX_FAILED])
        rest = len(failed) - MAX_FAILED
        more = f" … et {rest} autres" if rest > 0 else ""
        details.append(f"- Cartes en échec ({len(failed)}) : {shown}{more}")
    return ["", f"### {label}", "", *details] if details else []


def _duration(started_at: str, finished_at: str) -> str:
    """Durée entre deux horodatages ISO, au format ``1 h 13 min``."""
    elapsed = datetime.fromisoformat(finished_at) - datetime.fromisoformat(started_at)
    hours, minutes = divmod(round(elapsed.total_seconds() / 60), 60)
    return f"{hours} h {minutes:02d} min" if hours else f"{minutes} min"


def _count(value: int) -> str:
    """Entier avec séparateur de milliers français."""
    return f"{value:,}".replace(",", " ")


def _megabytes(size: int) -> str:
    """Taille en mégaoctets, une décimale, virgule française."""
    return f"{size / 1_000_000:.1f} Mo".replace(".", ",")


if __name__ == "__main__":
    sys.exit(main())
