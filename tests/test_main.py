import logging
from pathlib import Path

import pytest

from cartograph.__main__ import PROJECT_NAME, main


@pytest.mark.usefixtures("isolated_logs")
def test_main_logs_start_and_languages(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger=PROJECT_NAME):
        main()

    messages = caplog.messages
    assert "Démarrage de cartograph" in messages
    assert "Langues : fr, en, ja" in messages


def test_main_writes_log_file(isolated_logs: Path) -> None:
    main()

    log_files = list(isolated_logs.glob(f"{PROJECT_NAME}_*.log"))
    assert len(log_files) == 1
    assert "Démarrage de cartograph" in log_files[0].read_text(encoding="utf-8")
