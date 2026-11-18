from pathlib import Path

import pytest
from invoke import Exit, MockContext, Result

from tasks import _bumps_version, _touches_code, finish

CHECKS = [
    "uv run pre-commit run --all-files",
    "uv run mypy src/cartograph",
    "uv run pytest",
    "uv run dbt build --vars '{snapshot_dir: dbt/sample/snapshots}'"
    " --project-dir dbt --profiles-dir dbt",
    "uv run okflint validate --manifest okf-base.yaml",
]
PUSH = "git push -u origin HEAD"
PR_VIEW = "gh pr view --json url --jq .url"
PR_CREATE = "gh pr create --base develop --fill"
PR_URL = "https://github.com/AntoanetaStoyanova/cartograph/pull/13"
DIFF = "git diff --name-only origin/develop...HEAD"
LOG = "git log --format=%s origin/develop..HEAD"


@pytest.fixture(autouse=True)
def _cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)


def _context(
    branch: str = "feature/ci-01",
    status: str = "",
    pr_url: str = "",
    changed: str = "docs/index.md\n",
    subjects: str = "docs: guide\n",
) -> MockContext:
    results = {cmd: Result() for cmd in [*CHECKS, PUSH, PR_CREATE]}
    results["git branch --show-current"] = Result(f"{branch}\n")
    results["git status --porcelain"] = Result(status)
    results[DIFF] = Result(changed)
    results[LOG] = Result(subjects)
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
        DIFF,
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


def _answer(monkeypatch: pytest.MonkeyPatch, answer: str) -> list[str]:
    prompts: list[str] = []

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return answer

    monkeypatch.setattr("builtins.input", fake_input)
    return prompts


@pytest.mark.parametrize("answer", ["n", "", "N"])
def test_finish_stops_on_code_without_version_bump(
    monkeypatch: pytest.MonkeyPatch, answer: str
) -> None:
    prompts = _answer(monkeypatch, answer)
    c = _context(changed="dbt/models/mart.sql\n", subjects="docs: modèle\n")
    with pytest.raises(Exit, match="Aucun push"):
        finish(c)
    assert len(prompts) == 1
    assert PUSH not in _commands(c)
    assert CHECKS[0] not in _commands(c)


def test_finish_continues_after_confirmation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _answer(monkeypatch, "o")
    c = _context(changed="src/cartograph/a.py\n", subjects="docs: un\nchore: deux\n")
    finish(c)
    assert PUSH in _commands(c)
    out = capsys.readouterr().out
    assert "docs: un" in out and "chore: deux" in out


def test_finish_does_not_ask_with_feat(monkeypatch: pytest.MonkeyPatch) -> None:
    prompts = _answer(monkeypatch, "n")
    c = _context(changed="tasks/__init__.py\n", subjects="docs: a\nfeat: b\n")
    finish(c)
    assert prompts == []
    assert PUSH in _commands(c)


def test_finish_does_not_ask_for_docs_only(monkeypatch: pytest.MonkeyPatch) -> None:
    prompts = _answer(monkeypatch, "n")
    c = _context()
    finish(c)
    assert prompts == []
    assert LOG not in _commands(c)


@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        ("feat: x", True),
        ("fix(collect): x", True),
        ("feat(dbt)!: x", True),
        ("refactor!: x", True),
        ("perf: x", True),
        ("docs: x", False),
        ("chore(journal): x", False),
        ("feature: x", False),
        ("Merge branch 'develop'", False),
    ],
)
def test_bumps_version(subject: str, expected: bool) -> None:
    assert _bumps_version([subject]) is expected


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("src/cartograph/a.py", True),
        ("tasks/__init__.py", True),
        ("dbt/models/mart/x.sql", True),
        ("dbt/macros/m.sql", True),
        ("dbt/sample/snapshots/x.parquet", False),
        ("tests/test_a.py", False),
        ("CONTRIBUTING.md", False),
    ],
)
def test_touches_code(path: str, expected: bool) -> None:
    assert _touches_code([path]) is expected
