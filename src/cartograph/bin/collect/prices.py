"""
Prix Cardmarket : une requête par produit.
"""

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

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
    targets: dict[int, PriceTarget] = {}
    skipped = 0
    for language in LANGUAGES:
        for card in catalogues.get(language, ()):
            id_product = _id_product(card)
            if id_product is None:
                skipped += 1
            elif id_product not in targets:
                targets[id_product] = PriceTarget(language, card["id"], id_product)
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
        ISO 8601 et ``pricing`` brut, et les identifiants en échec.

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
        card_id=lambda target: target.card_id,
        label="prix",
    )


def _id_product(card: dict[str, Any]) -> int | None:
    """Renvoie ``pricing.cardmarket.idProduct`` de la fiche, ``None`` si absent."""
    cardmarket = (card.get("pricing") or {}).get("cardmarket") or {}
    id_product: int | None = cardmarket.get("idProduct")
    return id_product
