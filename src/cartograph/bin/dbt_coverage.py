"""
Couverture des tests dbt, tirée de ``target/manifest.json``.

Liste les colonnes de modèle sans aucun test et les clés (colonnes en ``_id``) sans
test ``relationships``. Un test posé sur une expression du modèle (``unique`` sur
plusieurs colonnes) ne compte pas pour ses colonnes.

Lancé par ``inv couverture-tests`` ou ``python -m cartograph.bin.dbt_coverage`` ; code
de sortie 1 si le manifeste est absent, 0 sinon (le rapport informe, il ne bloque pas).
"""

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cartograph.log import setup_logging

MANIFEST = Path("dbt/target/manifest.json")

# Nom fixe : lancé par `-m`, `__name__` vaut `__main__`, hors du logger `cartograph`.
logger = logging.getLogger("cartograph.bin.dbt_coverage")


@dataclass(frozen=True)
class Coverage:
    """
    Résultat de l'analyse des tests dbt.

    Attributes
    ----------
    untested_columns : list[str]
        Colonnes sans aucun test, au format ``modèle.colonne``, triées.
    keys_without_relationship : list[str]
        Colonnes en ``_id`` sans test ``relationships``, triées.
    column_count : int
        Nombre de colonnes déclarées par les modèles.
    """

    untested_columns: list[str]
    keys_without_relationship: list[str]
    column_count: int


def analyse(manifest: dict[str, Any]) -> Coverage:
    """
    Compte les colonnes de modèle sans test et les clés sans ``relationships``.

    Parameters
    ----------
    manifest : dict[str, Any]
        Contenu de ``manifest.json``.

    Returns
    -------
    Coverage
        Colonnes sans test et clés sans ``relationships``.
    """
    tested: set[tuple[str, str]] = set()
    related: set[tuple[str, str]] = set()
    for node in manifest["nodes"].values():
        column = node.get("column_name")
        if node["resource_type"] != "test" or not column:
            continue
        tested.add((node["attached_node"], column))
        if node["test_metadata"]["name"] == "relationships":
            related.add((node["attached_node"], column))
    untested: list[str] = []
    keys: list[str] = []
    column_count = 0
    for node_id, node in manifest["nodes"].items():
        if node["resource_type"] != "model":
            continue
        for column in node["columns"]:
            column_count += 1
            name = f"{node['name']}.{column}"
            if (node_id, column) not in tested:
                untested.append(name)
            if column.endswith("_id") and (node_id, column) not in related:
                keys.append(name)
    return Coverage(sorted(untested), sorted(keys), column_count)


def main(argv: Sequence[str] | None = None) -> int:
    """
    Écrit le rapport de couverture depuis la ligne de commande.

    Parameters
    ----------
    argv : Sequence[str] | None, optional
        Arguments, par défaut ceux de la ligne de commande.

    Returns
    -------
    int
        0 si le manifeste a été lu, 1 s'il est absent.
    """
    parser = argparse.ArgumentParser(
        prog="python -m cartograph.bin.dbt_coverage",
        description="Colonnes sans test et clés sans relationships.",
    )
    parser.add_argument(
        "--manifest", type=Path, default=MANIFEST, help="manifest.json de dbt"
    )
    args = parser.parse_args(argv)
    setup_logging("cartograph")
    if not args.manifest.is_file():
        logger.error("%s absent : lancer inv dbt d'abord.", args.manifest)
        return 1
    result = analyse(json.loads(args.manifest.read_text()))
    logger.info(
        "%d colonne sur %d sans test : %s",
        len(result.untested_columns),
        result.column_count,
        ", ".join(result.untested_columns) or "aucune",
    )
    logger.info(
        "%d clé sans relationships : %s",
        len(result.keys_without_relationship),
        ", ".join(result.keys_without_relationship) or "aucune",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
