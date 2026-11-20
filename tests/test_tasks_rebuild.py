from pathlib import Path
from typing import Any

import duckdb
import pytest
from invoke import Exit, MockContext, Result, UnexpectedExit

from tasks import rebuild

SYNC = "uv run python -m cartograph.bin.rebuild"
BUILD = "uv run dbt build --project-dir dbt --profiles-dir dbt"
TMP = Path("data/cartograph.rebuild.duckdb")
DB = Path("data/cartograph.duckdb")


@pytest.fixture(autouse=True)
def _cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    DB.parent.mkdir()
    DB.write_bytes(b"old")
    Path(f"{DB}.wal").write_bytes(b"old wal")


def _context(build_exit: int = 0) -> MockContext:
    c = MockContext(run={SYNC: Result(), BUILD: Result(exited=build_exit)})

    def run(command: str, **kwargs: Any) -> Result:
        if command == BUILD:
            Path(kwargs["env"]["CARTOGRAPH_DUCKDB"]).write_bytes(b"new")
        return Result(exited=build_exit if command == BUILD else 0)

    c.run.side_effect = run
    return c


def _commands(c: MockContext) -> list[str]:
    return [call.args[0] for call in c.run.call_args_list]


def test_rebuild_syncs_then_builds_into_temporary_database() -> None:
    c = _context()
    rebuild(c)
    assert _commands(c) == [SYNC, BUILD]
    assert c.run.call_args_list[1].kwargs["env"] == {"CARTOGRAPH_DUCKDB": str(TMP)}


@pytest.mark.regle("R-HIS-05")
def test_rebuild_replaces_database_on_success() -> None:
    rebuild(_context())
    assert DB.read_bytes() == b"new"
    assert not TMP.exists()
    assert not Path(f"{DB}.wal").exists()


def test_rebuild_skip_download() -> None:
    c = _context()
    rebuild(c, skip_download=True)
    assert _commands(c) == [BUILD]


@pytest.mark.regle("R-HIS-02")
@pytest.mark.regle("R-HIS-05")
def test_rebuild_starts_from_empty_database(tmp_path: Path) -> None:
    TMP.write_bytes(b"stale")
    Path(f"{TMP}.wal").write_bytes(b"stale wal")
    c = _context()
    c.run.side_effect = lambda command, **kwargs: Result()
    rebuild(c, skip_download=True)
    with duckdb.connect(DB) as con:
        assert con.sql("select 1").fetchall() == [(1,)]
    assert not Path(f"{TMP}.wal").exists()


@pytest.mark.regle("R-HIS-05")
def test_rebuild_keeps_database_when_dbt_fails() -> None:
    with pytest.raises(Exit, match="inchangée"):
        rebuild(_context(build_exit=1))
    assert DB.read_bytes() == b"old"
    assert Path(f"{DB}.wal").exists()
    assert not TMP.exists()


@pytest.mark.regle("R-HIS-05")
def test_rebuild_stops_before_dbt_when_download_fails() -> None:
    c = _context()

    def run(command: str, **kwargs: Any) -> Result:
        raise UnexpectedExit(Result(command=command, exited=1))

    c.run.side_effect = run

    with pytest.raises(UnexpectedExit):
        rebuild(c)
    assert _commands(c) == [SYNC]
    assert DB.read_bytes() == b"old"
    assert not TMP.exists()
