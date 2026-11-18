"""
Mise à jour quotidienne du catalogue sans collecte complète.

Les fiches lues dans la journée sont comparées au catalogue de la veille par
empreinte (voir ``snapshot.card_fingerprint``).
"""

from collections.abc import Mapping, Sequence
from typing import Any

import pyarrow as pa

from cartograph.bin.collect.prices import PriceTarget
from cartograph.bin.collect.snapshot import card_fingerprint


def changed_cards(
    base: pa.Table, cards: Mapping[str, Sequence[dict[str, Any]]]
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[str]]]:
    """
    Sépare les fiches lues en fiches modifiées et fiches identiques.

    Parameters
    ----------
    base : pa.Table
        Catalogue de la veille au schéma ``snapshot.CARD_SCHEMA``.
    cards : Mapping[str, Sequence[dict[str, Any]]]
        Fiches complètes lues dans la journée, par langue.

    Returns
    -------
    tuple[dict[str, list[dict[str, Any]]], dict[str, list[str]]]
        Fiches dont l'empreinte diffère de la ligne du catalogue, ou absentes
        du catalogue, par langue ; identifiants des fiches identiques, dont
        seul ``fetched_at`` est à avancer, par langue. Langues sans fiche
        omises.
    """
    known = dict(
        zip(
            zip(
                base.column("language").to_pylist(),
                base.column("card_id").to_pylist(),
                strict=True,
            ),
            base.column("fingerprint").to_pylist(),
            strict=True,
        )
    )
    changed: dict[str, list[dict[str, Any]]] = {}
    identical: dict[str, list[str]] = {}
    for language, items in cards.items():
        for card in items:
            if known.get((language, card["id"])) == card_fingerprint(card):
                identical.setdefault(language, []).append(card["id"])
            else:
                changed.setdefault(language, []).append(card)
    return changed, identical


def rotation_ids(
    base: pa.Table, price_targets: Sequence[PriceTarget], size: int
) -> dict[str, list[str]]:
    """
    Choisit les fiches du catalogue à relire, les plus anciennes d'abord.

    Les fiches des cibles de prix sont relues chaque jour avec les prix ; les
    cartes disparues ne sont plus servies par les listes de l'API.

    Parameters
    ----------
    base : pa.Table
        Catalogue de la veille au schéma ``snapshot.CARD_SCHEMA``.
    price_targets : Sequence[PriceTarget]
        Cartes interrogées pour les prix du jour, exclues.
    size : int
        Nombre maximal de fiches, toutes langues confondues.

    Returns
    -------
    dict[str, list[str]]
        Identifiants par langue, triés par ``fetched_at`` puis ``card_id`` ;
        langues sans fiche omises, vide si ``size`` vaut 0.

    Examples
    --------
    >>> rotation_ids(pa.table({"card_id": pa.array([], pa.string())}), [], 0)
    {}
    """
    if size <= 0:
        return {}
    excluded = {(target.language, target.card_id) for target in price_targets}
    rows = zip(
        base.column("fetched_at").to_pylist(),
        base.column("card_id").to_pylist(),
        base.column("language").to_pylist(),
        base.column("removed_on").to_pylist(),
        strict=True,
    )
    candidates = sorted(
        (fetched_at, card_id, language)
        for fetched_at, card_id, language, removed_on in rows
        if removed_on is None and (language, card_id) not in excluded
    )
    rotated: dict[str, list[str]] = {}
    for _, card_id, language in candidates[:size]:
        rotated.setdefault(language, []).append(card_id)
    return rotated
