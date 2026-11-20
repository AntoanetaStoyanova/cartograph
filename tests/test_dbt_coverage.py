import json
from pathlib import Path
from typing import Any

import pytest

from cartograph.bin.dbt_coverage import Coverage, analyse, main


def _model(name: str, columns: list[str]) -> dict[str, Any]:
    return {
        "resource_type": "model",
        "name": name,
        "columns": {column: {"name": column} for column in columns},
    }


def _test(model: str, column: str | None, kind: str = "not_null") -> dict[str, Any]:
    return {
        "resource_type": "test",
        "attached_node": f"model.cartograph.{model}",
        "column_name": column,
        "test_metadata": {"name": kind},
    }


def _manifest(*nodes: tuple[str, dict[str, Any]]) -> dict[str, Any]:
    return {"nodes": dict(nodes)}


def test_analyse_lists_columns_without_test() -> None:
    manifest = _manifest(
        ("model.cartograph.dim", _model("dim", ["a", "b"])),
        ("test.1", _test("dim", "a")),
    )
    assert analyse(manifest).untested_columns == ["dim.b"]
    assert analyse(manifest).column_count == 2


def test_analyse_counts_any_test_kind_on_a_column() -> None:
    manifest = _manifest(
        ("model.cartograph.dim", _model("dim", ["a"])),
        ("test.1", _test("dim", "a", "accepted_values")),
    )
    assert analyse(manifest).untested_columns == []


def test_analyse_ignores_model_level_and_singular_tests() -> None:
    manifest = _manifest(
        ("model.cartograph.dim", _model("dim", ["a"])),
        ("test.1", _test("dim", None, "unique")),
        ("test.2", {"resource_type": "test", "column_name": None}),
    )
    assert analyse(manifest).untested_columns == ["dim.a"]


def test_analyse_lists_keys_without_relationships() -> None:
    manifest = _manifest(
        ("model.cartograph.fct", _model("fct", ["product_id", "set_id", "label"])),
        ("test.1", _test("fct", "product_id", "relationships")),
        ("test.2", _test("fct", "set_id", "not_null")),
    )
    assert analyse(manifest).keys_without_relationship == ["fct.set_id"]


def test_analyse_skips_other_resources() -> None:
    manifest = _manifest(
        ("seed.cartograph.levels", {"resource_type": "seed", "columns": {"x": {}}}),
    )
    assert analyse(manifest) == Coverage([], [], 0)


def test_analyse_sorts_names() -> None:
    manifest = _manifest(
        ("model.cartograph.b", _model("b", ["z", "a"])),
        ("model.cartograph.a", _model("a", ["m"])),
    )
    assert analyse(manifest).untested_columns == ["a.m", "b.a", "b.z"]


def test_main_reports_counts(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            _manifest(
                ("model.cartograph.dim", _model("dim", ["a", "b_id"])),
                ("test.1", _test("dim", "a")),
            )
        )
    )
    with caplog.at_level("INFO", logger="cartograph.bin.dbt_coverage"):
        assert main(["--manifest", str(path)]) == 0
    assert "1 colonne sur 2 sans test" in caplog.text
    assert "dim.b_id" in caplog.text
    assert "1 clé sans relationships" in caplog.text


def test_main_fails_without_manifest(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    assert main(["--manifest", str(tmp_path / "none.json")]) == 1
    assert "inv dbt" in caplog.text
