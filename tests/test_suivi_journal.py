from datetime import date
from pathlib import Path

import pytest

from cartograph.bin.suivi.journal import worked_days

JOURNAL = Path(__file__).parent / "fixtures" / "suivi" / "journal.md"


def test_worked_days_of_a_month() -> None:
    assert worked_days(JOURNAL, "2026-10") == [date(2026, 10, 27), date(2026, 10, 30)]


def test_worked_days_without_month_returns_all_days_sorted() -> None:
    assert worked_days(JOURNAL) == [
        date(2026, 10, 27),
        date(2026, 10, 30),
        date(2026, 11, 9),
        date(2026, 11, 15),
    ]


def test_worked_days_of_an_empty_month() -> None:
    assert worked_days(JOURNAL, "2026-12") == []


def test_worked_days_rejects_a_malformed_month() -> None:
    with pytest.raises(ValueError, match="AAAA-MM"):
        worked_days(JOURNAL, "2026-1")
