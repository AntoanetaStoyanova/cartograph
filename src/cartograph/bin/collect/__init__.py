"""
Collecte du catalogue et des prix depuis l'API TCGdex.

Les fonctions renvoient le JSON brut de l'API, sans transformation. Une carte
en échec est notée dans ``FetchResult.failed`` sans arrêter la collecte.

Modules
-------
client
    Appels HTTP, pause, nouvelles tentatives et erreurs typées.
catalogue
    Liste des identifiants et fiches complètes d'une langue.
prices
    Une carte par produit Cardmarket et récupération de ses prix.
batch
    Boucle commune : échecs, arrêt sur panne, progression.

Examples
--------
>>> from cartograph.bin.collect.catalogue import fetch_catalogue
>>> from cartograph.bin.collect.client import TcgdexClient
>>> from cartograph.bin.collect.prices import fetch_prices, price_targets
>>> with TcgdexClient() as client:  # doctest: +SKIP
...     catalogues = {
...         language: fetch_catalogue(client, language).items
...         for language in ("fr", "en", "ja")
...     }
...     prices = fetch_prices(client, price_targets(catalogues))
>>> prices.failed  # doctest: +SKIP
[]
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FetchResult:
    """
    Résultat d'une collecte.

    Attributes
    ----------
    items : list[dict[str, Any]]
        Enregistrements récupérés, JSON brut de l'API.
    failed : list[str]
        Identifiants des cartes en échec.
    """

    items: list[dict[str, Any]]
    failed: list[str]
