import pytest
from invoke import Exit, MockContext, Result

from tasks import clean_branches, delete_branch

BRANCH = "feature/col-04-sets"
CURRENT = "git branch --show-current"
LIST = "git for-each-ref --format=%(refname:short) refs/heads/"
FETCH = "git fetch --prune"


def _merged(branch: str) -> str:
    return f"gh pr list --head {branch} --state merged --json number --jq length"


def _remote(branch: str) -> str:
    return f"git ls-remote --heads origin {branch}"


def _context(
    current: str = "feature/ci-03",
    branches: tuple[str, ...] = ("develop", "main", "feature/ci-03", BRANCH),
    merged: tuple[str, ...] = (BRANCH,),
    remote: tuple[str, ...] = (BRANCH,),
) -> MockContext:
    results = {CURRENT: Result(f"{current}\n"), LIST: Result("\n".join(branches))}
    results[FETCH] = Result()
    for branch in branches:
        results[_merged(branch)] = Result("1\n" if branch in merged else "0\n")
        results[_remote(branch)] = Result(
            f"abc\trefs/heads/{branch}\n" if branch in remote else ""
        )
        results[f"git branch -D {branch}"] = Result()
        results[f"git push origin --delete {branch}"] = Result()
    return MockContext(run=results)


def _commands(c: MockContext) -> list[str]:
    return [call.args[0] for call in c.run.call_args_list]


def _answer(monkeypatch: pytest.MonkeyPatch, answer: str) -> None:
    monkeypatch.setattr("builtins.input", lambda _: answer)


def test_delete_branch_removes_local_and_remote() -> None:
    c = _context()
    delete_branch(c, BRANCH)
    assert _commands(c)[-4:] == [
        f"git branch -D {BRANCH}",
        _remote(BRANCH),
        f"git push origin --delete {BRANCH}",
        FETCH,
    ]


def test_delete_branch_absent_from_origin_skips_push() -> None:
    c = _context(remote=())
    delete_branch(c, BRANCH)
    assert f"git push origin --delete {BRANCH}" not in _commands(c)
    assert f"git branch -D {BRANCH}" in _commands(c)


@pytest.mark.parametrize("branch", ["main", "develop"])
@pytest.mark.parametrize("force", [False, True])
def test_delete_branch_refuses_protected(branch: str, force: bool) -> None:
    c = _context(merged=("main", "develop"))
    with pytest.raises(Exit, match="protégée"):
        delete_branch(c, branch, force=force)
    assert not any("git branch -D" in cmd for cmd in _commands(c))


def test_delete_branch_refuses_current() -> None:
    c = _context(current=BRANCH)
    with pytest.raises(Exit, match="courante"):
        delete_branch(c, BRANCH)
    assert f"git branch -D {BRANCH}" not in _commands(c)


def test_delete_branch_refuses_unmerged() -> None:
    c = _context(merged=())
    with pytest.raises(Exit, match="fusionnée"):
        delete_branch(c, BRANCH)
    assert f"git branch -D {BRANCH}" not in _commands(c)


def test_delete_branch_unmerged_with_force() -> None:
    c = _context(merged=())
    delete_branch(c, BRANCH, force=True)
    assert f"git branch -D {BRANCH}" in _commands(c)
    assert _merged(BRANCH) not in _commands(c)


def test_clean_branches_deletes_merged_after_yes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _answer(monkeypatch, "o")
    c = _context(merged=("main", "develop", "feature/ci-03", BRANCH))
    clean_branches(c)
    commands = _commands(c)
    deleted = [cmd for cmd in commands if cmd.startswith("git branch -D")]
    assert deleted == [f"git branch -D {BRANCH}"]
    assert f"git push origin --delete {BRANCH}" in commands
    assert commands[-1] == FETCH
    assert BRANCH in capsys.readouterr().out


@pytest.mark.parametrize("answer", ["n", ""])
def test_clean_branches_keeps_all_without_yes(
    monkeypatch: pytest.MonkeyPatch, answer: str
) -> None:
    _answer(monkeypatch, answer)
    c = _context()
    clean_branches(c)
    assert not any(
        cmd.startswith(("git branch -D", "git push")) for cmd in _commands(c)
    )


def test_clean_branches_nothing_to_delete(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(_: str) -> str:
        raise AssertionError("question inattendue")

    monkeypatch.setattr("builtins.input", fail)
    c = _context(merged=())
    clean_branches(c)
    assert "Aucune" in capsys.readouterr().out
