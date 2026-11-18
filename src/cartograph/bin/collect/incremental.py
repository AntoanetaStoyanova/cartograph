"""
Mise à jour quotidienne du catalogue sans collecte complète.

Les fiches lues dans la journée sont comparées au catalogue de la veille par
empreinte (voir ``snapshot.card_fingerprint``).
"""

from collections.abc import Mapping, Sequence
from typing import Any

import pyarrow as pa

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
