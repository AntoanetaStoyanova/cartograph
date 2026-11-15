import json
import os
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest

from cartograph.bin.suivi import quality
from cartograph.bin.suivi.quality import Coverage, count_tests, read_coverage
from cartograph.config import PROJECT_ROOT


def write_coverage(tmp_path: Path) -> tuple[Path, Path]:
    data = tmp_path / ".coverage"
    data.write_bytes(b"")
    os.utime(data, (datetime(2026, 11, 14, 10).timestamp(),) * 2)
    path = tmp_path / "coverage.json"
    path.write_text(
        json.dumps({"totals": {"percent_covered": 97.456, "num_statements": 812}}),
        encoding="utf-8",
    )
    return path, data


def test_read_coverage_from_coverage_json(tmp_path: Path) -> None:
    path, data = write_coverage(tmp_path)

    assert read_coverage(path, data) == Coverage(
        percent=97.46, statements=812, measured=date(2026, 11, 14)
    )


def test_read_coverage_without_report(tmp_path: Path) -> None:
    _, data = write_coverage(tmp_path)

    assert read_coverage(tmp_path / "absent.json", data) is None


def test_read_coverage_without_data_file(tmp_path: Path) -> None:
    path, data = write_coverage(tmp_path)
    data.unlink()

    assert read_coverage(path, data) is None


def test_count_tests_parses_pytest_collect_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.update(kwargs)
        return subprocess.CompletedProcess(
            args, 0, stdout="tests/test_a.py::test_x\n\n151 tests collected in 2.1s\n"
        )

    monkeypatch.setattr(quality.subprocess, "run", run)

    assert count_tests() == 151
    assert seen["cwd"] == PROJECT_ROOT


def test_count_tests_without_summary_line(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 4, stdout="error\n")

    monkeypatch.setattr(quality.subprocess, "run", run)

    assert count_tests() is None
