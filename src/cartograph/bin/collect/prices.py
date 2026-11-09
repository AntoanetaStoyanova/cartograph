"""
Prix Cardmarket : une requête par produit, pas une par carte.
- Plusieurs cartes, par ex la version française et l'anglaise, partagent le même
idProduct et donc le même prix.
- price_targets_from_table parcourt les langues dans l'ordre fr, en, ja et garde
la première carte rencontrée pour chaque produit.
- Résultat: ex 29 314 requêtes au lieu de 58 000.
- les cartes sans idProduct sont ignorées et comptées
- le jour du catalogue, prices_from_cards lit les prix dans ses fiches, sans
seconde passe sur l'API.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from cartograph.bin.collect import FetchResult
from cartograph.bin.collect.batch import fetch_each
from cartograph.bin.collect.catalogue import card_path
from cartograph.bin.collect.client import TcgdexClient
from cartograph.config import LANGUAGES

_TARGET_COLUMNS = ["language", "card_id", "id_product"]


@dataclass(frozen=True)
class PriceTarget:
    """
    Carte interrogée pour obtenir le prix d'un produit Cardmarket.

    Attributes
    ----------
    language : str
        Langue de la carte interrogée.
    card_id : str
        Identifiant TCGdex de la carte.
    id_product : int
        Identifiant du produit Cardmarket.
    """

    language: str
    card_id: str
    id_product: int


def price_targets_from_table(table: pa.Table) -> list[PriceTarget]:
    """
    Choisit une carte par produit Cardmarket depuis un snapshot du catalogue.

    Les langues sont parcourues dans l'ordre de ``LANGUAGES`` et la première
    carte rencontrée pour chaque ``id_product`` est gardée : les cartes
    européennes d'un même produit partagent leur prix, les japonaises ont
    leurs propres produits.

    Parameters
    ----------
    table : pa.Table
        Catalogue toutes langues confondues, colonnes ``language``,
        ``card_id`` et ``id_product`` (voir ``snapshot.CARD_SCHEMA``) ; l'ordre
        des cartes d'une même langue est conservé, les langues hors
        ``LANGUAGES`` sont ignorées.

    Returns
    -------
    list[PriceTarget]
        Une cible par ``id_product`` ; les lignes sans ``id_product`` sont
        ignorées.

    Examples
    --------
    >>> table = pa.table(
    ...     {
    ...         "language": ["en", "fr"],
    ...         "card_id": ["swsh3-136", "swsh3-136"],
    ...         "id_product": [483559, 483559],
    ...     }
    ... )
    >>> price_targets_from_table(table)
    [PriceTarget(language='fr', card_id='swsh3-136', id_product=483559)]
    """
    rank = {language: index for index, language in enumerate(LANGUAGES)}
    rows = zip(
        table.column("language").to_pylist(),
        table.column("card_id").to_pylist(),
        table.column("id_product").to_pylist(),
        strict=True,
    )
    ordered = sorted(
        (row for row in rows if row[0] in rank), key=lambda row: rank[row[0]]
    )
    targets: dict[int, PriceTarget] = {}
    for language, card_id, id_product in ordered:
        if id_product is not None and id_product not in targets:
            targets[id_product] = PriceTarget(language, card_id, id_product)
    return list(targets.values())


@dataclass(frozen=True)
class PriceSelection:
    """
    Produits à interroger, choisis dans un snapshot du catalogue.

    Attributes
    ----------
    targets : list[PriceTarget]
        Une cible par produit Cardmarket (voir ``price_targets_from_table``).
    missing_languages : list[str]
        Langues demandées absentes du catalogue.
    skipped_without_id_product : int
        Cartes des langues demandées ignorées faute de produit Cardmarket.
    """

    targets: list[PriceTarget]
    missing_languages: list[str]
    skipped_without_id_product: int


def price_targets_from_catalogue(
    source: Path, languages: Sequence[str]
) -> PriceSelection:
    """
    Lit un snapshot du catalogue et choisit les produits à interroger.

    Parameters
    ----------
    source : Path
        Fichier ``cards-AAAA-MM-JJ.parquet``.
    languages : Sequence[str]
        Langues dont les cartes sont gardées.

    Returns
    -------
    PriceSelection
        Cibles des langues demandées, langues absentes du catalogue et cartes
        sans ``id_product`` ; cibles vides si aucune langue demandée n'y figure.
    """
    table = pq.read_table(source, columns=_TARGET_COLUMNS)
    available = set(table.column("language").unique().to_pylist())
    table = table.filter(
        pc.is_in(table.column("language"), pa.array(languages, type=pa.string()))
    )
    return PriceSelection(
        targets=price_targets_from_table(table),
        missing_languages=[lang for lang in languages if lang not in available],
        skipped_without_id_product=table.column("id_product").null_count,
    )


def fetch_prices(
    client: TcgdexClient,
    targets: Sequence[PriceTarget],
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> FetchResult:
    """
    Récupère les prix de chaque cible.

    Parameters
    ----------
    client : TcgdexClient
        Client de l'API.
    targets : Sequence[PriceTarget]
        Cartes à interroger (voir ``price_targets_from_table``).
    now : Callable[[], datetime], optional
        Horloge, par défaut l'heure UTC courante ; injectée en test.

    Returns
    -------
    FetchResult
        Un enregistrement ``{"language", "card_id", "id_product",
        "fetched_at", "pricing"}`` par cible, ``fetched_at`` en UTC
        ISO 8601 et ``pricing`` brut, et les cibles en échec au format
        ``langue/identifiant`` (une carte peut exister dans plusieurs langues).

    Raises
    ------
    TcgdexError
        Après ``MAX_CONSECUTIVE_FAILURES`` cartes en échec d'affilée.

    Notes
    -----
    Une carte en échec est notée dans ``failed`` et la collecte continue.
    Aucune valeur de ``pricing`` n'est journalisée.
    """
    return fetch_each(
        client,
        targets,
        path=lambda target: card_path(target.language, target.card_id),
        build=lambda target, card: _price_record(target, card, now()),
        card_id=lambda target: f"{target.language}/{target.card_id}",
        label="prix",
    )


def prices_from_cards(
    cards: Mapping[str, Sequence[dict[str, Any]]],
    targets: Sequence[PriceTarget],
    fetched_at: datetime,
) -> FetchResult:
    """
    Tire les prix de chaque cible des fiches déjà récupérées par le catalogue.

    Parameters
    ----------
    cards : Mapping[str, Sequence[dict[str, Any]]]
        Fiches complètes par langue, telles que renvoyées par l'API.
    targets : Sequence[PriceTarget]
        Cartes retenues (voir ``price_targets_from_table``).
    fetched_at : datetime
        Heure de récupération des fiches, reprise sur chaque enregistrement.

    Returns
    -------
    FetchResult
        Enregistrements de même forme que ``fetch_prices`` ; une cible absente
        de ``cards`` est notée dans ``failed`` (``langue/identifiant``).

    Examples
    --------
    >>> card = {"id": "swsh3-136", "pricing": None}
    >>> result = prices_from_cards(
    ...     {"fr": [card]},
    ...     [PriceTarget("fr", "swsh3-136", 483559)],
    ...     datetime(2026, 10, 28, tzinfo=UTC),
    ... )
    >>> result.items[0]["fetched_at"], result.failed
    ('2026-10-28T00:00:00+00:00', [])
    """
    by_id = {
        (language, card["id"]): card
        for language, items in cards.items()
        for card in items
    }
    items: list[dict[str, Any]] = []
    failed: list[str] = []
    for target in targets:
        card = by_id.get((target.language, target.card_id))
        if card is None:
            failed.append(f"{target.language}/{target.card_id}")
        else:
            items.append(_price_record(target, card, fetched_at))
    return FetchResult(items, failed)


def _price_record(
    target: PriceTarget, card: dict[str, Any], fetched_at: datetime
) -> dict[str, Any]:
    """
    Enregistrement de prix d'une cible, ``pricing`` brut de sa fiche.

    Parameters
    ----------
    target : PriceTarget
        Carte retenue pour le produit.
    card : dict[str, Any]
        Fiche complète de la carte.
    fetched_at : datetime
        Heure de récupération, convertie en UTC ISO 8601.

    Returns
    -------
    dict[str, Any]
        ``{"language", "card_id", "id_product", "fetched_at", "pricing"}``.
    """
    return {
        "language": target.language,
        "card_id": target.card_id,
        "id_product": target.id_product,
        "fetched_at": fetched_at.astimezone(UTC).isoformat(),
        "pricing": card.get("pricing"),
    }
