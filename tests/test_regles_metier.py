import json
import tomllib
from pathlib import Path
from typing import Any

import pytest

from cartograph.bin import regles_metier
from cartograph.bin.regles_metier import (
    Link,
    Rule,
    check,
    dbt_links,
    main,
    marker_links,
    parse_rules,
)

HEAD = (
    "| ID | Règle | Appliquée dans | Garantie par | Origine |\n"
    "| -- | -- | -- | -- | -- |"
)


def _doc(*rows: str) -> str:
    return "\n".join(["# Règles", "", HEAD, *rows, "", "Fin."])


def _row(rule: str, guarantee: str) -> str:
    return f"| {rule} | texte | code | {guarantee} | LOT-01 |"


def test_parse_rules_reads_tested_and_untested() -> None:
    text = _doc(_row("R-COL-01", "aucun (surveillance)"), _row("R-COL-02", "`a::b`"))
    assert parse_rules(text) == [Rule("R-COL-01", False), Rule("R-COL-02", True)]


def test_parse_rules_keeps_escaped_pipes_in_cell() -> None:
    row = _row("R-CAT-02", "`unique` sur `a \\|\\| '\\|' \\|\\| b`")
    assert parse_rules(_doc(row)) == [Rule("R-CAT-02", True)]


def test_parse_rules_keeps_duplicates() -> None:
    text = _doc(_row("R-COL-01", "aucun"), _row("R-COL-01", "test"))
    assert [r.id for r in parse_rules(text)] == ["R-COL-01", "R-COL-01"]


def test_parse_rules_ignores_other_tables() -> None:
    upcoming = "| Lot | Famille | Règle |\n| --- | --- | --- |\n| DBT-05 | PRX | x |"
    retired = (
        "| ID | Règle | Retirée le | Remplacée par |\n| -- | -- | -- | -- |\n"
        "| R-COL-99 | x | COL-05 | R-COL-02 |"
    )
    text = "\n\n".join([upcoming, retired, _doc(_row("R-COL-02", "test"))])
    assert parse_rules(text) == [Rule("R-COL-02", True)]


def _node(kind: str, name: str, **extra: Any) -> tuple[str, dict[str, Any]]:
    unique_id = f"{kind}.cartograph.{name}"
    node = {"resource_type": kind, "name": name, "columns": {}, "config": {}}
    return unique_id, node | extra


def _generic(model: str, column: str | None) -> tuple[str, dict[str, Any]]:
    unique_id, node = _node("test", f"not_null_{model}_{column}")
    node["attached_node"] = f"model.cartograph.{model}"
    node["column_name"] = column
    return unique_id, node


def _manifest(*nodes: tuple[str, dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {"nodes": dict(nodes), **extra}


def _links(manifest: dict[str, Any]) -> set[tuple[str, str, bool]]:
    return {(link.rule, link.source, link.guarantees) for link in dbt_links(manifest)}


def test_dbt_links_singular_and_unit_tests_guarantee() -> None:
    singular = _node("test", "assert_x", config={"meta": {"regles": ["R-QUA-09"]}})
    unit = {"config": {"meta": {"regles": ["R-QUA-07"]}}}
    manifest = _manifest(singular, unit_tests={"unit_test.c.m.u": unit})
    assert _links(manifest) == {
        ("R-QUA-09", "test.cartograph.assert_x", True),
        ("R-QUA-07", "unit_test.c.m.u", True),
    }


def test_dbt_links_column_needs_a_test_on_that_column() -> None:
    columns = {
        "low": {"meta": {"regles": ["R-QUA-06"]}},
        "high": {"config": {"meta": {"regles": ["R-QUA-06"]}}},
    }
    model = _node("model", "fct", columns=columns)
    manifest = _manifest(model, _generic("fct", "low"))
    assert _links(manifest) == {
        ("R-QUA-06", "model.cartograph.fct.low", True),
        ("R-QUA-06", "model.cartograph.fct.high", False),
    }


def test_dbt_links_model_regles_needs_a_test_not_a_contract() -> None:
    meta = {"meta": {"regles": ["R-CAT-02"]}}
    with_test = _node("model", "a", config=meta)
    contract_only = _node("model", "b", config=meta | {"contract": {"enforced": True}})
    seed = _node("seed", "c", config=meta)
    manifest = _manifest(with_test, contract_only, seed, _generic("a", "id"))
    assert _links(manifest) == {
        ("R-CAT-02", "model.cartograph.a", True),
        ("R-CAT-02", "model.cartograph.b", False),
        ("R-CAT-02", "seed.cartograph.c", False),
    }


def test_dbt_links_regles_contrat_needs_an_enforced_contract() -> None:
    meta = {"meta": {"regles_contrat": ["R-QUA-03"]}}
    enforced = _node("model", "a", config=meta | {"contract": {"enforced": True}})
    tested_only = _node("model", "b", config=meta)
    manifest = _manifest(enforced, tested_only, _generic("b", "id"))
    assert _links(manifest) == {
        ("R-QUA-03", "model.cartograph.a", True),
        ("R-QUA-03", "model.cartograph.b", False),
    }


def test_dbt_links_rejects_regles_that_is_not_a_list() -> None:
    model = _node("model", "a", config={"meta": {"regles": "R-HIS-03"}})
    with pytest.raises(ValueError, match="liste"):
        dbt_links(_manifest(model))


RULES = [Rule("R-COL-01", False), Rule("R-COL-02", True)]


def test_check_without_gap() -> None:
    assert check(RULES, [Link("R-COL-02", "t", True)]) == []


def test_check_unknown_rule() -> None:
    gaps = check(RULES, [Link("R-COL-02", "t", True), Link("R-COL-99", "u", True)])
    assert gaps == ["u : cite R-COL-99, absente du document"]


def test_check_tested_rule_without_test() -> None:
    assert check(RULES, [Link("R-COL-02", "col", False)]) == [
        "R-COL-02 : marquée testée, aucun test ne la cite",
        "col : cite R-COL-02 sans test ni contrat",
    ]


def test_check_untested_rule_with_test() -> None:
    links = [Link("R-COL-02", "t", True), Link("R-COL-01", "b", True)]
    assert check(RULES, links + [Link("R-COL-01", "a", True)]) == [
        "R-COL-01 : marquée sans test, citée par a, b"
    ]


def test_check_duplicate_rule() -> None:
    gaps = check([*RULES, Rule("R-COL-02", True)], [Link("R-COL-02", "t", True)])
    assert gaps == ["R-COL-02 : déclarée plusieurs fois dans le document"]


def test_marker_links_reads_regle_markers(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        "import pytest\n"
        "pytestmark = pytest.mark.regle('R-COL-01')\n"
        "@pytest.mark.regle('R-COL-02', 'R-COL-03')\n"
        "def test_a(): pass\n"
        "def test_b(): pass\n"
    )
    links = marker_links(tests, tmp_path / "out.json")
    assert {(link.rule, link.source.split("::")[-1]) for link in links} == {
        ("R-COL-01", "test_a"),
        ("R-COL-01", "test_b"),
        ("R-COL-02", "test_a"),
        ("R-COL-03", "test_a"),
    }
    assert all(link.guarantees for link in links)


def test_marker_links_rejects_malformed_identifier(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_sample.py").write_text(
        "import pytest\n@pytest.mark.regle('COL-02')\ndef test_a(): pass\n"
    )
    with pytest.raises(RuntimeError, match="R-XXX-nn"):
        marker_links(tests, tmp_path / "out.json")


def _project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rule: str = "R-COL-02"
) -> list[str]:
    document = tmp_path / "regles.md"
    document.write_text(_doc(_row("R-COL-02", "test_a")))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(_manifest()))
    monkeypatch.setattr(
        regles_metier, "marker_links", lambda *_: [Link(rule, "test_a", True)]
    )
    return ["--regles", str(document), "--manifest", str(manifest)]


def test_main_returns_zero_without_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert main(_project(tmp_path, monkeypatch)) == 0


def test_main_returns_one_and_logs_each_gap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("ERROR")
    assert main(_project(tmp_path, monkeypatch, "R-COL-99")) == 1
    assert "cite R-COL-99, absente du document" in caplog.text
    assert "R-COL-02 : marquée testée" in caplog.text


def test_main_returns_one_when_manifest_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    args = _project(tmp_path, monkeypatch)
    (tmp_path / "manifest.json").unlink()
    assert main(args) == 1


def test_main_returns_one_when_collection_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    args = _project(tmp_path, monkeypatch)

    def fail(*_: object) -> list[Link]:
        raise RuntimeError("collecte en échec")

    monkeypatch.setattr(regles_metier, "marker_links", fail)
    assert main(args) == 1


def test_pytest_config_registers_regle_and_rejects_unknown_markers() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    options = config["tool"]["pytest"]["ini_options"]
    assert "--strict-markers" in options["addopts"]
    assert any(marker.startswith("regle(") for marker in options["markers"])
