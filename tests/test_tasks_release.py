import pytest
from invoke import Exit, MockContext, Result

from tasks import release

CI = [
    "uv run pre-commit run --all-files",
    "uv run mypy src/cartograph",
    "uv run pytest",
]
DOCS = "uv run sphinx-build -b html docs docs/_build/html"


def _context(
    branch: str = "develop", status: str = "", bump_exit: int = 0
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
    return MockContext(run=results)


def _commands(c: MockContext) -> list[str]:
    return [call.args[0] for call in c.run.call_args_list]


def test_release_runs_checks_bump_docs_then_push() -> None:
    c = _context()
    release(c)
    assert _commands(c) == [
        "git branch --show-current",
        "git status --porcelain",
        "git pull --ff-only",
        *CI,
        "uv run cz bump --yes",
        DOCS,
        "git push --follow-tags",
    ]


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


@pytest.mark.parametrize("bump_exit", [3, 21])
def test_release_stops_when_nothing_to_bump(bump_exit: int) -> None:
    c = _context(bump_exit=bump_exit)
    with pytest.raises(Exit, match="Rien à publier"):
        release(c)
    assert "git push --follow-tags" not in _commands(c)
