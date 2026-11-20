import hashlib
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

import pytest

from cartograph.bin import rebuild
from cartograph.bin.rebuild import Asset, list_assets, orphans, plan_downloads

REPO = "AntoanetaStoyanova/cartograph-prices"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def asset(name: str, data: bytes = b"x", tag: str = "data-2026-11") -> Asset:
    return Asset(REPO, tag, name, len(data), sha(data))


def fake_gh(
    monkeypatch: pytest.MonkeyPatch, outputs: dict[str, Any], fail: bool = False
) -> list[list[str]]:
    calls: list[list[str]] = []

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if fail:
            raise subprocess.CalledProcessError(1, args, stderr="HTTP 404\n")
        key = args[3] if args[2] == "view" else "list"
        return subprocess.CompletedProcess(args, 0, stdout=outputs[key])

    monkeypatch.setattr(rebuild.subprocess, "run", run)
    return calls


def gh_asset(name: str, digest: str = "sha256:ab12") -> dict[str, Any]:
    return {"name": name, "size": 3, "digest": digest}


def test_list_assets_keeps_parquet_of_matching_releases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = fake_gh(
        monkeypatch,
        {
            "list": "data-2026-11\ncatalogue-old\ndata-2026-10\n",
            "data-2026-11": json.dumps(
                {
                    "assets": [
                        gh_asset("prices-2026-11-01.parquet"),
                        gh_asset("prices-2026-11-01.json.gz"),
                    ]
                }
            ),
            "data-2026-10": json.dumps(
                {"assets": [gh_asset("prices-2026-10-31.parquet", "sha256:cd34")]}
            ),
        },
    )
    assert list_assets(REPO, "data-") == [
        Asset(REPO, "data-2026-11", "prices-2026-11-01.parquet", 3, "ab12"),
        Asset(REPO, "data-2026-10", "prices-2026-10-31.parquet", 3, "cd34"),
    ]
    assert [c[3] for c in calls[1:]] == ["data-2026-11", "data-2026-10"]
    assert all("-R" in c and REPO in c for c in calls)


def test_list_assets_names_repo_when_gh_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_gh(monkeypatch, {}, fail=True)
    with pytest.raises(RuntimeError, match=f"{REPO}.*HTTP 404"):
        list_assets(REPO, "data-")


def test_plan_downloads_missing_and_changed(tmp_path: Path) -> None:
    (tmp_path / "same.parquet").write_bytes(b"same")
    (tmp_path / "changed.parquet").write_bytes(b"old")
    assets = [
        asset("missing.parquet"),
        asset("same.parquet", b"same"),
        asset("changed.parquet", b"new"),
    ]
    assert [a.name for a in plan_downloads(assets, tmp_path)] == [
        "missing.parquet",
        "changed.parquet",
    ]


def test_plan_downloads_missing_dir(tmp_path: Path) -> None:
    assets = [asset("a.parquet")]
    assert plan_downloads(assets, tmp_path / "absent") == assets


def test_orphans_lists_local_parquet_absent_from_releases(tmp_path: Path) -> None:
    for name in ("kept.parquet", "local.parquet", "raw.json.gz"):
        (tmp_path / name).write_bytes(b"x")
    assert orphans([asset("kept.parquet")], tmp_path) == [tmp_path / "local.parquet"]


def test_orphans_missing_dir(tmp_path: Path) -> None:
    assert orphans([], tmp_path / "absent") == []


def fake_download(
    monkeypatch: pytest.MonkeyPatch, content: dict[str, bytes]
) -> list[list[str]]:
    calls: list[list[str]] = []

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        name, folder = args[args.index("--pattern") + 1], args[args.index("--dir") + 1]
        (Path(folder) / name).write_bytes(content[name])
        return subprocess.CompletedProcess(args, 0, stdout="")

    monkeypatch.setattr(rebuild.subprocess, "run", run)
    return calls


def test_download_fetches_with_clobber_and_checks_sha(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = fake_download(monkeypatch, {"a.parquet": b"good"})
    folder = tmp_path / "snapshots"
    rebuild.download(asset("a.parquet", b"good"), folder)
    assert calls == [
        [
            "gh", "release", "download", "data-2026-11",
            "--pattern", "a.parquet", "--dir", str(folder), "--clobber",
            "-R", REPO,
        ]
    ]  # fmt: skip
    assert (folder / "a.parquet").read_bytes() == b"good"


@pytest.mark.regle("R-HIS-04")
def test_download_rejects_wrong_sha(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_download(monkeypatch, {"a.parquet": b"corrupt"})
    with pytest.raises(RuntimeError, match=r"a\.parquet"):
        rebuild.download(asset("a.parquet", b"good"), tmp_path)


def stub_sync(monkeypatch: pytest.MonkeyPatch, assets: list[Asset]) -> list[str]:
    downloaded: list[str] = []

    def download(a: Asset, folder: Path) -> None:
        downloaded.append(a.name)
        (folder / a.name).write_bytes(b"new")

    monkeypatch.setattr(rebuild, "list_assets", lambda repo, prefix: assets)
    monkeypatch.setattr(rebuild, "download", download)
    return downloaded


@pytest.mark.regle("R-HIS-04")
def test_sync_downloads_only_missing_or_changed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    (tmp_path / "same.parquet").write_bytes(b"new")
    (tmp_path / "changed.parquet").write_bytes(b"old")
    (tmp_path / "local.parquet").write_bytes(b"x")
    assets = [
        asset("same.parquet", b"new"),
        asset("changed.parquet", b"new"),
        asset("missing.parquet", b"new"),
    ]
    downloaded = stub_sync(monkeypatch, assets)
    with caplog.at_level(logging.INFO, logger="cartograph"):
        count = rebuild.sync(tmp_path, sources=[(REPO, "data-")])
    assert downloaded == ["changed.parquet", "missing.parquet"]
    assert count == 2
    assert "local.parquet absent des Releases" in caplog.text
    assert "3 fichiers publiés, 2 téléchargés" in caplog.text


def test_sync_second_run_downloads_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    downloaded = stub_sync(monkeypatch, [asset("a.parquet", b"new")])
    rebuild.sync(tmp_path, sources=[(REPO, "data-")])
    assert rebuild.sync(tmp_path, sources=[(REPO, "data-")]) == 0
    assert downloaded == ["a.parquet"]


@pytest.mark.usefixtures("isolated_logs")
def test_main_returns_0_on_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(rebuild, "sync", lambda folder: 0)
    assert rebuild.main(["--snapshot-dir", str(tmp_path)]) == 0


@pytest.mark.usefixtures("isolated_logs")
def test_main_returns_1_and_logs_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail(folder: Path) -> int:
        raise RuntimeError("gh release list cartograph-prices : HTTP 404")

    monkeypatch.setattr(rebuild, "sync", fail)
    assert rebuild.main(["--snapshot-dir", str(tmp_path)]) == 1
    assert "cartograph-prices : HTTP 404" in caplog.text
