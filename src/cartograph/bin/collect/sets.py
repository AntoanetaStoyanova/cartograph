"""
Sets d'une langue : liste des identifiants (par exemple ``/fr/sets``) et fiches
complètes, avec date de sortie et série.
"""

from urllib.parse import quote

from cartograph.bin.collect import FetchResult
from cartograph.bin.collect.batch import fetch_each
from cartograph.bin.collect.catalogue import check_language
from cartograph.bin.collect.client import TcgdexClient


def list_set_ids(client: TcgdexClient, language: str) -> list[str]:
    """
    Renvoie les identifiants de tous les sets d'une langue.

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
    return [item["id"] for item in client.get_json(f"/{language}/sets")]


def fetch_sets(client: TcgdexClient, language: str) -> FetchResult:
    """
    Récupère la fiche complète de chaque set d'une langue.

    Parameters
    ----------
    client : TcgdexClient
        Client de l'API.
    language : str
        Code de langue, parmi ``LANGUAGES``.

    Returns
    -------
    FetchResult
        Fiches récupérées et sets en échec (``langue/identifiant``).

    Raises
    ------
    ValueError
        Si ``language`` n'appartient pas à ``LANGUAGES``, avant tout appel.
    TcgdexError
        Si la liste des sets ne peut pas être récupérée, ou après
        ``MAX_CONSECUTIVE_FAILURES`` sets en échec d'affilée.
    """
    return fetch_each(
        client,
        list_set_ids(client, language),
        path=lambda set_id: set_path(language, set_id),
        build=lambda _, item: item,
        card_id=lambda set_id: f"{language}/{set_id}",
        label=f"sets {language}",
    )


def set_path(language: str, set_id: str) -> str:
    """
    Renvoie le chemin de la fiche d'un set, identifiant encodé.

    Certains identifiants japonais contiennent ``+`` (``SM1+``).

    Parameters
    ----------
    language : str
        Code de langue.
    set_id : str
        Identifiant TCGdex du set.

    Returns
    -------
    str
        Chemin relatif à la racine de l'API.

    Examples
    --------
    >>> set_path("ja", "SM1+")
    '/ja/sets/SM1%2B'
    """
    return f"/{language}/sets/{quote(set_id, safe='')}"
