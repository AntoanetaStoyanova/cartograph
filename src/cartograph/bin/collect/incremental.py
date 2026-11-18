"""
Mise à jour quotidienne du catalogue sans collecte complète.

Les fiches lues dans la journée sont comparées au catalogue de la veille par
empreinte (voir ``snapshot.card_fingerprint``).
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from typing import Any

import pyarrow as pa

from cartograph.bin.collect.catalogue import ListingDiff
from cartograph.bin.collect.prices import PriceTarget
from cartograph.bin.collect.snapshot import (
    CHANGE_SCHEMA,
    card_fingerprint,
    catalogue_table,
)

CHANGE_TYPES = ("new", "updated", "removed", "reappeared")


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


def apply_listing(base: pa.Table, diff: ListingDiff, day: date) -> pa.Table:
    """
    Pose ``removed_on`` des cartes disparues, l'efface pour les revenues.

    Parameters
    ----------
    base : pa.Table
        Catalogue de la veille au schéma ``snapshot.CARD_SCHEMA``.
    diff : ListingDiff
        Écarts entre les listes de l'API et ``base``.
    day : date
        Jour UTC de la collecte, posé sur les cartes disparues.

    Returns
    -------
    pa.Table
        ``base`` avec ``removed_on`` à jour ; aucune ligne retirée.
    """
    removed = _keys_of(diff.removed)
    back = _keys_of(diff.reappeared)
    if not removed and not back:
        return base
    removed_on = [
        day if key in removed else None if key in back else value
        for key, value in zip(
            _keys(base), base.column("removed_on").to_pylist(), strict=True
        )
    ]
    return _set(base, "removed_on", removed_on)


def merge_catalogue(
    base: pa.Table,
    changed: Mapping[str, Sequence[dict[str, Any]]],
    refreshed: Mapping[str, Sequence[str]],
    read_at: datetime,
) -> pa.Table:
    """
    Construit le catalogue du jour à partir de celui de la veille.

    Parameters
    ----------
    base : pa.Table
        Catalogue de la veille, ``removed_on`` déjà à jour (voir
        ``apply_listing``).
    changed : Mapping[str, Sequence[dict[str, Any]]]
        Fiches nouvelles ou modifiées par langue (voir ``changed_cards``) :
        elles remplacent leur ligne ou sont ajoutées.
    refreshed : Mapping[str, Sequence[str]]
        Fiches lues identiques par langue : seul ``fetched_at`` avance.
    read_at : datetime
        Heure de lecture, convertie en UTC, des fiches de ``changed`` et
        ``refreshed``.

    Returns
    -------
    pa.Table
        Table au schéma ``snapshot.CARD_SCHEMA`` ; les lignes non lues, dont
        celles des fiches en échec, sont gardées telles quelles.
    """
    read_at = read_at.astimezone(UTC)
    removed_on = dict(
        zip(_keys(base), base.column("removed_on").to_pylist(), strict=True)
    )
    replaced = {
        (language, card["id"]) for language, items in changed.items() for card in items
    }
    advanced = _keys_of(refreshed)
    kept = base.filter(
        pa.array([key not in replaced for key in _keys(base)], pa.bool_())
    )
    fetched_at = [
        read_at if key in advanced else value
        for key, value in zip(
            _keys(kept), kept.column("fetched_at").to_pylist(), strict=True
        )
    ]
    kept = _set(kept, "fetched_at", fetched_at)
    fresh = catalogue_table(changed, read_at)
    fresh = _set(fresh, "removed_on", [removed_on.get(key) for key in _keys(fresh)])
    return pa.concat_tables([kept, fresh])


def card_changes_table(base: pa.Table, merged: pa.Table) -> pa.Table:
    """
    Liste les changements entre le catalogue de la veille et celui du jour.

    Parameters
    ----------
    base : pa.Table
        Catalogue de la veille au schéma ``snapshot.CARD_SCHEMA``.
    merged : pa.Table
        Catalogue du jour (voir ``merge_catalogue``).

    Returns
    -------
    pa.Table
        Table au schéma ``snapshot.CHANGE_SCHEMA``, sans prix : une ligne par
        carte et type de changement, avec la ligne du jour.
    """
    before = {
        key: (fingerprint, removed_on)
        for key, fingerprint, removed_on in zip(
            _keys(base),
            base.column("fingerprint").to_pylist(),
            base.column("removed_on").to_pylist(),
            strict=True,
        )
    }
    indices: list[int] = []
    types: list[str] = []
    for index, (key, fingerprint, removed_on) in enumerate(
        zip(
            _keys(merged),
            merged.column("fingerprint").to_pylist(),
            merged.column("removed_on").to_pylist(),
            strict=True,
        )
    ):
        for change_type in _change_types(before.get(key), fingerprint, removed_on):
            indices.append(index)
            types.append(change_type)
    rows = merged.take(pa.array(indices, pa.int64()))
    return rows.add_column(0, "change_type", pa.array(types, pa.string())).cast(
        CHANGE_SCHEMA
    )


def count_changes(changes: pa.Table) -> dict[str, int]:
    """
    Compte les lignes de chaque type de changement.

    Parameters
    ----------
    changes : pa.Table
        Table au schéma ``snapshot.CHANGE_SCHEMA``.

    Returns
    -------
    dict[str, int]
        Nombre par type de ``CHANGE_TYPES``, zéro compris.
    """
    counts = Counter(changes.column("change_type").to_pylist())
    return {change_type: counts[change_type] for change_type in CHANGE_TYPES}


def _change_types(
    before: tuple[str, date | None] | None, fingerprint: str, removed_on: date | None
) -> list[str]:
    """Types de changement d'une carte, d'après sa ligne de la veille."""
    if before is None:
        return ["new"]
    old_fingerprint, old_removed_on = before
    types = []
    if old_fingerprint != fingerprint:
        types.append("updated")
    if old_removed_on is None and removed_on is not None:
        types.append("removed")
    if old_removed_on is not None and removed_on is None:
        types.append("reappeared")
    return types


def _keys(table: pa.Table) -> list[tuple[str, str]]:
    """Clés ``(language, card_id)`` des lignes, dans l'ordre."""
    return list(
        zip(
            table.column("language").to_pylist(),
            table.column("card_id").to_pylist(),
            strict=True,
        )
    )


def _keys_of(ids: Mapping[str, Sequence[str]]) -> set[tuple[str, str]]:
    """Clés ``(language, card_id)`` d'identifiants rangés par langue."""
    return {(language, card_id) for language, items in ids.items() for card_id in items}


def _set(table: pa.Table, name: str, values: Sequence[Any]) -> pa.Table:
    """Remplace une colonne en gardant son type."""
    index = table.schema.get_field_index(name)
    return table.set_column(
        index, name, pa.array(values, table.schema.field(index).type)
    )
