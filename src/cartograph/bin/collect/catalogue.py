"""
Catalogue d'une langue : liste des identifiants (par exemple ``/fr/cards``),
fiches complètes et écarts entre les listes de l'API et le dernier catalogue.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from urllib.parse import quote

import pyarrow as pa

from cartograph.bin.collect import FetchResult
from cartograph.bin.collect.batch import fetch_each
from cartograph.bin.collect.client import TcgdexClient
from cartograph.config import LANGUAGES


def list_card_ids(client: TcgdexClient, language: str) -> list[str]:
    """
    Renvoie les identifiants de toutes les cartes d'une langue.

    Parameters
    ----------
    client : TcgdexClient
        Client de l'API.
    language : str
        Code de langue, parmi ``LANGUAGES``.

    Returns
    -------
    list[str]
        Identifiants dans l'ordre de l'API.

    Raises
    ------
    ValueError
        Si ``language`` n'appartient pas à ``LANGUAGES``.
    TcgdexError
        Si l'API ne renvoie pas la liste.
    """
    check_language(language)
    return [card["id"] for card in client.get_json(f"/{language}/cards")]


def fetch_catalogue(
    client: TcgdexClient,
    language: str,
    card_ids: Sequence[str] | None = None,
) -> FetchResult:
    """
    Récupère la fiche complète de chaque carte d'une langue.

    Parameters
    ----------
    client : TcgdexClient
        Client de l'API.
    language : str
        Code de langue, parmi ``LANGUAGES``.
    card_ids : Sequence[str] | None, optional
        Cartes à récupérer ; toute la langue si ``None`` (voir
        ``list_card_ids``).

    Returns
    -------
    FetchResult
        Fiches récupérées et cartes en échec (``langue/identifiant``) ;
        ``error`` posé après ``MAX_CONSECUTIVE_FAILURES`` cartes en échec
        d'affilée.

    Raises
    ------
    ValueError
        Si ``language`` n'appartient pas à ``LANGUAGES``, avant tout appel.
    TcgdexError
        Si la liste des identifiants ne peut pas être récupérée.

    Notes
    -----
    Une carte en échec est notée dans ``failed`` et la collecte continue.
    """
    if card_ids is None:
        card_ids = list_card_ids(client, language)
    else:
        check_language(language)
    return fetch_each(
        client,
        card_ids,
        path=lambda card_id: card_path(language, card_id),
        build=lambda _, card: card,
        card_id=lambda card_id: f"{language}/{card_id}",
        label=f"catalogue {language}",
    )


@dataclass(frozen=True)
class ListingDiff:
    """
    Écarts entre les listes ``/<langue>/cards`` et un catalogue, par langue.

    Attributes
    ----------
    new : dict[str, list[str]]
        Cartes listées, absentes du catalogue, dans l'ordre de l'API.
    removed : dict[str, list[str]]
        Cartes du catalogue non disparues et non listées, triées.
    reappeared : dict[str, list[str]]
        Cartes déjà disparues (``removed_on`` posé) de nouveau listées, dans
        l'ordre de l'API.
    """

    new: dict[str, list[str]]
    removed: dict[str, list[str]]
    reappeared: dict[str, list[str]]


def listing_diff(
    client: TcgdexClient, languages: Sequence[str], catalogue: pa.Table
) -> ListingDiff:
    """
    Compare les listes de l'API au catalogue : nouvelles, disparues, revenues.

    Parameters
    ----------
    client : TcgdexClient
        Client de l'API.
    languages : Sequence[str]
        Langues comparées, parmi ``LANGUAGES`` ; une lecture de liste chacune.
    catalogue : pa.Table
        Catalogue au schéma ``snapshot.CARD_SCHEMA`` (voir
        ``snapshot.read_catalogue``).

    Returns
    -------
    ListingDiff
        Une entrée par langue ; listes vides, sans appel, pour une langue
        absente du catalogue (toutes ses cartes seraient nouvelles).

    Raises
    ------
    ValueError
        Si une langue n'appartient pas à ``LANGUAGES``.
    TcgdexError
        Si une liste ne peut pas être récupérée.

    Notes
    -----
    Une liste vide ne fait disparaître aucune carte : une réponse vide de
    l'API est plus probablement une panne qu'un catalogue vidé.
    """
    known = set(catalogue.column("language").to_pylist())
    listed: dict[str, list[str]] = {}
    for language in languages:
        check_language(language)
        listed[language] = list_card_ids(client, language) if language in known else []
    return compare_listing(catalogue, listed)


def compare_listing(
    catalogue: pa.Table, listed: Mapping[str, Sequence[str]]
) -> ListingDiff:
    """
    Compare des identifiants listés au catalogue, sans appel à l'API.

    Parameters
    ----------
    catalogue : pa.Table
        Catalogue au schéma ``snapshot.CARD_SCHEMA``.
    listed : Mapping[str, Sequence[str]]
        Identifiants listés par langue ; une liste vide ne fait disparaître
        aucune carte.

    Returns
    -------
    ListingDiff
        Une entrée par langue de ``listed``.

    Examples
    --------
    >>> import pyarrow as pa
    >>> empty = pa.table(
    ...     {
    ...         "language": pa.array([], pa.string()),
    ...         "card_id": pa.array([], pa.string()),
    ...         "removed_on": pa.array([], pa.date32()),
    ...     }
    ... )
    >>> compare_listing(empty, {"fr": ["a"]}).new
    {'fr': ['a']}
    """
    active: dict[str, set[str]] = {}
    gone: dict[str, set[str]] = {}
    for language, card_id, removed_on in zip(
        catalogue.column("language").to_pylist(),
        catalogue.column("card_id").to_pylist(),
        catalogue.column("removed_on").to_pylist(),
        strict=True,
    ):
        (active if removed_on is None else gone).setdefault(language, set()).add(
            card_id
        )
    diff = ListingDiff(new={}, removed={}, reappeared={})
    for language, ids in listed.items():
        known = active.get(language, set())
        removed = gone.get(language, set())
        seen = known | removed
        diff.new[language] = [card_id for card_id in ids if card_id not in seen]
        diff.removed[language] = sorted(known - set(ids)) if ids else []
        diff.reappeared[language] = [card_id for card_id in ids if card_id in removed]
    return diff


def card_path(language: str, card_id: str) -> str:
    """
    Renvoie le chemin de la fiche d'une carte, identifiant encodé.

    Certains identifiants contiennent des caractères réservés (``exu-%3F``).

    Parameters
    ----------
    language : str
        Code de langue.
    card_id : str
        Identifiant TCGdex de la carte.

    Returns
    -------
    str
        Chemin relatif à la racine de l'API.

    Examples
    --------
    >>> card_path("fr", "exu-%3F")
    '/fr/cards/exu-%253F'
    """
    return f"/{language}/cards/{quote(card_id, safe='')}"


def check_language(language: str) -> None:
    """
    Refuse une langue hors ``LANGUAGES``.

    Parameters
    ----------
    language : str
        Code de langue.

    Raises
    ------
    ValueError
        Si ``language`` n'appartient pas à ``LANGUAGES``.
    """
    if language not in LANGUAGES:
        raise ValueError(f"Langue inconnue : {language!r}, attendu parmi {LANGUAGES}")
