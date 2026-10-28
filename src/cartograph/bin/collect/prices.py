"""
Prix Cardmarket : une requête par produit.
"""

import logging
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pyarrow as pa

from cartograph.bin.collect import FetchResult
from cartograph.bin.collect.batch import fetch_each
from cartograph.bin.collect.catalogue import card_path
from cartograph.bin.collect.client import TcgdexClient
from cartograph.config import LANGUAGES

logger = logging.getLogger(__name__)


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


def price_targets(
    catalogues: Mapping[str, Sequence[dict[str, Any]]],
) -> list[PriceTarget]:
    """
    Choisit une carte par produit Cardmarket.

    Les langues sont parcourues dans l'ordre de ``LANGUAGES`` et la première
    carte rencontrée pour chaque ``idProduct`` est gardée : les cartes
    européennes d'un même produit partagent leur prix, les japonaises ont
    leurs propres produits.

    Parameters
    ----------
    catalogues : Mapping[str, Sequence[dict[str, Any]]]
        Fiches complètes par langue (voir ``fetch_catalogue``) ; les langues
        hors ``LANGUAGES`` sont ignorées.

    Returns
    -------
    list[PriceTarget]
        Une cible par ``idProduct`` ; les cartes sans ``idProduct`` sont
        ignorées.

    Examples
    --------
    >>> card = {"id": "swsh3-136", "pricing": {"cardmarket": {"idProduct": 483559}}}
    >>> price_targets({"en": [card], "fr": [card]})
    [PriceTarget(language='fr', card_id='swsh3-136', id_product=483559)]
    """
    return _dedupe(
        (language, card["id"], card_id_product(card))
        for language, cards in catalogues.items()
        for card in cards
    )


def price_targets_from_table(table: pa.Table) -> list[PriceTarget]:
    """
    Choisit une carte par produit Cardmarket depuis un snapshot du catalogue.

    Même règle que ``price_targets``, appliquée aux colonnes ``language``,
    ``card_id`` et ``id_product`` (voir ``snapshot.CARD_SCHEMA``).

    Parameters
    ----------
    table : pa.Table
        Table du catalogue, toutes langues confondues.

    Returns
    -------
    list[PriceTarget]
        Une cible par ``id_product`` ; les lignes sans ``id_product`` sont
        ignorées.
    """
    return _dedupe(
        zip(
            table.column("language").to_pylist(),
            table.column("card_id").to_pylist(),
            table.column("id_product").to_pylist(),
            strict=True,
        )
    )


def _dedupe(rows: Iterable[tuple[str, str, int | None]]) -> list[PriceTarget]:
    """
    Garde la première carte par produit, langues dans l'ordre de ``LANGUAGES``.

    Parameters
    ----------
    rows : Iterable[tuple[str, str, int | None]]
        Triplets ``(langue, carte, idProduct)`` ; l'ordre des cartes d'une
        même langue est conservé, les langues hors ``LANGUAGES`` sont ignorées.

    Returns
    -------
    list[PriceTarget]
        Une cible par ``idProduct``.
    """
    rank = {language: index for index, language in enumerate(LANGUAGES)}
    ordered = sorted(
        (row for row in rows if row[0] in rank), key=lambda row: rank[row[0]]
    )
    targets: dict[int, PriceTarget] = {}
    skipped = 0
    for language, card_id, id_product in ordered:
        if id_product is None:
            skipped += 1
        elif id_product not in targets:
            targets[id_product] = PriceTarget(language, card_id, id_product)
    logger.info(
        "prix : %d produits à interroger, %d cartes ignorées sans idProduct",
        len(targets),
        skipped,
    )
    return list(targets.values())


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
        Cartes à interroger (voir ``price_targets``).
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
        build=lambda target, card: {
            "language": target.language,
            "card_id": target.card_id,
            "id_product": target.id_product,
            "fetched_at": now().astimezone(UTC).isoformat(),
            "pricing": card.get("pricing"),
        },
        card_id=lambda target: f"{target.language}/{target.card_id}",
        label="prix",
    )


def card_id_product(card: dict[str, Any]) -> int | None:
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
