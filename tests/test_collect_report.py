import json
from pathlib import Path
from typing import Any

import pytest

from cartograph.bin.collect.report import main, render_markdown

REAL_SUMMARY = Path(__file__).parent / "fixtures" / "collect-summary.json"


def _step(**overrides: Any) -> dict[str, Any]:
    step: dict[str, Any] = {
        "status": "ok",
        "fetched": 18254,
        "failed": [],
        "skipped_without_id_product": 2978,
        "files": [
            {"name": "prices-2026-10-28.parquet", "rows": 18254, "bytes": 550831}
        ],
        "source": "cards-2026-10-28.parquet",
        "missing_languages": [],
        "error": None,
    }
    return step | overrides


def _summary(**steps: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": "2026-10-28",
        "started_at": "2026-10-28T03:17:05+00:00",
        "finished_at": "2026-10-28T04:30:05+00:00",
        "steps": {"catalogue": _step(status="skipped", fetched=0, files=[])}
        | {"prices": _step()}
        | steps,
    }


def test_successful_collection_shows_counts_files_and_duration() -> None:
    markdown = render_markdown(_summary())

    assert "## Collecte du 2026-10-28" in markdown
    assert "1 h 13 min" in markdown
    assert "| Prix | ✅ ok | 18 254 | 0 | 2 978 |" in markdown
    assert "| `prices-2026-10-28.parquet` | 18 254 | 0,6 Mo |" in markdown
    assert "`cards-2026-10-28.parquet`" in markdown


def test_skipped_step_is_marked_without_counts() -> None:
    markdown = render_markdown(_summary())

    assert "| Catalogue | sautée | | | |" in markdown


def test_failed_step_shows_error_and_missing_languages() -> None:
    prices = _step(
        status="failed",
        missing_languages=["ja"],
        error="TcgdexError: 503 après 4 tentatives",
        files=[],
    )

    markdown = render_markdown(_summary(prices=prices))

    assert "| Prix | ❌ échec |" in markdown
    assert "TcgdexError: 503 après 4 tentatives" in markdown
    assert "Langues absentes du catalogue : ja" in markdown


def test_long_failure_list_is_truncated() -> None:
    failed = [f"fr/card-{i}" for i in range(25)]

    markdown = render_markdown(_summary(prices=_step(failed=failed)))

    assert "`fr/card-19`" in markdown
    assert "`fr/card-20`" not in markdown
    assert "… et 5 autres" in markdown


def test_real_summary_contains_no_price() -> None:
    summary = json.loads(REAL_SUMMARY.read_text(encoding="utf-8"))

    markdown = render_markdown(summary).lower()

    for marker in ("cm_", "avg", "trend", "low", "€"):
        assert marker not in markdown


def test_main_writes_markdown_to_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "collect-2026-10-28.json"
    path.write_text(json.dumps(_summary()), encoding="utf-8")

    assert main([str(path)]) == 0
    assert "## Collecte du 2026-10-28" in capsys.readouterr().out
