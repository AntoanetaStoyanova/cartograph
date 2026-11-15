import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from cartograph.bin.suivi import quality
from cartograph.bin.suivi.quality import Coverage, count_tests, read_coverage


def test_read_coverage_from_coverage_json(tmp_path: Path) -> None:
    path = tmp_path / "coverage.json"
    path.write_text(
        json.dumps({"totals": {"percent_covered": 97.456, "num_statements": 812}}),
        encoding="utf-8",
    )

    assert read_coverage(path) == Coverage(percent=97.46, statements=812)


def test_read_coverage_without_file(tmp_path: Path) -> None:
    assert read_coverage(tmp_path / "coverage.json") is None


def test_count_tests_parses_pytest_collect_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args, 0, stdout="tests/test_a.py::test_x\n\n151 tests collected in 2.1s\n"
        )

    monkeypatch.setattr(quality.subprocess, "run", run)

    assert count_tests() == 151


def test_count_tests_without_summary_line(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 4, stdout="error\n")

    monkeypatch.setattr(quality.subprocess, "run", run)

    assert count_tests() is None
