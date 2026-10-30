"""
Prix Cardmarket : une requête par produit, pas une par carte.
- Plusieurs cartes, par ex la version française et l'anglaise, partagent le même
idProduct et donc le même prix.
- price_targets_from_table parcourt les langues dans l'ordre fr, en, ja et garde
la première carte rencontrée pour chaque produit.
- Résultat: ex 29 314 requêtes au lieu de 58 000.
- les cartes sans idProduct sont ignorées et comptées
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import pyarrow as pa

from cartograph.bin.collect import FetchResult
from cartograph.bin.collect.batch import fetch_each
from cartograph.bin.collect.catalogue import card_path
from cartograph.bin.collect.client import TcgdexClient
from cartograph.config import LANGUAGES


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
