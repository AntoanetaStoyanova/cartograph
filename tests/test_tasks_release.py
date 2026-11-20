import re
from pathlib import Path

import pytest
from invoke import Exit, MockContext, Result

from tasks import LOG_HEADER, _changelog_section, _journal_to_log, release

CI = [
    "uv run pre-commit run --all-files",
    "uv run mypy src/cartograph",
    "uv run pytest",
    "uv run dbt build --exclude tag:donnees_reelles"
    " --vars '{snapshot_dir: dbt/sample/snapshots}'"
    " --project-dir dbt --profiles-dir dbt",
]
DOCS = "uv run sphinx-build -b html docs docs/_build/html"
VERSION = "uv version --short"
GET_NEXT = "uv run cz bump --get-next"
GIT_ADD = "git add .ai-context/JOURNAL.md .ai-context/LOG.md"
GIT_COMMIT = "git commit -m 'chore(journal): archive avant v0.4.0'"
PR_LIST = (
    "gh pr list --base main --head develop --state open --json url --jq '.[0].url'"
)
PR_CREATE = re.compile(
    r"gh pr create --base main --head develop --title 'Release v0\.4\.0' "
    r"--body-file \S+$"
)
PR_URL = "https://github.com/AntoanetaStoyanova/cartograph/pull/14"
LS_FILES = "git ls-files"
CHANGELOG = """## v0.4.0 (2026-11-20)

### Nouveautés

- tâche inv finish

## v0.3.0 (2026-11-15)

### Corrections

- suivi sans exécutions en cours
"""
JOURNAL = """# Journal — cartograph

---

## [2026-11-20] — Session en cours

### Reste à faire

- COL-04

## [2026-11-19] — COL-04 étape 1

## [2026-11-18] — Plan COL-04
"""


@pytest.fixture(autouse=True)
def _changelog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    (tmp_path / ".clean").write_text("docs/_build/\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)


def _context(
    branch: str = "develop", status: str = "", bump_exit: int = 0, pr_url: str = ""
) -> MockContext:
    commands = [
        "git pull --ff-only",
        *CI,
        DOCS,
        "git push --follow-tags",
        GIT_ADD,
        GIT_COMMIT,
    ]
    results = {cmd: Result() for cmd in commands}
    results["git branch --show-current"] = Result(f"{branch}\n")
    results["git status --porcelain"] = Result(status)
    results[GET_NEXT] = Result("0.4.0\n", exited=bump_exit)
    results["uv run cz bump --yes"] = Result(exited=bump_exit)
    results["uv run cz bump --dry-run --yes"] = Result(exited=bump_exit)
    results[VERSION] = Result("0.4.0\n")
    results[PR_LIST] = Result(f"{pr_url}\n")
    results[PR_CREATE] = Result()
    results[LS_FILES] = Result("CHANGELOG.md\n")
    return MockContext(run=results)


def _commands(c: MockContext) -> list[str]:
    return [call.args[0] for call in c.run.call_args_list]


def test_release_runs_checks_bump_docs_push_then_opens_pr() -> None:
    c = _context()
    release(c)
    commands = _commands(c)
    assert commands[-1] == LS_FILES
    assert commands[:-2] == [
        "git branch --show-current",
        "git status --porcelain",
        "git pull --ff-only",
        *CI,
        GET_NEXT,
        "uv run cz bump --yes",
        DOCS,
        "git push --follow-tags",
        VERSION,
        PR_LIST,
    ]
    assert PR_CREATE.match(commands[-2])


def test_release_shows_existing_pr(capsys: pytest.CaptureFixture[str]) -> None:
    c = _context(pr_url=PR_URL)
    release(c)
    assert _commands(c)[-2:] == [PR_LIST, LS_FILES]
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
    assert "uv run cz bump --yes" not in _commands(c)


def test_release_archives_journal_before_bump(tmp_path: Path) -> None:
    journal = tmp_path / ".ai-context" / "JOURNAL.md"
    journal.parent.mkdir()
    journal.write_text(JOURNAL, encoding="utf-8")
    c = _context()
    release(c)
    commands = _commands(c)
    bump = commands.index("uv run cz bump --yes")
    assert commands[bump - 2 : bump] == [GIT_ADD, GIT_COMMIT]
    assert "## [2026-11-19]" not in journal.read_text(encoding="utf-8")
    log = (tmp_path / ".ai-context" / "LOG.md").read_text(encoding="utf-8")
    assert "# v0.4.0 — " in log
    assert "## [2026-11-18] — Plan COL-04" in log


def test_journal_to_log_keeps_most_recent_entry() -> None:
    moved = _journal_to_log(JOURNAL, "", "0.4.0", "2026-11-20")
    assert moved is not None
    journal, log = moved
    assert journal == JOURNAL.split("## [2026-11-19]")[0].rstrip() + "\n"
    assert log == (
        LOG_HEADER + "\n# v0.4.0 — 2026-11-20\n\n## [2026-11-19] — COL-04 étape 1\n\n"
        "## [2026-11-18] — Plan COL-04\n"
    )


def test_journal_to_log_puts_new_version_first() -> None:
    old = LOG_HEADER + "\n# v0.3.1 — 2026-11-16\n\n## [2026-11-16] — CI-02\n"
    moved = _journal_to_log(JOURNAL, old, "0.4.0", "2026-11-20")
    assert moved is not None
    log = moved[1]
    assert log.startswith(LOG_HEADER)
    assert log.index("# v0.4.0") < log.index("# v0.3.1")
    assert log.endswith("## [2026-11-16] — CI-02\n")


def test_journal_to_log_nothing_to_move() -> None:
    only_one = JOURNAL.split("## [2026-11-19]")[0]
    assert _journal_to_log(only_one, "", "0.4.0", "2026-11-20") is None


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
