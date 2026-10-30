import hashlib
import json
from pathlib import Path

import pytest

from cartograph.bin.collect.manifest import build_manifest, main
from tests.conftest import (
    PRICE_MARKERS,
    REAL_SUMMARY,
    SUMMARY_DAY,
    make_step,
    make_summary,
)

DAY = SUMMARY_DAY


def _data_dir(tmp_path: Path) -> Path:
    (tmp_path / "snapshots").mkdir()
    (tmp_path / "raw").mkdir()
    (tmp_path / "snapshots" / f"prices-{DAY}.parquet").write_bytes(b"12345")
    (tmp_path / "raw" / f"prices-{DAY}.json.gz").write_bytes(b"abc")
    return tmp_path


def test_successful_collection_lists_files_with_release_and_sha256(
    tmp_path: Path,
) -> None:
    manifest = build_manifest(make_summary(), _data_dir(tmp_path), DAY, 42, 120)

    assert manifest["date"] == DAY
    assert manifest["run_id"] == 42
    assert manifest["repo_kib"] == 120
    assert manifest["summary"] is True
    assert manifest["steps"]["prices"] == {
        "status": "ok",
        "fetched": 18254,
        "failed": 0,
    }
    assert manifest["files"] == [
        {
            "name": f"prices-{DAY}.parquet",
            "release": "cartograph-prices/data-2026-10",
            "rows": 18254,
            "bytes": 550831,
            "sha256": hashlib.sha256(b"12345").hexdigest(),
        },
        {
            "name": f"prices-{DAY}.json.gz",
            "release": "cartograph-prices/data-2026-10",
            "rows": 18254,
            "bytes": 742904,
            "sha256": hashlib.sha256(b"abc").hexdigest(),
        },
    ]


def test_catalogue_parquet_goes_to_public_release(tmp_path: Path) -> None:
    data_dir = _data_dir(tmp_path)
    (data_dir / "snapshots" / f"cards-{DAY}.parquet").write_bytes(b"cards")
    files = [{"name": f"cards-{DAY}.parquet", "rows": 2, "bytes": 5}]
    summary = make_summary(catalogue=make_step(files=files, source=None))

    manifest = build_manifest(summary, data_dir, DAY, 42, 120)

    assert manifest["files"][0]["release"] == "cartograph-data/catalogue"


def test_skipped_step_keeps_its_status(tmp_path: Path) -> None:
    manifest = build_manifest(make_summary(), _data_dir(tmp_path), DAY, 42, 120)

    assert manifest["steps"]["catalogue"] == {
        "status": "skipped",
        "fetched": 0,
        "failed": 0,
    }


def test_failed_step_counts_failures_without_card_ids(tmp_path: Path) -> None:
    prices = make_step(status="failed", failed=["fr/swsh1-1", "fr/swsh1-2"], files=[])

    manifest = build_manifest(
        make_summary(prices=prices), _data_dir(tmp_path), DAY, 42, 120
    )

    assert manifest["steps"]["prices"]["failed"] == 2
    assert "swsh1" not in json.dumps(manifest)


def test_missing_file_has_no_sha256(tmp_path: Path) -> None:
    data_dir = _data_dir(tmp_path)
    (data_dir / "raw" / f"prices-{DAY}.json.gz").unlink()

    manifest = build_manifest(make_summary(), data_dir, DAY, 42, 120)

    assert manifest["files"][1]["sha256"] is None


def test_no_summary_gives_empty_steps_and_files(tmp_path: Path) -> None:
    manifest = build_manifest(None, tmp_path, DAY, 42, 120)

    assert manifest["summary"] is False
    assert manifest["steps"] == {}
    assert manifest["files"] == []


def test_real_summary_contains_no_price(tmp_path: Path) -> None:
    summary = json.loads(REAL_SUMMARY.read_text(encoding="utf-8"))

    text = json.dumps(build_manifest(summary, tmp_path, DAY, 42, 120)).lower()

    for marker in PRICE_MARKERS:
        assert marker not in text


def test_main_writes_sorted_json_to_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data_dir = _data_dir(tmp_path)
    path = tmp_path / f"collect-{DAY}.json"
    path.write_text(json.dumps(make_summary()), encoding="utf-8")
    argv = ["--data-dir", str(data_dir), "--date", DAY, "--run-id", "42"]

    assert main([*argv, "--repo-kib", "120", "--summary", str(path)]) == 0
    out = capsys.readouterr().out
    assert json.loads(out)["files"][0]["sha256"] is not None
    assert out.index('"date"') < out.index('"files"') < out.index('"run_id"')


def test_main_withoutmake_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["--data-dir", str(tmp_path), "--date", DAY, "--run-id", "42"]

    assert main([*argv, "--repo-kib", "120"]) == 0
    assert json.loads(capsys.readouterr().out)["summary"] is False
