from pathlib import Path

import pytest
from invoke import MockContext, Result

from tasks import dbt

BUILD = "uv run dbt build --project-dir dbt --profiles-dir dbt"
DEBUG = "uv run dbt debug --project-dir dbt --profiles-dir dbt"


@pytest.fixture(autouse=True)
def _cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)


def _commands(c: MockContext) -> list[str]:
    return [call.args[0] for call in c.run.call_args_list]


def test_dbt_builds_by_default() -> None:
    c = MockContext(run={BUILD: Result()})
    dbt(c)
    assert _commands(c) == [BUILD]


def test_dbt_runs_given_command() -> None:
    c = MockContext(run={DEBUG: Result()})
    dbt(c, args="debug")
    assert _commands(c) == [DEBUG]


def test_dbt_creates_data_dir(tmp_path: Path) -> None:
    dbt(MockContext(run={BUILD: Result()}))
    assert (tmp_path / "data").is_dir()
