import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from cartograph.bin.suivi import run
from cartograph.bin.suivi.actions import RunStats

FIXTURES = Path(__file__).parent / "fixtures" / "suivi"


@pytest.fixture
def paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, isolated_logs: Path) -> Path:
    monkeypatch.setattr(run, "ROADMAP", FIXTURES / "roadmap.md")
    monkeypatch.setattr(run, "JOURNAL", FIXTURES / "journal.md")
    monkeypatch.setattr(run, "LOG", tmp_path / "LOG.md")
    monkeypatch.setattr(run, "COVERAGE_DATA", tmp_path / ".coverage")
    monkeypatch.setattr(run, "OUT_DIR", tmp_path / "suivi")
    monkeypatch.setattr(run, "collect_runs", lambda month: RunStats(2, 2, 0, 130, 0))
    monkeypatch.setattr(run, "count_tests", lambda: 42)
    monkeypatch.setattr(run, "today", lambda: date(2026, 11, 15))
    return tmp_path / "suivi"


def test_main_writes_the_report_of_the_month(paths: Path) -> None:
    assert run.main(["--mois", "2026-10"]) == 0

    text = (paths / "2026-10.md").read_text(encoding="utf-8")
    assert "# Suivi — octobre 2026" in text
    assert "| Jours travaillés | 2 (27, 30) |" in text
    assert "| Minutes facturables | 130 |" in text
    assert "| Couverture | non mesuré |" in text


def test_main_defaults_to_the_current_month(paths: Path) -> None:
    assert run.main([]) == 0

    assert (paths / "2026-11.md").exists()


def test_main_refuses_to_overwrite_without_force(paths: Path, caplog: Any) -> None:
    run.main(["--mois", "2026-10"])

    assert run.main(["--mois", "2026-10"]) == 1
    assert run.main(["--mois", "2026-10", "--force"]) == 0


def test_main_rejects_a_malformed_month(paths: Path) -> None:
    with pytest.raises(SystemExit):
        run.main(["--mois", "2026-1"])


def test_main_drops_a_stale_coverage_report(
    paths: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".coverage").write_bytes(b"")
    (tmp_path / "coverage.json").write_text(
        '{"totals": {"percent_covered": 50.0, "num_statements": 10}}', encoding="utf-8"
    )
    monkeypatch.setattr(
        run.subprocess,
        "run",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 1),
    )

    assert run.main(["--mois", "2026-10"]) == 0

    text = (paths / "2026-10.md").read_text(encoding="utf-8")
    assert "| Couverture | non mesuré |" in text
