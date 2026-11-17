from pathlib import Path

import pytest
from invoke import MockContext, Result

from tasks import ci, dbt

BUILD = "uv run dbt build --project-dir dbt --profiles-dir dbt"
DEBUG = "uv run dbt debug --project-dir dbt --profiles-dir dbt"
SAMPLE_BUILD = (
    "uv run dbt build --vars '{snapshot_dir: dbt/sample/snapshots}'"
    " --project-dir dbt --profiles-dir dbt"
)
SAMPLE_ENV = {"CARTOGRAPH_DUCKDB": "data/cartograph.sample.duckdb"}


@pytest.fixture(autouse=True)
def _cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)


def _commands(c: MockContext) -> list[str]:
    return [call.args[0] for call in c.run.call_args_list]


def test_dbt_builds_by_default() -> None:
    c = MockContext(run={BUILD: Result()})
    dbt(c)
    assert _commands(c) == [BUILD]
    assert "env" not in c.run.call_args.kwargs


def test_dbt_runs_given_command() -> None:
    c = MockContext(run={DEBUG: Result()})
    dbt(c, args="debug")
    assert _commands(c) == [DEBUG]


def test_dbt_creates_data_dir(tmp_path: Path) -> None:
    dbt(MockContext(run={BUILD: Result()}))
    assert (tmp_path / "data").is_dir()


def test_dbt_sample_uses_sample_snapshots_and_database() -> None:
    c = MockContext(run={SAMPLE_BUILD: Result()})
    dbt(c, sample=True)
    assert _commands(c) == [SAMPLE_BUILD]
    assert c.run.call_args.kwargs["env"] == SAMPLE_ENV


def test_ci_runs_dbt_on_sample() -> None:
    dbt_calls = [p for p in ci.pre if getattr(p, "task", p) is dbt]
    assert [p.kwargs for p in dbt_calls] == [{"sample": True}]
