"""
Snapshots Parquet des Releases GitHub, rapatriés pour reconstruire la base.

Le catalogue est dans la Release ``catalogue`` de ``DATA_REPO``, les prix dans
les Releases ``data-AAAA-MM`` de ``PRICES_REPO`` (privé, lu avec la session
``gh`` locale). Un fichier n'est téléchargé que s'il manque ou si son SHA-256
diffère du ``digest`` donné par GitHub : une collecte relancée le même jour
remplace le fichier du jour sous le même nom.

Lancé par ``inv rebuild`` ou ``python -m cartograph.bin.rebuild`` ; code de
sortie 0 si tous les fichiers sont à jour et vérifiés, 1 sinon.
"""

import argparse
import hashlib
import json
import logging
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from cartograph.config import DATA_DIR, DATA_REPO, LOG_DIR, PRICES_REPO
from cartograph.log import setup_logging

SOURCES: tuple[tuple[str, str], ...] = (
    (DATA_REPO, "catalogue"),
    (PRICES_REPO, "data-"),
)

# Nom fixe : lancé par `-m`, `__name__` vaut `__main__`, hors du logger `cartograph`.
logger = logging.getLogger("cartograph.bin.rebuild")


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


def download(asset: Asset, snapshot_dir: Path) -> None:
    """
    Télécharge un fichier de Release et vérifie son empreinte.

    Parameters
    ----------
    asset : Asset
        Fichier à télécharger.
    snapshot_dir : Path
        Dossier local des snapshots, créé s'il manque ; un fichier du même nom
        est remplacé.

    Raises
    ------
    RuntimeError
        Si ``gh`` échoue, ou si le SHA-256 du fichier reçu diffère de celui de
        la Release.
    """
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    _gh(
        asset.repo,
        "download",
        asset.tag,
        "--pattern",
        asset.name,
        "--dir",
        str(snapshot_dir),
        "--clobber",
    )
    actual = file_sha256(snapshot_dir / asset.name)
    if actual != asset.sha256:
        raise RuntimeError(
            f"{asset.name} : SHA-256 {actual} au lieu de {asset.sha256} ({asset.tag})"
        )


def sync(snapshot_dir: Path, sources: Sequence[tuple[str, str]] = SOURCES) -> int:
    """
    Met le dossier des snapshots à jour avec les Releases.

    Les Parquet locaux absents des Releases sont gardés et signalés.

    Parameters
    ----------
    snapshot_dir : Path
        Dossier local des snapshots.
    sources : Sequence[tuple[str, str]], optional
        Couples (dépôt, préfixe de tag) à rapatrier.

    Returns
    -------
    int
        Nombre de fichiers téléchargés.

    Raises
    ------
    RuntimeError
        Si ``gh`` échoue ou si une empreinte est fausse.
    """
    start = time.monotonic()
    assets = [a for repo, prefix in sources for a in list_assets(repo, prefix)]
    todo = plan_downloads(assets, snapshot_dir)
    for asset in todo:
        logger.info(
            "Téléchargement de %s (%s, %d octets)", asset.name, asset.tag, asset.size
        )
        download(asset, snapshot_dir)
    for path in orphans(assets, snapshot_dir):
        logger.warning("%s absent des Releases, gardé", path.name)
    logger.info(
        "Snapshots à jour : %d fichiers publiés, %d téléchargés en %.1f s",
        len(assets),
        len(todo),
        time.monotonic() - start,
    )
    return len(todo)


def main(argv: Sequence[str] | None = None) -> int:
    """
    Met les snapshots à jour depuis la ligne de commande.

    Parameters
    ----------
    argv : Sequence[str] | None, optional
        Arguments, par défaut ceux de la ligne de commande.

    Returns
    -------
    int
        0 si tous les fichiers sont à jour et vérifiés, 1 sinon.
    """
    parser = argparse.ArgumentParser(
        prog="python -m cartograph.bin.rebuild",
        description="Rapatrie les snapshots Parquet des Releases GitHub.",
    )
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=DATA_DIR / "snapshots",
        help="dossier des snapshots",
    )
    args = parser.parse_args(argv)
    setup_logging("cartograph", log_dir=LOG_DIR)
    try:
        sync(args.snapshot_dir)
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1
    return 0


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


if __name__ == "__main__":
    sys.exit(main())
