"""
Lecture des lots de ``docs/plans/roadmap-lots.md``.

Une ligne de lot est une ligne de tableau dont la première cellule est l'état
(``[x]``, ``[ ]`` ou ``—``) et la deuxième un identifiant comme ``DBT-01``.
"""

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

_LOT_ID = re.compile(r"^[A-Z0-9]+-[A-Z0-9]+$")


class LotState(StrEnum):
    """État d'un lot dans la feuille de route."""

    DONE = "fait"
    OPEN = "ouvert"
    DROPPED = "supprimé"


_STATES = {"[x]": LotState.DONE, "[ ]": LotState.OPEN, "—": LotState.DROPPED}


@dataclass(frozen=True)
class Lot:
    """
    Lot de la feuille de route.

    Attributes
    ----------
    id : str
        Identifiant, par exemple ``DBT-01``.
    state : LotState
        Fait, ouvert ou supprimé.
    priority : str | None
        ``P1``, ``P2`` ou ``P3`` ; ``None`` pour ``—``.
    """

    id: str
    state: LotState
    priority: str | None


def read_lots(path: Path) -> list[Lot]:
    """
    Lit les lots de la feuille de route, dans l'ordre du fichier.

    Parameters
    ----------
    path : Path
        Fichier ``roadmap-lots.md``.

    Returns
    -------
    list[Lot]
        Un lot par ligne de tableau ; en-têtes et listes ignorés.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     path = Path(tmp) / "roadmap.md"
    ...     _ = path.write_text("| [x] | FND-01 | Socle | P1 |\\n", encoding="utf-8")
    ...     read_lots(path)
    [Lot(id='FND-01', state=<LotState.DONE: 'fait'>, priority='P1')]
    """
    lots = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] not in _STATES or not _LOT_ID.match(cells[1]):
            continue
        priority = cells[-1] if cells[-1].startswith("P") else None
        lots.append(Lot(cells[1], _STATES[cells[0]], priority))
    return lots
