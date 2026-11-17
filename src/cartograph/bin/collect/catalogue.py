"""
Catalogue d'une langue : liste des identifiants (par exemple ``/fr/cards``),
fiches complètes et cartes absentes du dernier catalogue.
"""

from collections.abc import Sequence
from pathlib import Path
from urllib.parse import quote

import pyarrow.parquet as pq

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
        Fiches récupérées et cartes en échec (``langue/identifiant``).

    Raises
    ------
    ValueError
        Si ``language`` n'appartient pas à ``LANGUAGES``, avant tout appel.
    TcgdexError
        Si la liste des identifiants ne peut pas être récupérée, ou après
        ``MAX_CONSECUTIVE_FAILURES`` cartes en échec d'affilée.

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


def new_card_ids(
    client: TcgdexClient, languages: Sequence[str], catalogue: Path
) -> dict[str, list[str]]:
    """
    Renvoie les cartes listées par l'API et absentes d'un catalogue.

    Parameters
    ----------
    client : TcgdexClient
        Client de l'API.
    languages : Sequence[str]
        Langues comparées, parmi ``LANGUAGES``.
    catalogue : Path
        Snapshot ``cards-AAAA-MM-JJ.parquet`` de référence.

    Returns
    -------
    dict[str, list[str]]
        Nouveaux identifiants par langue, dans l'ordre de l'API ; liste vide,
        sans appel, pour une langue absente du catalogue (toutes ses cartes
        seraient nouvelles).

    Raises
    ------
    ValueError
        Si une langue n'appartient pas à ``LANGUAGES``.
    TcgdexError
        Si une liste ne peut pas être récupérée.
    """
    table = pq.read_table(catalogue, columns=["language", "card_id"])
    known: dict[str, set[str]] = {}
    for language, card_id in zip(
        table.column("language").to_pylist(),
        table.column("card_id").to_pylist(),
        strict=True,
    ):
        known.setdefault(language, set()).add(card_id)
    new: dict[str, list[str]] = {}
    for language in languages:
        check_language(language)
        if language not in known:
            new[language] = []
            continue
        listed = list_card_ids(client, language)
        new[language] = [
            card_id for card_id in listed if card_id not in known[language]
        ]
    return new


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
