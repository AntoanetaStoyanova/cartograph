"""
Manifeste quotidien de la collecte, commité dans ``cartograph-data``.

Lit ``collect-AAAA-MM-JJ.json`` et les fichiers du jour, sans jamais lire de
prix : seulement des statuts, des nombres et des empreintes. Lancé par
``python -m cartograph.bin.collect.manifest`` ; le JSON part sur la sortie
standard.
"""

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from dataclasses import astuple
from datetime import date
from pathlib import Path
from typing import Any

from cartograph.bin.collect import CollectSummary
from cartograph.bin.collect.snapshot import snapshot_paths

_PUBLIC_RELEASE = "cartograph-data/catalogue"


def build_manifest(
    summary: CollectSummary | None,
    data_dir: Path,
    day: str,
    run_id: int,
    repo_kib: int,
) -> dict[str, Any]:
    """
    Construit le manifeste d'une exécution.

    Parameters
    ----------
    summary : CollectSummary | None
        Contenu de ``collect-AAAA-MM-JJ.json``, ``None`` si la collecte n'a
        rien écrit.
    data_dir : Path
        Dossier racine des sorties (voir ``snapshot_paths``).
    day : str
        Jour de la collecte, ``AAAA-MM-JJ``.
    run_id : int
        Identifiant de l'exécution GitHub Actions.
    repo_kib : int
        Taille du dépôt ``cartograph-data`` donnée par GitHub, en Kio.

    Returns
    -------
    dict[str, Any]
        Statut et nombres par étape, fichiers avec Release, lignes, octets et
        SHA-256 (``None`` si le fichier est absent du disque).

    Examples
    --------
    >>> manifest = build_manifest(None, Path("data"), "2026-10-28", 42, 120)
    >>> manifest["summary"], manifest["files"]
    (False, [])
    """
    steps = summary["steps"] if summary else {}
    paths = {
        path.name: path
        for path in astuple(snapshot_paths(data_dir, date.fromisoformat(day)))
    }
    return {
        "date": day,
        "run_id": run_id,
        "repo_kib": repo_kib,
        "summary": summary is not None,
        "steps": {
            name: {
                "status": step["status"],
                "fetched": step["fetched"],
                "failed": len(step["failed"]),
            }
            for name, step in steps.items()
        },
        "files": [
            {
                "name": file["name"],
                "release": _release(file["name"], day),
                "rows": file["rows"],
                "bytes": file["bytes"],
                "sha256": _sha256(paths.get(file["name"])),
            }
            for step in steps.values()
            for file in step["files"]
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    """
    Écrit sur la sortie standard le manifeste JSON d'une exécution.

    Parameters
    ----------
    argv : Sequence[str] | None, optional
        Arguments, par défaut ceux de la ligne de commande.

    Returns
    -------
    int
        Toujours 0.
    """
    parser = argparse.ArgumentParser(
        prog="python -m cartograph.bin.collect.manifest",
        description="Construit le manifeste sans prix d'une collecte.",
    )
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--date", required=True, help="AAAA-MM-JJ")
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--repo-kib", type=int, required=True)
    parser.add_argument("--summary", type=Path, help="collect-AAAA-MM-JJ.json")
    args = parser.parse_args(argv)
    summary = (
        json.loads(args.summary.read_text(encoding="utf-8")) if args.summary else None
    )
    manifest = build_manifest(
        summary, args.data_dir, args.date, args.run_id, args.repo_kib
    )
    sys.stdout.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return 0


def _release(name: str, day: str) -> str:
    """Release où le workflow envoie le fichier, même règle que ``collect.yml``."""
    if name.startswith("cards-") and name.endswith(".parquet"):
        return _PUBLIC_RELEASE
    return f"cartograph-prices/data-{day[:7]}"


def _sha256(path: Path | None) -> str | None:
    """SHA-256 du fichier, ``None`` s'il est inconnu ou absent du disque."""
    if path is None or not path.is_file():
        return None
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


if __name__ == "__main__":
    sys.exit(main())
