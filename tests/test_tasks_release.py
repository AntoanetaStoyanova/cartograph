import re
from pathlib import Path

import pytest
from invoke import Exit, MockContext, Result

from tasks import _changelog_section, release

CI = [
    "uv run pre-commit run --all-files",
    "uv run mypy src/cartograph",
    "uv run pytest",
    "uv run dbt build --project-dir dbt --profiles-dir dbt",
]
DOCS = "uv run sphinx-build -b html docs docs/_build/html"
VERSION = "uv version --short"
PR_LIST = (
    "gh pr list --base main --head develop --state open --json url --jq '.[0].url'"
)
PR_CREATE = re.compile(
    r"gh pr create --base main --head develop --title 'Release v0\.4\.0' "
    r"--body-file \S+$"
)
PR_URL = "https://github.com/AntoanetaStoyanova/cartograph/pull/14"
CHANGELOG = """## v0.4.0 (2026-11-20)

### Nouveautés

- tâche inv finish

## v0.3.0 (2026-11-15)

### Corrections

- suivi sans exécutions en cours
"""


@pytest.fixture(autouse=True)
def _changelog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    monkeypatch.chdir(tmp_path)


def _context(
    branch: str = "develop", status: str = "", bump_exit: int = 0, pr_url: str = ""
) -> MockContext:
    commands = [
        "git pull --ff-only",
        *CI,
        DOCS,
        "git push --follow-tags",
    ]
    results = {cmd: Result() for cmd in commands}
    results["git branch --show-current"] = Result(f"{branch}\n")
    results["git status --porcelain"] = Result(status)
    results["uv run cz bump --yes"] = Result(exited=bump_exit)
    results["uv run cz bump --dry-run --yes"] = Result(exited=bump_exit)
    results[VERSION] = Result("0.4.0\n")
    results[PR_LIST] = Result(f"{pr_url}\n")
    results[PR_CREATE] = Result()
    return MockContext(run=results)


def _commands(c: MockContext) -> list[str]:
    return [call.args[0] for call in c.run.call_args_list]


def test_release_runs_checks_bump_docs_push_then_opens_pr() -> None:
    c = _context()
    release(c)
    commands = _commands(c)
    assert commands[:-1] == [
        "git branch --show-current",
        "git status --porcelain",
        "git pull --ff-only",
        *CI,
        "uv run cz bump --yes",
        DOCS,
        "git push --follow-tags",
        VERSION,
        PR_LIST,
    ]
    assert PR_CREATE.match(commands[-1])


def test_release_shows_existing_pr(capsys: pytest.CaptureFixture[str]) -> None:
    c = _context(pr_url=PR_URL)
    release(c)
    assert _commands(c)[-1] == PR_LIST
    assert PR_URL in capsys.readouterr().out


def test_release_refuses_other_branch() -> None:
    c = _context(branch="feature/controle")
    with pytest.raises(Exit, match="develop"):
        release(c)
    assert _commands(c) == ["git branch --show-current"]


def test_release_refuses_dirty_tree() -> None:
    c = _context(status=" M pyproject.toml\n")
    with pytest.raises(Exit, match="propre"):
        release(c)
    assert "git pull --ff-only" not in _commands(c)


def test_release_dry_run_changes_nothing() -> None:
    c = _context()
    release(c, dry_run=True)
    assert _commands(c)[-1] == "uv run cz bump --dry-run --yes"
    assert "git pull --ff-only" not in _commands(c)
    assert "git push --follow-tags" not in _commands(c)
    assert not any(cmd.startswith("gh ") for cmd in _commands(c))


@pytest.mark.parametrize("bump_exit", [3, 21])
def test_release_stops_when_nothing_to_bump(bump_exit: int) -> None:
    c = _context(bump_exit=bump_exit)
    with pytest.raises(Exit, match="Rien à publier"):
        release(c)
    assert "git push --follow-tags" not in _commands(c)


def test_changelog_section_first_version() -> None:
    assert _changelog_section(CHANGELOG, "v0.4.0") == (
        "### Nouveautés\n\n- tâche inv finish"
    )


def test_changelog_section_middle_version() -> None:
    text = "## v0.5.0 (2026-12-01)\n\n- a\n\n" + CHANGELOG
    assert _changelog_section(text, "v0.4.0") == (
        "### Nouveautés\n\n- tâche inv finish"
    )


def test_changelog_section_last_version() -> None:
    assert _changelog_section(CHANGELOG, "v0.3.0") == (
        "### Corrections\n\n- suivi sans exécutions en cours"
    )


def test_changelog_section_missing_version() -> None:
    with pytest.raises(Exit, match="v0.9.0"):
        _changelog_section(CHANGELOG, "v0.9.0")
