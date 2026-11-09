"""
Orchestration d'une collecte : catalogue, puis prix, avec un résumé après chacun.

Ce module enchaîne les étapes, choisit le catalogue source des prix, décide
de l'échec d'une étape et sert le CLI ; la récupération, la sélection des prix
et la mise en forme des tables sont dans ``catalogue``, ``prices`` et
``snapshot``.

Le catalogue est tout ou rien : si une langue échoue, aucun
``cards-*.parquet`` n'est écrit. Les prix utilisent le catalogue du jour s'il
vient d'être écrit, en lisant ses fiches sans nouvel appel à l'API ; sinon,
ceux du plus récent du dossier, interrogés carte par carte.

Lancé par ``inv collect`` ou ``python -m cartograph.bin.collect.run`` ; code de
sortie 0 si chaque étape demandée est ``ok``, 1 sinon.
"""

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa

from cartograph.bin.collect import (
    CollectSummary,
    FetchResult,
    FileSummary,
    StepSummary,
    skipped_step,
)
from cartograph.bin.collect.catalogue import fetch_catalogue
from cartograph.bin.collect.client import TcgdexClient, TcgdexError
from cartograph.bin.collect.prices import (
    PriceTarget,
    fetch_prices,
    price_targets_from_catalogue,
    prices_from_cards,
)
from cartograph.bin.collect.snapshot import (
    SORT_BY,
    SnapshotPaths,
    catalogue_table,
    latest_catalogue,
    price_table,
    snapshot_paths,
    write_json,
    write_json_gz,
    write_parquet,
)
from cartograph.config import DATA_DIR, LANGUAGES, LOG_DIR
from cartograph.log import setup_logging

logger = logging.getLogger(__name__)


def collect(
    client: TcgdexClient,
    data_dir: Path,
    catalogue: bool,
    prices: bool,
    languages: Sequence[str],
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> CollectSummary:
    """
    Collecte le catalogue et les prix, écrit les snapshots et le résumé.

    Parameters
    ----------
    client : TcgdexClient
        Client de l'API.
    data_dir : Path
        Dossier racine des sorties (voir ``snapshot_paths``).
    catalogue : bool
        Collecter le catalogue.
    prices : bool
        Collecter les prix.
    languages : Sequence[str]
        Langues collectées.
    now : Callable[[], datetime], optional
        Horloge, par défaut l'heure UTC courante ; injectée en test. Le jour
        des fichiers est la date UTC du début.

    Returns
    -------
    CollectSummary
        Résumé écrit dans ``runs/collect-AAAA-MM-JJ.json``.

    Notes
    -----
    Quand le catalogue et les prix sont demandés, le résumé est écrit une
    première fois après le catalogue, avec les prix à ``failed``, puis
    remplacé à la fin : une collecte coupée pendant les prix laisse un
    catalogue publiable. Si le catalogue du jour est ``ok``, les prix sont
    tirés de ses fiches sans nouvel appel à l'API ; sinon ils sont demandés
    pour les produits du dernier catalogue du dossier.
    """
    started_at = now().astimezone(UTC)
    day = started_at.date()
    paths = snapshot_paths(data_dir, day)
    catalogue_report = skipped_step()
    cards: dict[str, list[dict[str, Any]]] = {}
    catalogue_at = now()
    if catalogue:
        catalogue_report = _collect_catalogue(
            client, paths, languages, catalogue_at, cards
        )
    prices_report = skipped_step()
    if prices:
        if catalogue:
            _write_summary(
                paths, started_at, now, catalogue_report, _interrupted_step()
            )
        if catalogue_report["status"] == "ok":
            prices_report = _collect_prices(
                paths,
                paths.cards,
                languages,
                lambda targets: prices_from_cards(cards, targets, catalogue_at),
                "tirés du catalogue du jour",
            )
        else:
            prices_report = _collect_prices(
                paths,
                latest_catalogue(paths.cards.parent),
                languages,
                lambda targets: fetch_prices(client, targets, now=now),
                "à interroger",
            )
    return _write_summary(paths, started_at, now, catalogue_report, prices_report)


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

    setup_logging("cartograph", log_dir=LOG_DIR)
    with TcgdexClient() as client:
        summary = collect(
            client,
            args.data_dir,
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


def _interrupted_step() -> StepSummary:
    """
    Bilan provisoire d'une étape lancée mais pas terminée.

    Returns
    -------
    StepSummary
        Statut ``failed``, erreur « étape interrompue avant la fin ».
    """
    report = skipped_step()
    report["status"] = "failed"
    report["error"] = "étape interrompue avant la fin"
    return report


def _write_summary(
    paths: SnapshotPaths,
    started_at: datetime,
    now: Callable[[], datetime],
    catalogue_report: StepSummary,
    prices_report: StepSummary,
) -> CollectSummary:
    """
    Écrit le résumé de la collecte dans son état courant.

    Parameters
    ----------
    paths : SnapshotPaths
        Fichiers du jour.
    started_at : datetime
        Début de la collecte, en UTC.
    now : Callable[[], datetime]
        Horloge, pour ``finished_at``.
    catalogue_report, prices_report : StepSummary
        Bilans des deux étapes.

    Returns
    -------
    CollectSummary
        Résumé écrit, de façon atomique, dans ``paths.summary``.
    """
    summary: CollectSummary = {
        "date": started_at.date().isoformat(),
        "started_at": started_at.isoformat(),
        "finished_at": now().astimezone(UTC).isoformat(),
        "steps": {"catalogue": catalogue_report, "prices": prices_report},
    }
    write_json(summary, paths.summary)
    return summary


def _collect_catalogue(
    client: TcgdexClient,
    paths: SnapshotPaths,
    languages: Sequence[str],
    fetched_at: datetime,
    cards: dict[str, list[dict[str, Any]]],
) -> StepSummary:
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
    fetched_at : datetime
        Début de l'étape, écrit dans la table.
    cards : dict[str, list[dict[str, Any]]]
        Rempli avec les fiches par langue, pour en tirer les prix.

    Returns
    -------
    StepSummary
        ``failed`` si une langue échoue (rien n'est alors écrit) ou si la
        conversion en table échoue (le brut est alors conservé).
    """
    report = skipped_step()
    try:
        for language in languages:
            result = fetch_catalogue(client, language)
            cards[language] = result.items
            report["fetched"] += len(result.items)
            report["failed"] += result.failed
    except TcgdexError as error:
        report["status"] = "failed"
        report["error"] = str(error)
        return report
    report["files"].append(
        _file(paths.raw_cards, report["fetched"], write_json_gz(cards, paths.raw_cards))
    )
    _write_table(report, paths.cards, lambda: catalogue_table(cards, fetched_at))
    return report


def _collect_prices(
    paths: SnapshotPaths,
    source: Path | None,
    languages: Sequence[str],
    fetch: Callable[[Sequence[PriceTarget]], FetchResult],
    origin: str,
) -> StepSummary:
    """
    Récupère les prix des produits du catalogue ``source`` et les écrit.

    Parameters
    ----------
    paths : SnapshotPaths
        Fichiers du jour.
    source : Path | None
        Snapshot du catalogue ; ``None`` fait échouer l'étape.
    languages : Sequence[str]
        Langues dont les cartes sont retenues.
    fetch : Callable[[Sequence[PriceTarget]], FetchResult]
        Récupère les prix des cibles : ``fetch_prices`` ou
        ``prices_from_cards``.
    origin : str
        Provenance des prix, pour le log.

    Returns
    -------
    StepSummary
        ``failed`` sans catalogue, si aucune langue demandée n'y figure, si la
        collecte s'arrête ou si la conversion en table échoue (le brut est
        alors conservé).
    """
    report = skipped_step()
    if source is None:
        report["status"] = "failed"
        report["error"] = "aucun catalogue disponible"
        return report
    report["source"] = source.name
    selection = price_targets_from_catalogue(source, languages)
    missing = selection.missing_languages
    report["missing_languages"] = missing
    if missing:
        logger.warning(
            "prix : langues absentes du catalogue %s : %s",
            source.name,
            ", ".join(missing),
        )
    if len(missing) == len(languages):
        report["status"] = "failed"
        report["error"] = "aucune langue demandée dans le catalogue"
        return report
    targets = selection.targets
    report["skipped_without_id_product"] = selection.skipped_without_id_product
    logger.info(
        "prix : %d produits %s, %d cartes ignorées sans idProduct",
        len(targets),
        origin,
        report["skipped_without_id_product"],
    )
    try:
        result = fetch(targets)
    except TcgdexError as error:
        report["status"] = "failed"
        report["error"] = str(error)
        return report
    report["fetched"] = len(result.items)
    report["failed"] = result.failed
    report["files"].append(
        _file(
            paths.raw_prices,
            report["fetched"],
            write_json_gz(result.items, paths.raw_prices),
        )
    )
    _write_table(report, paths.prices, lambda: price_table(result.items))
    return report


def _write_table(
    report: StepSummary, path: Path, build: Callable[[], pa.Table]
) -> None:
    """
    Construit la table d'une étape et l'écrit, le brut étant déjà sauvegardé.

    Une réponse de l'API de forme inattendue fait échouer l'étape sans perdre
    la collecte. Seul le type de l'erreur est noté : son message peut contenir
    une valeur de prix (T8).

    Parameters
    ----------
    report : StepSummary
        Bilan de l'étape, complété (``status``, ``files``, ``error``).
    path : Path
        Snapshot Parquet à écrire.
    build : Callable[[], pa.Table]
        Construit la table depuis le brut.
    """
    try:
        table = build()
    except Exception as error:
        report["status"] = "failed"
        report["error"] = f"conversion en table impossible ({type(error).__name__})"
        logger.error("%s : %s, brut conservé", path.name, report["error"])
        return
    report["files"].insert(
        0, _file(path, table.num_rows, write_parquet(table, path, SORT_BY))
    )
    report["status"] = "ok"


def _file(path: Path, rows: int, size: int) -> FileSummary:
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
    FileSummary
        ``{"name", "rows", "bytes"}``.
    """
    return {"name": path.name, "rows": rows, "bytes": size}


if __name__ == "__main__":
    sys.exit(main())
