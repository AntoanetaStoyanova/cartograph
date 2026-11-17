"""
Jours travaillés, lus dans ``.ai-context/JOURNAL.md`` et ``.ai-context/LOG.md``.

Chaque jour de travail ouvre une entrée ``## [AAAA-MM-JJ] — titre`` ; un même
jour peut avoir plusieurs entrées.
"""

import re
from collections.abc import Sequence
from datetime import date
from pathlib import Path

_ENTRY = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]", re.MULTILINE)
_MONTH = re.compile(r"^\d{4}-\d{2}$")


def worked_days(paths: Sequence[Path], month: str | None = None) -> list[date]:
    """
    Renvoie les jours qui ont une entrée dans le journal ou le log.

    Parameters
    ----------
    paths : Sequence[Path]
        Fichiers du journal et du log ; un fichier absent est ignoré.
    month : str | None
        Mois ``AAAA-MM`` ; ``None`` pour tous les jours.

    Returns
    -------
    list[date]
        Jours triés, sans doublon.

    Raises
    ------
    ValueError
        Si ``month`` n'est pas au format ``AAAA-MM``.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     path = Path(tmp) / "JOURNAL.md"
    ...     _ = path.write_text("## [2026-10-27] — Début\\n", encoding="utf-8")
    ...     worked_days([path, Path(tmp) / "LOG.md"], "2026-10")
    [datetime.date(2026, 10, 27)]
    """
    if month is not None and not _MONTH.match(month):
        raise ValueError(f"Mois attendu au format AAAA-MM : {month!r}")
    days = {
        date.fromisoformat(day)
        for path in paths
        if path.exists()
        for day in _ENTRY.findall(path.read_text(encoding="utf-8"))
        if month is None or day.startswith(f"{month}-")
    }
    return sorted(days)
