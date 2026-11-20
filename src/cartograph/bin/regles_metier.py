"""
Traçabilité des règles métier : lien entre ``regles-metier.md`` et les tests.

Lit les règles du document, les identifiants cités par dbt (``meta: regles`` du
manifeste) et par pytest (marqueur ``regle``), puis liste les écarts : règle citée
mais absente du document, règle « testée » sans test, règle « sans test » avec un test,
identifiant déclaré deux fois.

Lancé par ``inv regles`` ou ``python -m cartograph.bin.regles_metier`` ; code de sortie
1 au moindre écart. Le module est aussi le plugin pytest de la collecte des marqueurs.
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from cartograph.log import setup_logging

RULES = Path("docs/gouvernance/regles-metier.md")
MANIFEST = Path("dbt/target/manifest.json")
TESTS = Path("tests")
OUTPUT_ENV = "CARTOGRAPH_REGLES_OUT"
RULE_ID = re.compile(r"R-[A-Z]{3}-\d{2}")
_CELL_SPLIT = re.compile(r"(?<!\\)\|")

# Nom fixe : lancé par `-m`, `__name__` vaut `__main__`, hors du logger `cartograph`.
logger = logging.getLogger("cartograph.bin.regles_metier")


@dataclass(frozen=True)
class Rule:
    """
    Règle du document.

    Attributes
    ----------
    id : str
        Identifiant ``R-<FAMILLE>-<nn>``.
    tested : bool
        Faux quand « Garantie par » commence par « aucun ».
    """

    id: str
    tested: bool


@dataclass(frozen=True)
class Link:
    """
    Règle citée par un test ou par un objet dbt.

    Attributes
    ----------
    rule : str
        Identifiant cité.
    source : str
        Test pytest, identifiant dbt ou ``identifiant.colonne``.
    guarantees : bool
        Vrai si la source est un test, ou porte un test (colonne, modèle, seed).
    """

    rule: str
    source: str
    guarantees: bool


def parse_rules(text: str) -> list[Rule]:
    """
    Lit les règles des tables dont la quatrième colonne est « Garantie par ».

    Parameters
    ----------
    text : str
        Contenu de ``regles-metier.md``.

    Returns
    -------
    list[Rule]
        Règles dans l'ordre du document, doublons compris.

    Examples
    --------
    >>> head = "| ID | Règle | Dans | Garantie par | Origine |"
    >>> parse_rules(head + "\\n| R-COL-01 | a | b | aucun | c |")
    [Rule(id='R-COL-01', tested=False)]
    """
    rules: list[Rule] = []
    in_rules_table = False
    for line in text.splitlines():
        if not line.startswith("|"):
            in_rules_table = False
            continue
        cells = [cell.strip() for cell in _CELL_SPLIT.split(line)[1:-1]]
        if cells and cells[0] == "ID":
            in_rules_table = len(cells) > 3 and cells[3] == "Garantie par"
        elif in_rules_table and len(cells) > 3 and RULE_ID.fullmatch(cells[0]):
            rules.append(Rule(cells[0], not cells[3].lower().startswith("aucun")))
    return rules


def _regles(entry: dict[str, Any], label: str) -> list[str]:
    """Lit la liste ``regles`` du ``meta`` d'un objet du manifeste."""
    meta = {**(entry.get("meta") or {}), **(entry.get("config", {}).get("meta") or {})}
    value = meta.get("regles", [])
    if not isinstance(value, list) or not all(isinstance(r, str) for r in value):
        raise ValueError(f"{label} : `regles` doit être une liste d'identifiants")
    return value


def dbt_links(manifest: dict[str, Any]) -> list[Link]:
    """
    Liste les règles citées par ``meta: regles`` dans le manifeste dbt.

    Un test unitaire, singulier ou générique garantit la règle qu'il cite. Un modèle,
    une colonne ou un seed la garantit seulement s'il a un test générique à son niveau
    (pour un modèle : un test sur le modèle ou l'une de ses colonnes, ou son contrat).

    Parameters
    ----------
    manifest : dict[str, Any]
        Contenu de ``manifest.json``.

    Returns
    -------
    list[Link]
        Une entrée par règle citée.

    Raises
    ------
    ValueError
        Si ``regles`` n'est pas une liste de textes.
    """
    nodes: dict[str, dict[str, Any]] = manifest["nodes"]
    tested: dict[str, set[str | None]] = defaultdict(set)
    for node in nodes.values():
        if node["resource_type"] == "test" and node.get("attached_node"):
            tested[node["attached_node"]].add(node.get("column_name"))
    links: list[Link] = []
    for node_id, node in nodes.items():
        kind = node["resource_type"]
        if kind == "test":
            links += [Link(r, node_id, True) for r in _regles(node, node_id)]
        elif kind in ("model", "seed"):
            contract = kind == "model" and node["config"].get("contract", {}).get(
                "enforced", False
            )
            guaranteed = bool(tested[node_id]) or bool(contract)
            links += [Link(r, node_id, guaranteed) for r in _regles(node, node_id)]
            for column, entry in node["columns"].items():
                label = f"{node_id}.{column}"
                links += [
                    Link(r, label, column in tested[node_id])
                    for r in _regles(entry, label)
                ]
    for unit_id, unit in manifest.get("unit_tests", {}).items():
        links += [Link(r, unit_id, True) for r in _regles(unit, unit_id)]
    return links


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Écrit dans ``$CARTOGRAPH_REGLES_OUT`` les règles de chaque test collecté."""
    found: dict[str, list[str]] = {}
    for item in items:
        for marker in item.iter_markers("regle"):
            for rule in marker.args:
                if not isinstance(rule, str) or not RULE_ID.fullmatch(rule):
                    raise pytest.UsageError(
                        f"{item.nodeid} : `regle` attend R-XXX-nn, reçu {rule!r}"
                    )
                found.setdefault(item.nodeid, []).append(rule)
    Path(os.environ[OUTPUT_ENV]).write_text(json.dumps(found), encoding="utf-8")


def marker_links(tests_dir: Path, output: Path) -> list[Link]:
    """
    Liste les règles citées par le marqueur ``regle`` des tests de ``tests_dir``.

    Parameters
    ----------
    tests_dir : Path
        Dossier des tests, collecté par un pytest dans un sous-processus.
    output : Path
        Fichier JSON temporaire écrit par le plugin.

    Returns
    -------
    list[Link]
        Une entrée par règle citée.

    Raises
    ------
    RuntimeError
        Si la collecte échoue ; le message reprend la fin de sa sortie.
    """
    command = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "-p",
        "cartograph.bin.regles_metier",
        "-p",
        "no:cacheprovider",
        "-o",
        "addopts=",
        str(tests_dir),
    ]
    result = subprocess.run(
        command,
        env={**os.environ, OUTPUT_ENV: str(output)},
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        tail = "\n".join((result.stdout + result.stderr).splitlines()[-15:])
        raise RuntimeError(f"collecte pytest en échec :\n{tail}")
    found: dict[str, list[str]] = json.loads(output.read_text(encoding="utf-8"))
    return [Link(r, test, True) for test, rules in found.items() for r in rules]


def check(rules: Sequence[Rule], links: Sequence[Link]) -> list[str]:
    """
    Compare les règles du document aux règles citées par les tests.

    Parameters
    ----------
    rules : Sequence[Rule]
        Règles du document.
    links : Sequence[Link]
        Règles citées par dbt et pytest.

    Returns
    -------
    list[str]
        Un message par écart, triés ; vide si tout concorde.
    """
    gaps: list[str] = []
    known: dict[str, Rule] = {}
    for rule in rules:
        if rule.id in known:
            gaps.append(f"{rule.id} : déclarée plusieurs fois dans le document")
        known.setdefault(rule.id, rule)
    guarantors: dict[str, set[str]] = defaultdict(set)
    for link in links:
        if link.rule not in known:
            gaps.append(f"{link.source} : cite {link.rule}, absente du document")
        elif link.guarantees:
            guarantors[link.rule].add(link.source)
    for rule in known.values():
        if rule.tested and not guarantors[rule.id]:
            gaps.append(f"{rule.id} : marquée testée, aucun test ne la cite")
        elif not rule.tested and guarantors[rule.id]:
            sources = ", ".join(sorted(guarantors[rule.id]))
            gaps.append(f"{rule.id} : marquée sans test, citée par {sources}")
    return sorted(gaps)


def main(argv: Sequence[str] | None = None) -> int:
    """
    Écrit les écarts de traçabilité depuis la ligne de commande.

    Parameters
    ----------
    argv : Sequence[str] | None, optional
        Arguments, par défaut ceux de la ligne de commande.

    Returns
    -------
    int
        0 sans écart, 1 au moindre écart, fichier absent ou collecte en échec.
    """
    parser = argparse.ArgumentParser(
        prog="python -m cartograph.bin.regles_metier",
        description="Lien entre regles-metier.md et les tests dbt et pytest.",
    )
    parser.add_argument("--regles", type=Path, default=RULES, help="regles-metier.md")
    parser.add_argument(
        "--manifest", type=Path, default=MANIFEST, help="manifest.json de dbt"
    )
    parser.add_argument("--tests", type=Path, default=TESTS, help="dossier pytest")
    args = parser.parse_args(argv)
    setup_logging("cartograph")
    for path in (args.regles, args.manifest):
        if not path.is_file():
            logger.error("%s absent (pour le manifeste : lancer inv regles).", path)
            return 1
    rules = parse_rules(args.regles.read_text(encoding="utf-8"))
    try:
        links = dbt_links(json.loads(args.manifest.read_text(encoding="utf-8")))
        with tempfile.TemporaryDirectory() as directory:
            links += marker_links(args.tests, Path(directory) / "regles.json")
    except (ValueError, RuntimeError) as error:
        logger.error("%s", error)
        return 1
    gaps = check(rules, links)
    for gap in gaps:
        logger.error(gap)
    logger.info("%d règle, %d citation, %d écart.", len(rules), len(links), len(gaps))
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main())
