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
snapshot
    Chemins datés, tables typées sans prix dans le catalogue, écriture atomique.
run
    Enchaînement catalogue puis prix, résumé d'exécution.
report
    Résumé Markdown pour la page d'exécution GitHub.
manifest
    Manifeste quotidien sans prix, avec empreintes des fichiers.

Examples
--------
>>> from datetime import UTC, datetime
>>> from pathlib import Path
>>> from cartograph.bin.collect.client import TcgdexClient
>>> from cartograph.bin.collect.run import collect
>>> with TcgdexClient() as client:  # doctest: +SKIP
...     summary = collect(client, Path("data"), True, True, ("fr", "en", "ja"))
>>> summary["steps"]["prices"]["status"]  # doctest: +SKIP
'ok'
"""

from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict


@dataclass(frozen=True)
class FetchResult:
    """
    Résultat d'une collecte.

    Attributes
    ----------
    items : list[dict[str, Any]]
        Enregistrements récupérés, JSON brut de l'API.
    failed : list[str]
        Cartes en échec, au format ``langue/identifiant`` (une carte peut
        exister dans plusieurs langues).
    """

    items: list[dict[str, Any]]
    failed: list[str]


class FileSummary(TypedDict):
    """Fichier écrit par une étape : nom, lignes ou enregistrements, octets."""

    name: str
    rows: int
    bytes: int


class StepSummary(TypedDict):
    """
    Bilan d'une étape de la collecte, sans aucun prix.

    Attributes
    ----------
    status : {"ok", "failed", "skipped"}
        ``skipped`` si l'étape n'a pas été demandée.
    fetched : int
        Fiches ou prix récupérés.
    failed : list[str]
        Cartes en échec, au format ``langue/identifiant``.
    skipped_without_id_product : int
        Cartes ignorées faute de produit Cardmarket (étape prix).
    files : list[FileSummary]
        Fichiers écrits, le Parquet avant le brut.
    source : str | None
        Catalogue utilisé pour les prix.
    missing_languages : list[str]
        Langues demandées absentes du catalogue utilisé pour les prix ; absent
        des premiers résumés (28 octobre 2026).
    error : str | None
        Cause de l'échec de l'étape.
    """

    status: Literal["ok", "failed", "skipped"]
    fetched: int
    failed: list[str]
    skipped_without_id_product: int
    files: list[FileSummary]
    source: str | None
    missing_languages: NotRequired[list[str]]
    error: str | None


class CollectSummary(TypedDict):
    """
    Résumé ``runs/collect-AAAA-MM-JJ.json`` d'une collecte, sans aucun prix.

    Écrit par ``run``, lu par ``report`` et ``manifest``.

    Attributes
    ----------
    date : str
        Jour UTC de la collecte, ``AAAA-MM-JJ``.
    started_at, finished_at : str
        Début et fin, ISO 8601 en UTC.
    steps : dict[str, StepSummary]
        Bilan par étape : ``catalogue``, ``prices``.
    """

    date: str
    started_at: str
    finished_at: str
    steps: dict[str, StepSummary]
