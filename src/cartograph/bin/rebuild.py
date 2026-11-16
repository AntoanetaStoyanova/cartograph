"""
Snapshots Parquet des Releases GitHub, rapatriés pour reconstruire la base.

Le catalogue est dans la Release ``catalogue`` de ``DATA_REPO``, les prix dans
les Releases ``data-AAAA-MM`` de ``PRICES_REPO`` (privé, lu avec la session
``gh`` locale). Un fichier n'est téléchargé que s'il manque ou si son SHA-256
diffère du ``digest`` donné par GitHub : une collecte relancée le même jour
remplace le fichier du jour sous le même nom.
"""

import hashlib
import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Asset:
    """
    Fichier Parquet d'une Release.

    Attributes
    ----------
    repo : str
        Dépôt GitHub (``propriétaire/nom``).
    tag : str
        Tag de la Release.
    name : str
        Nom du fichier.
    size : int
        Taille en octets.
    sha256 : str
        Empreinte SHA-256 en hexadécimal, sans préfixe.
    """

    repo: str
    tag: str
    name: str
    size: int
    sha256: str


def list_assets(repo: str, tag_prefix: str) -> list[Asset]:
    """
    Liste les fichiers Parquet des Releases dont le tag commence par un préfixe.

    Parameters
    ----------
    repo : str
        Dépôt GitHub (``propriétaire/nom``).
    tag_prefix : str
        Début des tags retenus (``catalogue``, ``data-``).

    Returns
    -------
    list[Asset]
        Fichiers ``*.parquet``, dans l'ordre des Releases puis des fichiers.

    Raises
    ------
    RuntimeError
        Si ``gh`` échoue, avec le dépôt et le message d'erreur.
    """
    tags = _gh(
        repo, "list", "--limit", "1000", "--json", "tagName", "--jq", ".[].tagName"
    )
    assets: list[Asset] = []
    for tag in (t for t in tags.splitlines() if t.startswith(tag_prefix)):
        view = json.loads(_gh(repo, "view", tag, "--json", "assets"))
        assets.extend(
            Asset(repo, tag, a["name"], a["size"], a["digest"].removeprefix("sha256:"))
            for a in view["assets"]
            if a["name"].endswith(".parquet")
        )
    return assets


def plan_downloads(assets: Sequence[Asset], snapshot_dir: Path) -> list[Asset]:
    """
    Choisit les fichiers à télécharger.

    Parameters
    ----------
    assets : Sequence[Asset]
        Fichiers des Releases.
    snapshot_dir : Path
        Dossier local des snapshots.

    Returns
    -------
    list[Asset]
        Fichiers absents du dossier ou dont le SHA-256 local diffère.
    """
    return [a for a in assets if file_sha256(snapshot_dir / a.name) != a.sha256]


def orphans(assets: Sequence[Asset], snapshot_dir: Path) -> list[Path]:
    """
    Liste les Parquet locaux absents des Releases, gardés comme sauvegarde.

    Parameters
    ----------
    assets : Sequence[Asset]
        Fichiers des Releases.
    snapshot_dir : Path
        Dossier local des snapshots.

    Returns
    -------
    list[Path]
        Fichiers ``*.parquet`` du dossier sans équivalent publié, triés.
    """
    published = {a.name for a in assets}
    return sorted(p for p in snapshot_dir.glob("*.parquet") if p.name not in published)


def file_sha256(path: Path) -> str | None:
    """
    Calcule le SHA-256 d'un fichier.

    Parameters
    ----------
    path : Path
        Fichier à lire.

    Returns
    -------
    str or None
        Empreinte en hexadécimal, ``None`` si le fichier n'existe pas.
    """
    if not path.is_file():
        return None
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def _gh(repo: str, *args: str) -> str:
    """Lance ``gh release <args> -R <repo>`` et renvoie sa sortie standard."""
    try:
        result = subprocess.run(
            ["gh", "release", *args, "-R", repo],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"gh release {args[0]} {repo} : {exc.stderr.strip()}"
        ) from exc
    return result.stdout
