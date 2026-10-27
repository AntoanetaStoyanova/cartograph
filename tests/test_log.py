import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from cartograph.log import setup_logging


@pytest.fixture
def logger_name(request: pytest.FixtureRequest) -> Iterator[str]:
    name = f"test_log.{request.node.name}"
    yield name
    logger = logging.getLogger(name)
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


def test_setup_logging_sets_level(logger_name: str) -> None:
    logger = setup_logging(logger_name, level=logging.DEBUG)

    assert logger.level == logging.DEBUG


def test_setup_logging_twice_does_not_duplicate_handlers(logger_name: str) -> None:
    setup_logging(logger_name)
    logger = setup_logging(logger_name)

    assert len(logger.handlers) == 1


def test_setup_logging_writes_file_when_log_dir_given(
    logger_name: str, tmp_path: Path
) -> None:
    logger = setup_logging(logger_name, log_dir=tmp_path / "logs")
    logger.info("hello")

    log_files = list((tmp_path / "logs").glob(f"{logger_name}_*.log"))
    assert len(log_files) == 1
    assert "hello" in log_files[0].read_text(encoding="utf-8")


def test_setup_logging_without_log_dir_creates_no_file(
    logger_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    logger = setup_logging(logger_name)

    assert not any(isinstance(h, logging.FileHandler) for h in logger.handlers)
    assert list(tmp_path.iterdir()) == []


def test_setup_logging_console_writes_to_stderr(
    logger_name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    logger = setup_logging(logger_name)
    logger.info("hello")

    captured = capsys.readouterr()
    assert "hello" in captured.err
    assert captured.out == ""


def _create_old_logs(log_dir: Path, name: str, count: int) -> list[Path]:
    log_dir.mkdir(parents=True, exist_ok=True)
    files = [log_dir / f"{name}_2026010{i}_000000.log" for i in range(count)]
    for file in files:
        file.touch()
    return files


def test_setup_logging_keeps_max_files_and_removes_oldest(
    logger_name: str, tmp_path: Path
) -> None:
    old_files = _create_old_logs(tmp_path, logger_name, count=3)

    setup_logging(logger_name, log_dir=tmp_path, max_files=3)

    remaining = sorted(tmp_path.glob(f"{logger_name}_*.log"))
    assert len(remaining) == 3
    assert not old_files[0].exists()
    assert old_files[1].exists() and old_files[2].exists()


def test_setup_logging_below_max_files_removes_nothing(
    logger_name: str, tmp_path: Path
) -> None:
    old_files = _create_old_logs(tmp_path, logger_name, count=2)

    setup_logging(logger_name, log_dir=tmp_path, max_files=10)

    assert all(file.exists() for file in old_files)
    assert len(list(tmp_path.glob(f"{logger_name}_*.log"))) == 3


def test_setup_logging_does_not_remove_other_logs(
    logger_name: str, tmp_path: Path
) -> None:
    _create_old_logs(tmp_path, logger_name, count=3)
    other = tmp_path / "autre_20250101_000000.log"
    other.touch()

    setup_logging(logger_name, log_dir=tmp_path, max_files=1)

    assert other.exists()
    assert len(list(tmp_path.glob(f"{logger_name}_*.log"))) == 1


def test_setup_logging_twice_does_not_remove_again(
    logger_name: str, tmp_path: Path
) -> None:
    _create_old_logs(tmp_path, logger_name, count=3)
    setup_logging(logger_name, log_dir=tmp_path, max_files=3)
    remaining = sorted(tmp_path.glob(f"{logger_name}_*.log"))

    setup_logging(logger_name, log_dir=tmp_path, max_files=3)

    assert sorted(tmp_path.glob(f"{logger_name}_*.log")) == remaining
