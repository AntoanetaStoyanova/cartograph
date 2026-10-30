"""
Écriture des snapshots datés de la collecte.

Chaque fichier est écrit dans un fichier temporaire du même dossier puis
renommé : relancer la collecte le même jour remplace les fichiers du jour sans
jamais laisser de fichier à moitié écrit.
"""

import gzip
import json
import logging
import os
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, BinaryIO

import pyarrow as pa
import pyarrow.parquet as pq

from cartograph.config import SNAPSHOT_COMPRESSION

logger = logging.getLogger(__name__)

_CM_STATS = ("avg", "low", "trend", "avg1", "avg7", "avg30")
_CM_PRICE_FIELDS = {
    **{stat: f"cm_{stat}" for stat in _CM_STATS},
    **{f"{stat}-holo": f"cm_{stat}_holo" for stat in _CM_STATS},
}
_CM_KNOWN_FIELDS = {"updated", "unit", "idProduct", *_CM_PRICE_FIELDS}
_UTC_TIMESTAMP = pa.timestamp("us", tz="UTC")
PRICE_SCHEMA = pa.schema(
    [
        ("language", pa.string()),
        ("card_id", pa.string()),
        ("id_product", pa.int64()),
        ("fetched_at", _UTC_TIMESTAMP),
        ("cm_updated", _UTC_TIMESTAMP),
        ("cm_unit", pa.string()),
        *[(column, pa.float64()) for column in _CM_PRICE_FIELDS.values()],
        ("tcgplayer_json", pa.string()),
    ]
)
"""
Schéma des snapshots de prix : une ligne par produit Cardmarket.

``fetched_at`` est l'heure de la requête de chaque produit : la collecte des
prix dure plus d'une heure.
"""

CARD_SCHEMA = pa.schema(
    [
        ("language", pa.string()),
        ("card_id", pa.string()),
        ("local_id", pa.string()),
        ("name", pa.string()),
        ("set_id", pa.string()),
        ("set_name", pa.string()),
        ("rarity", pa.string()),
        ("category", pa.string()),
        ("illustrator", pa.string()),
        ("image", pa.string()),
        ("id_product", pa.int64()),
        ("updated", _UTC_TIMESTAMP),
        ("fetched_at", _UTC_TIMESTAMP),
        ("raw_json", pa.string()),
    ]
)
"""
Schéma des snapshots du catalogue : une ligne par carte et par langue, sans prix.

``fetched_at`` est l'heure du début de l'étape, la même pour toutes les cartes :
le catalogue est un instantané, publié en entier ou pas du tout.
"""


@dataclass(frozen=True)
class SnapshotPaths:
    """
    Fichiers de sortie d'une collecte.

    Attributes
    ----------
    cards : Path
        Catalogue sans prix (Parquet).
    prices : Path
        Prix Cardmarket et TCGplayer (Parquet).
    raw_cards : Path
        Réponses brutes du catalogue, prix compris (JSON gzip).
    raw_prices : Path
        Réponses brutes des prix (JSON gzip).
    summary : Path
        Résumé d'exécution, sans prix (JSON).
    """

    cards: Path
    prices: Path
    raw_cards: Path
    raw_prices: Path
    summary: Path


def snapshot_paths(data_dir: Path, day: date) -> SnapshotPaths:
    """
    Renvoie les chemins des fichiers d'une collecte.

    Parameters
    ----------
    data_dir : Path
        Dossier racine des sorties.
    day : date
        Date UTC du début de la collecte.

    Returns
    -------
    SnapshotPaths
        Chemins sous ``snapshots/``, ``raw/`` et ``runs/``.

    Examples
    --------
    >>> snapshot_paths(Path("data"), date(2026, 10, 28)).prices.as_posix()
    'data/snapshots/prices-2026-10-28.parquet'
    """
    stamp = day.isoformat()
    return SnapshotPaths(
        cards=data_dir / "snapshots" / f"cards-{stamp}.parquet",
        prices=data_dir / "snapshots" / f"prices-{stamp}.parquet",
        raw_cards=data_dir / "raw" / f"cards-{stamp}.json.gz",
        raw_prices=data_dir / "raw" / f"prices-{stamp}.json.gz",
        summary=data_dir / "runs" / f"collect-{stamp}.json",
    )


def price_table(records: Sequence[dict[str, Any]]) -> pa.Table:
    """
    Convertit les enregistrements de ``fetch_prices`` en table typée.

    Les champs Cardmarket absents valent nul ; les champs inconnus sont ignorés
    et leurs noms, jamais leurs valeurs, journalisés une fois.

    Parameters
    ----------
    records : Sequence[dict[str, Any]]
        Enregistrements ``{"language", "card_id", "id_product", "fetched_at",
        "pricing"}``.

    Returns
    -------
    pa.Table
        Table au schéma ``PRICE_SCHEMA``.
    """
    unknown: set[str] = set()
    rows = []
    for record in records:
        pricing = record["pricing"] or {}
        cardmarket = pricing.get("cardmarket") or {}
        tcgplayer = pricing.get("tcgplayer")
        unknown.update(cardmarket.keys() - _CM_KNOWN_FIELDS)
        rows.append(
            {
                "language": record["language"],
                "card_id": record["card_id"],
                "id_product": record["id_product"],
                "fetched_at": _utc(record["fetched_at"]),
                "cm_updated": _utc(cardmarket.get("updated")),
                "cm_unit": cardmarket.get("unit"),
                **{
                    column: _float(cardmarket.get(field))
                    for field, column in _CM_PRICE_FIELDS.items()
                },
                "tcgplayer_json": None
                if tcgplayer is None
                else json.dumps(tcgplayer, ensure_ascii=False, sort_keys=True),
            }
        )
    if unknown:
        logger.warning(
            "Champs Cardmarket inconnus ignorés : %s", ", ".join(sorted(unknown))
        )
    return pa.Table.from_pylist(rows, schema=PRICE_SCHEMA)


# garantie que le catalogue public ne contient aucun prix.
def strip_prices(card: dict[str, Any]) -> dict[str, Any]:
    """
    Copie une fiche sans aucune clé ``pricing``, à toute profondeur.

    Parameters
    ----------
    card : dict[str, Any]
        Fiche complète de l'API, non modifiée.

    Returns
    -------
    dict[str, Any]
        Copie sans ``pricing`` ni ``variants_detailed[].pricing``.

    Examples
    --------
    >>> strip_prices({"id": "a", "pricing": {}, "variants": [{"pricing": {}}]})
    {'id': 'a', 'variants': [{}]}
    """
    stripped: dict[str, Any] = _without_pricing(card)
    return stripped


def card_table(
    cards: Sequence[dict[str, Any]], language: str, fetched_at: datetime
) -> pa.Table:
    """
    Convertit les fiches d'une langue en table du catalogue, sans prix.

    Parameters
    ----------
    cards : Sequence[dict[str, Any]]
        Fiches complètes de ``fetch_catalogue``.
    language : str
        Langue des fiches.
    fetched_at : datetime
        Début de l'étape du catalogue, converti en UTC (voir ``CARD_SCHEMA``).

    Returns
    -------
    pa.Table
        Table au schéma ``CARD_SCHEMA`` ; ``id_product`` est lu avant le
        retrait des prix, ``raw_json`` est la fiche sans prix.
    """
    fetched_at_utc = fetched_at.astimezone(UTC)
    rows = [
        {
            "language": language,
            "card_id": card["id"],
            "local_id": card.get("localId"),
            "name": card.get("name"),
            "set_id": (card.get("set") or {}).get("id"),
            "set_name": (card.get("set") or {}).get("name"),
            "rarity": card.get("rarity"),
            "category": card.get("category"),
            "illustrator": card.get("illustrator"),
            "image": card.get("image"),
            "id_product": _card_id_product(card),
            "updated": _utc(card.get("updated")),
            "fetched_at": fetched_at_utc,
            "raw_json": json.dumps(
                strip_prices(card), ensure_ascii=False, sort_keys=True
            ),
        }
        for card in cards
    ]
    return pa.Table.from_pylist(rows, schema=CARD_SCHEMA)


def write_parquet(table: pa.Table, path: Path, sort_by: Sequence[str]) -> int:
    """
    Écrit une table triée en Parquet compressé, de façon atomique.

    Parameters
    ----------
    table : pa.Table
        Table à écrire.
    path : Path
        Fichier de destination, remplacé s'il existe.
    sort_by : Sequence[str]
        Colonnes de tri, par ordre de priorité, croissant.

    Returns
    -------
    int
        Taille du fichier écrit, en octets.
    """
    sorted_table = table.sort_by([(column, "ascending") for column in sort_by])

    def write(file: BinaryIO) -> None:
        pq.write_table(sorted_table, file, compression=SNAPSHOT_COMPRESSION)

    return _write_atomic(path, write)


def write_json(obj: Any, path: Path) -> int:
    """
    Écrit un objet en JSON indenté, de façon atomique.

    Parameters
    ----------
    obj : Any
        Objet sérialisable en JSON.
    path : Path
        Fichier de destination, remplacé s'il existe.

    Returns
    -------
    int
        Taille du fichier écrit, en octets.
    """
    data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")

    def write(file: BinaryIO) -> None:
        file.write(data)

    return _write_atomic(path, write)


def write_json_gz(obj: Any, path: Path) -> int:
    """
    Écrit un objet en JSON compressé gzip, de façon atomique.

    Parameters
    ----------
    obj : Any
        Objet sérialisable en JSON.
    path : Path
        Fichier de destination, remplacé s'il existe.

    Returns
    -------
    int
        Taille du fichier écrit, en octets.
    """
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")

    def write(file: BinaryIO) -> None:
        with gzip.GzipFile(fileobj=file, mode="wb", mtime=0) as archive:
            archive.write(data)

    return _write_atomic(path, write)


# l'écriture est atomique : un fichier temporaire est écrit puis renommé avec
# os.replace ; une relance le même jour remplace les fichiers du jour.
def _write_atomic(path: Path, write: Callable[[BinaryIO], None]) -> int:
    """
    Écrit dans un fichier temporaire du même dossier puis le renomme.

    Parameters
    ----------
    path : Path
        Fichier de destination.
    write : Callable[[BinaryIO], None]
        Écrit le contenu dans le fichier ouvert.

    Returns
    -------
    int
        Taille du fichier écrit, en octets.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as file:
            write(file)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return path.stat().st_size


def _card_id_product(card: dict[str, Any]) -> int | None:
    """
    Renvoie le produit Cardmarket d'une fiche.

    Parameters
    ----------
    card : dict[str, Any]
        Fiche complète de l'API.

    Returns
    -------
    int | None
        ``pricing.cardmarket.idProduct``, ``None`` si absent.
    """
    cardmarket = (card.get("pricing") or {}).get("cardmarket") or {}
    id_product: int | None = cardmarket.get("idProduct")
    return id_product


def _utc(value: str | None) -> datetime | None:
    """
    Convertit une date ISO 8601 de l'API en ``datetime`` UTC.

    Parameters
    ----------
    value : str | None
        Date ISO 8601 (``Z`` accepté), ou nul.

    Returns
    -------
    datetime | None
        Date avec fuseau UTC, ou nul.
    """
    if value is None:
        return None
    return datetime.fromisoformat(value).astimezone(UTC)


def _float(value: int | float | None) -> float | None:
    """
    Convertit un prix en ``float``, les entiers JSON compris.

    Parameters
    ----------
    value : int | float | None
        Prix lu dans l'API, ou nul.

    Returns
    -------
    float | None
        Prix en ``float``, ou nul.
    """
    return None if value is None else float(value)


def _without_pricing(node: Any) -> Any:
    """
    Copie récursive d'un nœud JSON sans les clés ``pricing``.

    Parameters
    ----------
    node : Any
        Nœud JSON : dictionnaire, liste ou valeur.

    Returns
    -------
    Any
        Copie du nœud sans ``pricing``.
    """
    if isinstance(node, dict):
        return {
            key: _without_pricing(value)
            for key, value in node.items()
            if key != "pricing"
        }
    if isinstance(node, list):
        return [_without_pricing(item) for item in node]
    return node
