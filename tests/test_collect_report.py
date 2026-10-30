import json
from pathlib import Path

import pytest

from cartograph.bin.collect.report import main, render_markdown
from tests.conftest import PRICE_MARKERS, REAL_SUMMARY, make_step, make_summary


def test_successful_collection_shows_counts_files_and_duration() -> None:
    markdown = render_markdown(make_summary())

    assert "## Collecte du 2026-10-28" in markdown
    assert "1 h 13 min" in markdown
    assert "| Prix | ✅ ok | 18 254 | 0 | 2 978 |" in markdown
    assert "| `prices-2026-10-28.parquet` | 18 254 | 0,6 Mo |" in markdown
    assert "`cards-2026-10-28.parquet`" in markdown


def test_skipped_step_is_marked_without_counts() -> None:
    markdown = render_markdown(make_summary())

    assert "| Catalogue | sautée | | | |" in markdown


def test_failed_step_shows_error_and_missing_languages() -> None:
    prices = make_step(
        status="failed",
        missing_languages=["ja"],
        error="TcgdexError: 503 après 4 tentatives",
        files=[],
    )

    markdown = render_markdown(make_summary(prices=prices))

    assert "| Prix | ❌ échec |" in markdown
    assert "TcgdexError: 503 après 4 tentatives" in markdown
    assert "Langues absentes du catalogue : ja" in markdown


def test_long_failure_list_is_truncated() -> None:
    failed = [f"fr/card-{i}" for i in range(25)]

    markdown = render_markdown(make_summary(prices=make_step(failed=failed)))

    assert "`fr/card-19`" in markdown
    assert "`fr/card-20`" not in markdown
    assert "… et 5 autres" in markdown


def test_real_summary_contains_no_price() -> None:
    summary = json.loads(REAL_SUMMARY.read_text(encoding="utf-8"))

    markdown = render_markdown(summary).lower()

    for marker in PRICE_MARKERS:
        assert marker not in markdown


def test_main_writes_markdown_to_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "collect-2026-10-28.json"
    path.write_text(json.dumps(make_summary()), encoding="utf-8")

    assert main([str(path)]) == 0
    assert "## Collecte du 2026-10-28" in capsys.readouterr().out
