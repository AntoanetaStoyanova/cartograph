import pytest

from cartograph.config import (
    DATA_DIR,
    ENV_FILE,
    LANGUAGES,
    LOG_DIR,
    PROJECT_ROOT,
    _require_env,
)


def test_languages_are_non_empty_and_unique() -> None:
    assert LANGUAGES
    assert len(set(LANGUAGES)) == len(LANGUAGES)


def test_require_env_returns_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CARTOGRAPH_TEST_VAR", "valeur")

    assert _require_env("CARTOGRAPH_TEST_VAR") == "valeur"


@pytest.mark.parametrize("value", [None, ""])
def test_require_env_missing_raises_clear_error(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is None:
        monkeypatch.delenv("CARTOGRAPH_TEST_VAR", raising=False)
    else:
        monkeypatch.setenv("CARTOGRAPH_TEST_VAR", value)

    with pytest.raises(RuntimeError, match=r"\.env\.example"):
        _require_env("CARTOGRAPH_TEST_VAR")


def test_env_file_is_at_project_root() -> None:
    assert (ENV_FILE.parent / "pyproject.toml").exists()


def test_output_dirs_are_at_project_root_outside_package() -> None:
    assert PROJECT_ROOT.is_absolute()
    assert DATA_DIR == PROJECT_ROOT / "data"
    assert LOG_DIR == PROJECT_ROOT / "logs"
