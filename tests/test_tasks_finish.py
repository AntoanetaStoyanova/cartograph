import pytest
from invoke import Exit, MockContext, Result

from tasks import finish

CHECKS = [
    "uv run pre-commit run --all-files",
    "uv run mypy src/cartograph",
    "uv run pytest",
    "uv run okflint validate --manifest okf-base.yaml",
]
PUSH = "git push -u origin HEAD"
PR_VIEW = "gh pr view --json url --jq .url"
PR_CREATE = "gh pr create --base develop --fill"
PR_URL = "https://github.com/AntoanetaStoyanova/cartograph/pull/13"


def _context(
    branch: str = "feature/ci-01", status: str = "", pr_url: str = ""
) -> MockContext:
    results = {cmd: Result() for cmd in [*CHECKS, PUSH, PR_CREATE]}
    results["git branch --show-current"] = Result(f"{branch}\n")
    results["git status --porcelain"] = Result(status)
    results[PR_VIEW] = Result(f"{pr_url}\n") if pr_url else Result(exited=1)
    return MockContext(run=results)


def _commands(c: MockContext) -> list[str]:
    return [call.args[0] for call in c.run.call_args_list]


def test_finish_checks_pushes_then_opens_pr() -> None:
    c = _context()
    finish(c)
    assert _commands(c) == [
        "git branch --show-current",
        "git status --porcelain",
        *CHECKS,
        PUSH,
        PR_VIEW,
        PR_CREATE,
    ]


def test_finish_shows_existing_pr(capsys: pytest.CaptureFixture[str]) -> None:
    c = _context(pr_url=PR_URL)
    finish(c)
    assert PR_CREATE not in _commands(c)
    assert PR_URL in capsys.readouterr().out


@pytest.mark.parametrize("branch", ["develop", "main", "ci-01"])
def test_finish_refuses_non_feature_branch(branch: str) -> None:
    c = _context(branch=branch)
    with pytest.raises(Exit, match="feature/"):
        finish(c)
    assert _commands(c) == ["git branch --show-current"]


def test_finish_refuses_dirty_tree() -> None:
    c = _context(status=" M tasks/__init__.py\n")
    with pytest.raises(Exit, match="propre"):
        finish(c)
    assert PUSH not in _commands(c)
