"""
Orchestration d'une collecte : catalogue, sets, nouvelles cartes, puis prix,
avec un résumé après chacun.

Ce module enchaîne les étapes, choisit le catalogue source des prix, décide
de l'échec d'une étape et sert le CLI ; la récupération, la sélection des prix
et la mise en forme des tables sont dans ``catalogue``, ``sets``, ``prices`` et
``snapshot``.

La collecte complète (``--catalogue``) est tout ou rien : si une langue
échoue, aucun ``cards-*.parquet`` n'est écrit ; une fiche en échec garde sa
ligne du catalogue précédent. Les prix utilisent le catalogue du jour s'il
vient d'être écrit, en lisant ses fiches sans nouvel appel à l'API ; sinon,
ceux du plus récent du dossier, interrogés carte par carte. Les sets sont
collectés à chaque exécution, après le catalogue ; leur échec ne touche ni le
catalogue, ni les nouvelles cartes, ni les prix.
Les jours sans collecte complète, les listes de l'API donnent les cartes
nouvelles, disparues et revenues ; les nouvelles sont téléchargées
(``new_cards``) et leurs prix ajoutés à ceux du jour. Le catalogue de la veille
est ensuite mis à jour avec les fiches reçues avec les prix, les nouvelles et
une rotation des fiches les plus anciennes, puis écrit avec ses changements.

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
import pyarrow.compute as pc

from cartograph.bin.collect import (
    CollectSummary,
    FetchResult,
    FileSummary,
    StepSummary,
    skipped_step,
)
from cartograph.bin.collect.catalogue import (
    ListingDiff,
    compare_listing,
    fetch_catalogue,
    listing_diff,
)
from cartograph.bin.collect.client import TcgdexClient, TcgdexError
from cartograph.bin.collect.incremental import (
    apply_listing,
    card_changes_table,
    changed_cards,
    count_changes,
    merge_catalogue,
    rotation_ids,
)
from cartograph.bin.collect.prices import (
    PriceTarget,
    fetch_prices,
    new_card_targets,
    price_targets_from_catalogue,
    prices_from_cards,
)
from cartograph.bin.collect.sets import fetch_sets
from cartograph.bin.collect.snapshot import (
    SET_SORT_BY,
    SORT_BY,
    SnapshotPaths,
    catalogue_table,
    latest_catalogue,
    price_table,
    read_catalogue,
    set_table,
    snapshot_paths,
    write_json,
    write_json_gz,
    write_parquet,
)
from cartograph.config import DATA_DIR, LANGUAGES, LOG_DIR, ROTATION_SIZE
from cartograph.log import setup_logging

logger = logging.getLogger(__name__)


def collect(
    client: TcgdexClient,
    data_dir: Path,
    catalogue: bool,
    prices: bool,
    languages: Sequence[str],
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    rotation: int = ROTATION_SIZE,
) -> CollectSummary:
    """
    Collecte le catalogue, les sets et les prix, écrit les snapshots et le résumé.

    Parameters
    ----------
    client : TcgdexClient
        Client de l'API.
    data_dir : Path
        Dossier racine des sorties (voir ``snapshot_paths``).
    catalogue : bool
        Collecter le catalogue, avant les sets.
    prices : bool
        Collecter les prix.
    languages : Sequence[str]
        Langues collectées.
    now : Callable[[], datetime], optional
        Horloge, par défaut l'heure UTC courante ; injectée en test. Le jour
        des fichiers est la date UTC du début.
    rotation : int, optional
        Fiches hors prix relues dans la journée, par défaut ``ROTATION_SIZE``.

    Returns
    -------
    CollectSummary
        Résumé écrit dans ``runs/collect-AAAA-MM-JJ.json``.

    Notes
    -----
    Le résumé est écrit après chaque étape suivie d'une autre, les étapes
    restantes à ``failed``, puis remplacé à la fin : une collecte coupée
    pendant les sets, les nouvelles cartes ou les prix laisse publiables les
    fichiers déjà écrits. Les sets sont collectés à chaque exécution. Si le
    catalogue du jour est ``ok``, les prix sont tirés de ses fiches sans
    nouvel appel à l'API ; sinon ils sont demandés pour les produits du
    dernier catalogue du dossier antérieur au jour, et ceux des nouvelles
    cartes tirés de leurs fiches. Sans ``catalogue``, le catalogue de la
    veille est ensuite mis à jour (étape ``catalogue``) ; une collecte
    complète en échec n'est pas remplacée par cette mise à jour.
    """
    started_at = now().astimezone(UTC)
    day = started_at.date()
    paths = snapshot_paths(data_dir, day)
    source = latest_catalogue(paths.cards.parent, before=day)
    steps = {
        name: skipped_step() for name in ("catalogue", "sets", "new_cards", "prices")
    }

    def checkpoint(*pending: str) -> None:
        for name in pending:
            steps[name] = _interrupted_step()
        _write_summary(paths, started_at, now, steps)

    cards: dict[str, list[dict[str, Any]]] = {}
    catalogue_at = now()
    if catalogue:
        steps["catalogue"] = _collect_catalogue(
            client, paths, languages, catalogue_at, cards, source
        )
        checkpoint("sets", *(["prices"] if prices else []))
    steps["sets"] = _collect_sets(client, paths, languages, now())
    if not prices:
        return _write_summary(paths, started_at, now, steps)
    if steps["catalogue"]["status"] == "ok":
        checkpoint("prices")
        steps["prices"], _ = _collect_prices(
            paths,
            paths.cards.name,
            read_catalogue(paths.cards),
            languages,
            lambda targets: prices_from_cards(cards, targets, catalogue_at),
            "tirés du catalogue du jour",
        )
        return _write_summary(paths, started_at, now, steps)

    update = not catalogue and source is not None
    checkpoint("prices", *(["catalogue"] if update else []))
    previous: pa.Table | None = None
    base: pa.Table | None = None
    new_cards: dict[str, list[dict[str, Any]]] = {}
    new_table: pa.Table | None = None
    new_at = now()
    if source is not None:
        previous = read_catalogue(source)
        steps["new_cards"], new_table, diff = _collect_new_cards(
            client, paths, languages, previous, source.name, new_at, new_cards
        )
        base = apply_listing(previous, diff, day)
        checkpoint("prices", *(["catalogue"] if update else []))
    price_cards: dict[str, list[dict[str, Any]]] = {}

    def fetch(targets: Sequence[PriceTarget]) -> FetchResult:
        fetched = fetch_prices(client, targets, now=now)
        price_cards.update(fetched.cards)
        if new_table is None:
            return fetched.prices
        new_targets = new_card_targets(new_table, targets)
        logger.info("prix : %d produits de nouvelles cartes", len(new_targets))
        extra = prices_from_cards(new_cards, new_targets, new_at)
        return FetchResult(
            fetched.prices.items + extra.items, fetched.prices.failed + extra.failed
        )

    prices_at = now()
    steps["prices"], targets = _collect_prices(
        paths,
        None if source is None else source.name,
        base,
        languages,
        fetch,
        "à interroger",
    )
    if update and previous is not None and base is not None and source is not None:
        checkpoint("catalogue")
        steps["catalogue"] = _update_catalogue(
            client,
            paths,
            previous,
            base,
            source.name,
            languages,
            [new_cards, price_cards],
            targets,
            rotation,
            prices_at,
        )
    return _write_summary(paths, started_at, now, steps)


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
        "--rotation",
        type=_rotation,
        default=ROTATION_SIZE,
        help=f"fiches hors prix relues (défaut : {ROTATION_SIZE})",
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
            rotation=args.rotation,
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


def _rotation(value: str) -> int:
    """
    Lit l'option ``--rotation``.

    Parameters
    ----------
    value : str
        Nombre de fiches, entier positif ou nul.

    Returns
    -------
    int
        Nombre de fiches relues.

    Raises
    ------
    argparse.ArgumentTypeError
        Si ``value`` n'est pas un entier positif ou nul.
    """
    try:
        size = int(value)
    except ValueError:
        size = -1
    if size < 0:
        raise argparse.ArgumentTypeError(
            f"rotation invalide : {value!r} (entier positif ou nul attendu)"
        )
    return size


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
    steps: dict[str, StepSummary],
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
    steps : dict[str, StepSummary]
        Bilan de chaque étape, copié dans le résumé.

    Returns
    -------
    CollectSummary
        Résumé écrit, de façon atomique, dans ``paths.summary``.
    """
    summary: CollectSummary = {
        "date": started_at.date().isoformat(),
        "started_at": started_at.isoformat(),
        "finished_at": now().astimezone(UTC).isoformat(),
        "steps": dict(steps),
    }
    write_json(summary, paths.summary)
    return summary


def _collect_catalogue(
    client: TcgdexClient,
    paths: SnapshotPaths,
    languages: Sequence[str],
    fetched_at: datetime,
    cards: dict[str, list[dict[str, Any]]],
    source: Path | None,
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
    source : Path | None
        Catalogue précédent : ses lignes sont gardées pour les fiches en échec,
        les cartes non listées et les langues non collectées, et les
        changements sont écrits ; ``None`` écrit les seules fiches lues.

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
    if source is None:
        _write_table(
            report, paths.cards, lambda: catalogue_table(cards, fetched_at), SORT_BY
        )
        return report
    report["source"] = source.name
    previous = read_catalogue(source)
    listed = {
        language: [card["id"] for card in items]
        + [
            failed.split("/", 1)[1]
            for failed in report["failed"]
            if failed.startswith(f"{language}/")
        ]
        for language, items in cards.items()
    }
    base = apply_listing(
        previous, compare_listing(previous, listed), fetched_at.astimezone(UTC).date()
    )
    _write_catalogue(report, paths, previous, base, cards, fetched_at)
    return report


def _collect_sets(
    client: TcgdexClient,
    paths: SnapshotPaths,
    languages: Sequence[str],
    fetched_at: datetime,
) -> StepSummary:
    """
    Collecte les sets de toutes les langues puis écrit leur table.

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

    Returns
    -------
    StepSummary
        ``failed`` si une langue échoue ou si la conversion en table échoue ;
        rien n'est alors écrit, les fiches de sets n'ayant pas de brut à part.
    """
    report = skipped_step()
    sets: dict[str, list[dict[str, Any]]] = {}
    try:
        for language in languages:
            result = fetch_sets(client, language)
            sets[language] = result.items
            report["fetched"] += len(result.items)
            report["failed"] += result.failed
    except TcgdexError as error:
        report["status"] = "failed"
        report["error"] = str(error)
        return report
    _write_table(report, paths.sets, lambda: set_table(sets, fetched_at), SET_SORT_BY)
    return report


def _collect_new_cards(
    client: TcgdexClient,
    paths: SnapshotPaths,
    languages: Sequence[str],
    base: pa.Table,
    source_name: str,
    fetched_at: datetime,
    cards: dict[str, list[dict[str, Any]]],
) -> tuple[StepSummary, pa.Table | None, ListingDiff]:
    """
    Compare les listes au catalogue, télécharge les nouvelles cartes et les écrit.

    Parameters
    ----------
    client : TcgdexClient
        Client de l'API.
    paths : SnapshotPaths
        Fichiers du jour.
    languages : Sequence[str]
        Langues comparées.
    base : pa.Table
        Catalogue de la veille (voir ``read_catalogue``).
    source_name : str
        Nom du fichier de ``base``, pour le résumé.
    fetched_at : datetime
        Début de l'étape, écrit dans la table.
    cards : dict[str, list[dict[str, Any]]]
        Rempli avec les nouvelles fiches par langue, pour en tirer les prix.

    Returns
    -------
    tuple[StepSummary, pa.Table | None, ListingDiff]
        Bilan, ``ok`` sans fichier s'il n'y a aucune nouvelle carte ;
        ``failed`` si une liste ou la collecte échoue (rien n'est écrit) ou
        si la conversion en table échoue (le brut est conservé). Table écrite,
        ``None`` sinon. Écarts des listes, vides si une liste a échoué.
    """
    report = skipped_step()
    report["source"] = source_name
    diff = ListingDiff(new={}, removed={}, reappeared={})
    try:
        diff = listing_diff(client, languages, base)
        for language, card_ids in diff.new.items():
            if card_ids:
                result = fetch_catalogue(client, language, card_ids)
                cards[language] = result.items
                report["fetched"] += len(result.items)
                report["failed"] += result.failed
    except TcgdexError as error:
        report["status"] = "failed"
        report["error"] = str(error)
        return report, None, diff
    logger.info("nouvelles cartes : %d depuis %s", report["fetched"], source_name)
    if not report["fetched"]:
        report["status"] = "ok"
        return report, None, diff
    report["files"].append(
        _file(
            paths.raw_new_cards,
            report["fetched"],
            write_json_gz(cards, paths.raw_new_cards),
        )
    )
    table = _write_table(
        report, paths.new_cards, lambda: catalogue_table(cards, fetched_at), SORT_BY
    )
    if table is not None:
        report["skipped_without_id_product"] = table.column("id_product").null_count
    return report, table, diff


def _collect_prices(
    paths: SnapshotPaths,
    source_name: str | None,
    catalogue: pa.Table | None,
    languages: Sequence[str],
    fetch: Callable[[Sequence[PriceTarget]], FetchResult],
    origin: str,
) -> tuple[StepSummary, list[PriceTarget]]:
    """
    Récupère les prix des produits d'un catalogue et les écrit.

    Parameters
    ----------
    paths : SnapshotPaths
        Fichiers du jour.
    source_name : str | None
        Nom du fichier du catalogue, pour le résumé.
    catalogue : pa.Table | None
        Catalogue au schéma ``CARD_SCHEMA`` ; ``None`` fait échouer l'étape.
    languages : Sequence[str]
        Langues dont les cartes sont retenues.
    fetch : Callable[[Sequence[PriceTarget]], FetchResult]
        Récupère les prix des cibles : ``fetch_prices`` ou
        ``prices_from_cards``.
    origin : str
        Provenance des prix, pour le log.

    Returns
    -------
    tuple[StepSummary, list[PriceTarget]]
        Bilan, ``failed`` sans catalogue, si aucune langue demandée n'y
        figure, si la collecte s'arrête ou si la conversion en table échoue
        (le brut est alors conservé) ; cibles interrogées.
    """
    report = skipped_step()
    if catalogue is None:
        report["status"] = "failed"
        report["error"] = "aucun catalogue disponible"
        return report, []
    report["source"] = source_name
    selection = price_targets_from_catalogue(catalogue, languages)
    missing = selection.missing_languages
    report["missing_languages"] = missing
    if missing:
        logger.warning(
            "prix : langues absentes du catalogue %s : %s",
            source_name,
            ", ".join(missing),
        )
    if len(missing) == len(languages):
        report["status"] = "failed"
        report["error"] = "aucune langue demandée dans le catalogue"
        return report, []
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
        return report, targets
    report["fetched"] = len(result.items)
    report["failed"] = result.failed
    report["files"].append(
        _file(
            paths.raw_prices,
            report["fetched"],
            write_json_gz(result.items, paths.raw_prices),
        )
    )
    _write_table(report, paths.prices, lambda: price_table(result.items), SORT_BY)
    return report, targets


def _update_catalogue(
    client: TcgdexClient,
    paths: SnapshotPaths,
    previous: pa.Table,
    base: pa.Table,
    source_name: str,
    languages: Sequence[str],
    reads: Sequence[dict[str, list[dict[str, Any]]]],
    targets: Sequence[PriceTarget],
    rotation: int,
    read_at: datetime,
) -> StepSummary:
    """
    Relit les fiches de la rotation et écrit le catalogue du jour par fusion.

    Parameters
    ----------
    client : TcgdexClient
        Client de l'API.
    paths : SnapshotPaths
        Fichiers du jour.
    previous : pa.Table
        Catalogue de la veille tel que lu, référence des changements.
    base : pa.Table
        ``previous`` avec ``removed_on`` à jour (voir ``apply_listing``).
    source_name : str
        Nom du fichier de ``previous``, pour le résumé.
    languages : Sequence[str]
        Langues dont les fiches sont relues.
    reads : Sequence[dict[str, list[dict[str, Any]]]]
        Fiches déjà lues dans la journée par langue : nouvelles cartes, prix.
    targets : Sequence[PriceTarget]
        Cibles des prix, exclues de la rotation.
    rotation : int
        Nombre maximal de fiches relues.
    read_at : datetime
        Heure de lecture retenue pour toutes les fiches lues.

    Returns
    -------
    StepSummary
        ``fetched`` : fiches relues par la rotation ; ``changes`` : nombres par
        type de changement et ``rotated``. ``failed`` si la rotation s'arrête
        (le catalogue est quand même écrit avec ce qui a été lu) ou si la
        fusion échoue (rien n'est écrit).
    """
    report = skipped_step()
    report["source"] = source_name
    candidates = base.filter(
        pc.is_in(base.column("language"), pa.array(languages, type=pa.string()))
    )
    rotated: dict[str, list[dict[str, Any]]] = {}
    error = None
    try:
        for language, card_ids in rotation_ids(candidates, targets, rotation).items():
            result = fetch_catalogue(client, language, card_ids)
            rotated[language] = result.items
            report["fetched"] += len(result.items)
            report["failed"] += result.failed
    except TcgdexError as stop:
        error = str(stop)
    read: dict[str, list[dict[str, Any]]] = {}
    for group in [*reads, rotated]:
        for language, items in group.items():
            read.setdefault(language, []).extend(items)
    logger.info("catalogue : %d fiches relues par la rotation", report["fetched"])
    _write_catalogue(report, paths, previous, base, read, read_at)
    if "changes" in report:
        report["changes"]["rotated"] = report["fetched"]
    if error is not None:
        report["status"] = "failed"
        report["error"] = error
    return report


def _write_catalogue(
    report: StepSummary,
    paths: SnapshotPaths,
    previous: pa.Table,
    base: pa.Table,
    read: dict[str, list[dict[str, Any]]],
    read_at: datetime,
) -> None:
    """
    Fusionne les fiches lues au catalogue précédent et écrit ses changements.

    Parameters
    ----------
    report : StepSummary
        Bilan de l'étape, complété (``status``, ``files``, ``error``,
        ``changes``).
    paths : SnapshotPaths
        Fichiers du jour.
    previous : pa.Table
        Catalogue précédent tel que lu, référence des changements.
    base : pa.Table
        ``previous`` avec ``removed_on`` à jour.
    read : dict[str, list[dict[str, Any]]]
        Fiches complètes lues, par langue.
    read_at : datetime
        Heure de lecture des fiches.
    """
    changed, refreshed = changed_cards(base, read)
    merged = _write_table(
        report,
        paths.cards,
        lambda: merge_catalogue(base, changed, refreshed, read_at),
        SORT_BY,
    )
    if merged is None:
        return
    changes = card_changes_table(previous, merged)
    report["files"].append(
        _file(
            paths.card_changes,
            changes.num_rows,
            write_parquet(changes, paths.card_changes, SORT_BY),
        )
    )
    report["changes"] = count_changes(changes)
    logger.info("catalogue : changements %s", report["changes"])


def _write_table(
    report: StepSummary,
    path: Path,
    build: Callable[[], pa.Table],
    sort_by: Sequence[str],
) -> pa.Table | None:
    """
    Construit la table d'une étape et l'écrit, le brut éventuel déjà sauvegardé.

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
    sort_by : Sequence[str]
        Colonnes de tri du Parquet.

    Returns
    -------
    pa.Table | None
        Table écrite, ``None`` si la conversion a échoué.
    """
    try:
        table = build()
    except Exception as error:
        report["status"] = "failed"
        report["error"] = f"conversion en table impossible ({type(error).__name__})"
        logger.error("%s : %s, brut conservé", path.name, report["error"])
        return None
    report["files"].insert(
        0, _file(path, table.num_rows, write_parquet(table, path, sort_by))
    )
    report["status"] = "ok"
    return table


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
