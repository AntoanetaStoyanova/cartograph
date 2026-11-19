import subprocess
from pathlib import Path

import pytest
from invoke import Exit, MockContext, Result

from tasks import _clean_targets, _read_clean, clean

LS_FILES = "git ls-files"


def _touch(root: Path, *paths: str) -> None:
    for path in paths:
        target = root / path
        if path.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("x", encoding="utf-8")


def _relative(root: Path, paths: list[Path]) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in paths)


def test_read_clean_skips_blank_lines_and_comments(tmp_path: Path) -> None:
    path = tmp_path / ".clean"
    path.write_text("# caches\n\n.pytest_cache/\n  \n.coverage\n", encoding="utf-8")

    assert _read_clean(path) == [".pytest_cache/", ".coverage"]


def test_read_clean_missing_file(tmp_path: Path) -> None:
    with pytest.raises(Exit, match=r"\.clean"):
        _read_clean(tmp_path / ".clean")


def test_targets_match_files_and_directories(tmp_path: Path) -> None:
    _touch(
        tmp_path,
        "src/pkg/__pycache__/a.pyc",
        "__pycache__/b.pyc",
        ".coverage",
        "dbt/target/run.json",
        "src/pkg/a.py",
    )
    patterns = ["**/__pycache__/", ".coverage", "dbt/target/", "htmlcov/"]

    targets = _clean_targets(tmp_path, patterns, set())

    assert _relative(tmp_path, targets) == [
        ".coverage",
        "__pycache__",
        "dbt/target",
        "src/pkg/__pycache__",
    ]


def test_directory_pattern_ignores_files(tmp_path: Path) -> None:
    _touch(tmp_path, "build")

    assert _clean_targets(tmp_path, ["build/"], set()) == []


def test_wildcards_skip_protected_directories(tmp_path: Path) -> None:
    _touch(tmp_path, ".venv/lib/__pycache__/a.pyc", "docs/plans/__pycache__/")

    assert _clean_targets(tmp_path, ["**/__pycache__/"], set()) == []


@pytest.mark.parametrize(
    "pattern",
    [
        ".env",
        ".venv/",
        ".venv/lib/",
        ".git/",
        "data/snapshots/",
        "data/raw/x.json",
        "docs/plans/",
        "docs/specs/*.md",
        "data/",
        "docs/",
        "**/*.duckdb",
    ],
)
def test_protected_path_refused(tmp_path: Path, pattern: str) -> None:
    _touch(
        tmp_path,
        ".env",
        ".venv/lib/",
        ".git/HEAD",
        "data/snapshots/x.parquet",
        "data/raw/x.json",
        "data/cartograph.duckdb",
        "docs/plans/p.md",
        "docs/specs/s.md",
    )

    with pytest.raises(Exit, match="protégé"):
        _clean_targets(tmp_path, [pattern], set())


@pytest.mark.parametrize("pattern", ["../x/", "/tmp/x", "a/../../x"])
def test_outside_repository_refused(tmp_path: Path, pattern: str) -> None:
    with pytest.raises(Exit, match="hors du dépôt"):
        _clean_targets(tmp_path, [pattern], set())


@pytest.mark.parametrize("pattern", ["src/", "src/pkg/a.py", "**/*.py"])
def test_tracked_file_refused(tmp_path: Path, pattern: str) -> None:
    _touch(tmp_path, "src/pkg/a.py")

    with pytest.raises(Exit, match="suivi"):
        _clean_targets(tmp_path, [pattern], {"src/pkg/a.py"})


def test_clean_removes_targets_and_lists_them(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _touch(tmp_path, ".pytest_cache/v/x", ".coverage", "src/a.py", "logs/run.log")
    (tmp_path / ".clean").write_text(
        ".pytest_cache/\n.coverage\nhtmlcov/\n", encoding="utf-8"
    )
    c = MockContext(run={LS_FILES: Result(".clean\nsrc/a.py\n")})

    clean(c)

    assert not (tmp_path / ".pytest_cache").exists()
    assert not (tmp_path / ".coverage").exists()
    assert (tmp_path / "src/a.py").exists()
    assert (tmp_path / "logs/run.log").exists()
    out = capsys.readouterr().out
    assert ".pytest_cache" in out and ".coverage" in out


def test_clean_refusal_deletes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _touch(tmp_path, ".coverage", "src/a.py")
    (tmp_path / ".clean").write_text(".coverage\nsrc/\n", encoding="utf-8")
    c = MockContext(run={LS_FILES: Result("src/a.py\n")})

    with pytest.raises(Exit, match="suivi"):
        clean(c)

    assert (tmp_path / ".coverage").exists()


def test_real_clean_file_is_accepted() -> None:
    patterns = _read_clean(Path(__file__).parents[1] / ".clean")

    assert "**/__pycache__/" in patterns
    assert "logs/" not in patterns


def test_real_clean_file_targets_no_tracked_or_protected_path() -> None:
    root = Path(__file__).parents[1]
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.splitlines()

    targets = _clean_targets(root, _read_clean(root / ".clean"), set(tracked))

    assert all(path.is_relative_to(root) for path in targets)
