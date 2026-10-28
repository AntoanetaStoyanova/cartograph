"""
Enchaînement d'une collecte : catalogue, puis prix, puis résumé.

Le catalogue est tout ou rien : si une langue échoue, aucun
``cards-*.parquet`` n'est écrit. Les prix utilisent le catalogue du jour s'il
vient d'être écrit, sinon le plus récent du dossier.

Lancé par ``inv collect`` ou ``python -m cartograph.bin.collect.run`` ; code de
sortie 0 si chaque étape demandée est ``ok``, 1 sinon.
"""

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from cartograph.bin.collect.catalogue import fetch_catalogue
from cartograph.bin.collect.client import TcgdexClient, TcgdexError
from cartograph.bin.collect.prices import fetch_prices, price_targets_from_table
from cartograph.bin.collect.snapshot import (
    SnapshotPaths,
    card_table,
    price_table,
    snapshot_paths,
    write_json,
    write_json_gz,
    write_parquet,
)
from cartograph.config import DATA_DIR, LANGUAGES, LOG_DIR
from cartograph.log import setup_logging

logger = logging.getLogger(__name__)

SORT_BY = ("card_id", "language")
_TARGET_COLUMNS = ["language", "card_id", "id_product"]


@dataclass
class StepReport:
    """
    Bilan d'une étape de la collecte, sans aucun prix.

    Attributes
    ----------
    status : {"ok", "failed", "skipped"}
        ``skipped`` si l'étape n'a pas été demandée.
    fetched : int
        Fiches ou prix récupérés.
    failed : list[str]
        Cartes en échec, au format ``langue/identifiant``.
    skipped_without_id_product : int
        Cartes ignorées faute de produit Cardmarket (étape prix).
    files : list[dict[str, Any]]
        Fichiers écrits : ``name``, ``rows``, ``bytes``.
    source : str | None
        Catalogue utilisé pour les prix.
    missing_languages : list[str]
        Langues demandées absentes du catalogue utilisé pour les prix.
    error : str | None
        Cause de l'échec de l'étape.
    """

    status: Literal["ok", "failed", "skipped"] = "skipped"
    fetched: int = 0
    failed: list[str] = field(default_factory=list)
    skipped_without_id_product: int = 0
    files: list[dict[str, Any]] = field(default_factory=list)
    source: str | None = None
    missing_languages: list[str] = field(default_factory=list)
    error: str | None = None


def latest_catalogue(snapshots_dir: Path) -> Path | None:
    """
    Renvoie le snapshot du catalogue le plus récent.

    Parameters
    ----------
    snapshots_dir : Path
        Dossier des snapshots.

    Returns
    -------
    Path | None
        Dernier ``cards-AAAA-MM-JJ.parquet``, ``None`` s'il n'y en a aucun.
    """
    return max(snapshots_dir.glob("cards-*.parquet"), default=None)


def collect(
    client: TcgdexClient,
    data_dir: Path,
    day: date,
    catalogue: bool,
    prices: bool,
    languages: Sequence[str],
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    """
    Collecte le catalogue et les prix, écrit les snapshots et le résumé.

    Parameters
    ----------
    client : TcgdexClient
        Client de l'API.
    data_dir : Path
        Dossier racine des sorties (voir ``snapshot_paths``).
    day : date
        Date UTC du snapshot.
    catalogue : bool
        Collecter le catalogue.
    prices : bool
        Collecter les prix.
    languages : Sequence[str]
        Langues collectées.
    now : Callable[[], datetime], optional
        Horloge, par défaut l'heure UTC courante ; injectée en test.

    Returns
    -------
    dict[str, Any]
        Résumé écrit dans ``runs/collect-AAAA-MM-JJ.json`` : date, début, fin
        et bilan de chaque étape (voir ``StepReport``).
    """
    paths = snapshot_paths(data_dir, day)
    started_at = now().astimezone(UTC)
    catalogue_report = (
        _collect_catalogue(client, paths, languages, now) if catalogue else StepReport()
    )
    prices_report = StepReport()
    if prices:
        source = (
            paths.cards
            if catalogue_report.status == "ok"
            else latest_catalogue(paths.cards.parent)
        )
        prices_report = _collect_prices(client, paths, source, languages, now)
    summary = {
        "date": day.isoformat(),
        "started_at": started_at.isoformat(),
        "finished_at": now().astimezone(UTC).isoformat(),
        "steps": {
            "catalogue": asdict(catalogue_report),
            "prices": asdict(prices_report),
        },
    }
    write_json(summary, paths.summary)
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    """
    Lance une collecte depuis la ligne de commande.

    Parameters
    ----------
    argv : Sequence[str] | None, optional
        Arguments, par défaut ceux de la ligne de commande.

    Returns
    -------
    int
        0 si chaque étape demandée est ``ok``, 1 sinon.
    """
    parser = argparse.ArgumentParser(
        prog="python -m cartograph.bin.collect.run",
        description="Collecte le catalogue et les prix TCGdex du jour.",
    )
    parser.add_argument(
        "--catalogue", action="store_true", help="collecter aussi le catalogue"
    )
    parser.add_argument(
        "--no-prices", action="store_true", help="ne pas collecter les prix"
    )
    parser.add_argument(
        "--languages",
        type=_languages,
        default=LANGUAGES,
        help=f"langues séparées par des virgules (défaut : {','.join(LANGUAGES)})",
    )
    parser.add_argument(
        "--data-dir", type=Path, default=DATA_DIR, help="dossier des sorties"
    )
    args = parser.parse_args(argv)
    if not args.catalogue and args.no_prices:
        parser.error("rien à collecter : --no-prices sans --catalogue")

    logger = setup_logging("cartograph", log_dir=LOG_DIR)
    with TcgdexClient() as client:
        summary = collect(
            client,
            args.data_dir,
            datetime.now(UTC).date(),
            catalogue=args.catalogue,
            prices=not args.no_prices,
            languages=args.languages,
        )
    statuses = {name: step["status"] for name, step in summary["steps"].items()}
    logger.info("Collecte terminée : %s", statuses)
    return 0 if "failed" not in statuses.values() else 1


def _languages(value: str) -> tuple[str, ...]:
    """
    Lit l'option ``--languages``.

    Parameters
    ----------
    value : str
        Langues séparées par des virgules.

    Returns
    -------
    tuple[str, ...]
        Langues demandées.

    Raises
    ------
    argparse.ArgumentTypeError
        Si une langue est hors ``LANGUAGES``.
    """
    languages = tuple(part.strip() for part in value.split(",") if part.strip())
    unknown = [language for language in languages if language not in LANGUAGES]
    if not languages or unknown:
        raise argparse.ArgumentTypeError(
            f"langues inconnues : {value!r} (attendu parmi {','.join(LANGUAGES)})"
        )
    return languages


def _collect_catalogue(
    client: TcgdexClient,
    paths: SnapshotPaths,
    languages: Sequence[str],
    now: Callable[[], datetime],
) -> StepReport:
    """
    Collecte toutes les langues puis écrit le catalogue et son brut.

    Parameters
    ----------
    client : TcgdexClient
        Client de l'API.
    paths : SnapshotPaths
        Fichiers du jour.
    languages : Sequence[str]
        Langues collectées.
    now : Callable[[], datetime]
        Horloge.

    Returns
    -------
    StepReport
        ``failed`` si une langue échoue (rien n'est alors écrit) ou si la
        conversion en table échoue (le brut est alors conservé).
    """
    report = StepReport()
    fetched_at = now()
    cards: dict[str, list[dict[str, Any]]] = {}
    try:
        for language in languages:
            result = fetch_catalogue(client, language)
            cards[language] = result.items
            report.fetched += len(result.items)
            report.failed += [f"{language}/{card_id}" for card_id in result.failed]
    except TcgdexError as error:
        report.status = "failed"
        report.error = str(error)
        return report
    report.files.append(
        _file(paths.raw_cards, report.fetched, write_json_gz(cards, paths.raw_cards))
    )
    _write_table(
        report,
        paths.cards,
        lambda: pa.concat_tables(
            [
                card_table(items, language, fetched_at)
                for language, items in cards.items()
            ]
        ),
    )
    return report


def _collect_prices(
    client: TcgdexClient,
    paths: SnapshotPaths,
    source: Path | None,
    languages: Sequence[str],
    now: Callable[[], datetime],
) -> StepReport:
    """
    Collecte les prix des produits du catalogue ``source`` et les écrit.

    Parameters
    ----------
    client : TcgdexClient
        Client de l'API.
    paths : SnapshotPaths
        Fichiers du jour.
    source : Path | None
        Snapshot du catalogue ; ``None`` fait échouer l'étape.
    languages : Sequence[str]
        Langues dont les cartes sont interrogées.
    now : Callable[[], datetime]
        Horloge.

    Returns
    -------
    StepReport
        ``failed`` sans catalogue, si aucune langue demandée n'y figure, si la
        collecte s'arrête ou si la conversion en table échoue (le brut est
        alors conservé).
    """
    report = StepReport()
    if source is None:
        report.status = "failed"
        report.error = "aucun catalogue disponible"
        return report
    report.source = source.name
    table = pq.read_table(source, columns=_TARGET_COLUMNS)
    available = set(table.column("language").unique().to_pylist())
    report.missing_languages = [lang for lang in languages if lang not in available]
    if report.missing_languages:
        logger.warning(
            "prix : langues absentes du catalogue %s : %s",
            source.name,
            ", ".join(report.missing_languages),
        )
    if len(report.missing_languages) == len(languages):
        report.status = "failed"
        report.error = "aucune langue demandée dans le catalogue"
        return report
    table = table.filter(pc.is_in(table.column("language"), pa.array(languages)))
    report.skipped_without_id_product = table.column("id_product").null_count
    targets = price_targets_from_table(table)
    try:
        result = fetch_prices(client, targets, now=now)
    except TcgdexError as error:
        report.status = "failed"
        report.error = str(error)
        return report
    report.fetched = len(result.items)
    report.failed = result.failed
    report.files.append(
        _file(
            paths.raw_prices,
            report.fetched,
            write_json_gz(result.items, paths.raw_prices),
        )
    )
    _write_table(report, paths.prices, lambda: price_table(result.items))
    return report


def _write_table(report: StepReport, path: Path, build: Callable[[], pa.Table]) -> None:
    """
    Construit la table d'une étape et l'écrit, le brut étant déjà sauvegardé.

    Une réponse de l'API de forme inattendue fait échouer l'étape sans perdre
    la collecte. Seul le type de l'erreur est noté : son message peut contenir
    une valeur de prix (T8).

    Parameters
    ----------
    report : StepReport
        Bilan de l'étape, complété (``status``, ``files``, ``error``).
    path : Path
        Snapshot Parquet à écrire.
    build : Callable[[], pa.Table]
        Construit la table depuis le brut.
    """
    try:
        table = build()
    except Exception as error:
        report.status = "failed"
        report.error = f"conversion en table impossible ({type(error).__name__})"
        logger.error("%s : %s, brut conservé", path.name, report.error)
        return
    report.files.insert(
        0, _file(path, table.num_rows, write_parquet(table, path, SORT_BY))
    )
    report.status = "ok"


def _file(path: Path, rows: int, size: int) -> dict[str, Any]:
    """
    Décrit un fichier écrit pour le résumé.

    Parameters
    ----------
    path : Path
        Fichier écrit.
    rows : int
        Nombre de lignes ou d'enregistrements.
    size : int
        Taille en octets.

    Returns
    -------
    dict[str, Any]
        ``{"name", "rows", "bytes"}``.
    """
    return {"name": path.name, "rows": rows, "bytes": size}


if __name__ == "__main__":
    sys.exit(main())
