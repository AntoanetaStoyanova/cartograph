import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

import cartograph.__main__ as entry
from cartograph.__main__ import PROJECT_NAME, main


@pytest.fixture
def isolated_logger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setattr(entry, "LOG_DIR", tmp_path)
    yield tmp_path
    logger = logging.getLogger(PROJECT_NAME)
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


@pytest.mark.usefixtures("isolated_logger")
def test_main_logs_start_and_languages(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger=PROJECT_NAME):
        main()

    messages = caplog.messages
    assert "Démarrage de cartograph" in messages
    assert "Langues : fr, en, ja" in messages


def test_main_writes_log_file(isolated_logger: Path) -> None:
    main()

    log_files = list(isolated_logger.glob(f"{PROJECT_NAME}_*.log"))
    assert len(log_files) == 1
    assert "Démarrage de cartograph" in log_files[0].read_text(encoding="utf-8")
