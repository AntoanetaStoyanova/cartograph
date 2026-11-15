import json
import subprocess
from typing import Any

import pytest

from cartograph.bin.suivi import actions
from cartograph.bin.suivi.actions import RunStats, collect_runs, gh_api

RUNS_PATH = (
    "repos/AntoanetaStoyanova/cartograph-data/actions/workflows/collect.yml/runs"
    "?created=2026-11-01..2026-11-30&per_page=100"
)


def fake_fetch(pages: dict[str, list[dict[str, Any]]]) -> Any:
    calls: list[str] = []

    def fetch(path: str, key: str) -> list[dict[str, Any]]:
        calls.append(path)
        return pages[path]

    fetch.calls = calls  # type: ignore[attr-defined]
    return fetch


def job(start: str, end: str | None) -> dict[str, Any]:
    return {"started_at": start, "completed_at": end}


def test_collect_runs_counts_runs_and_bills_whole_minutes() -> None:
    fetch = fake_fetch(
        {
            RUNS_PATH: [
                {"id": 1, "conclusion": "success"},
                {"id": 2, "conclusion": "failure"},
            ],
            "repos/AntoanetaStoyanova/cartograph-data/actions/runs/1/jobs": [
                job("2026-11-01T03:17:00Z", "2026-11-01T04:20:30Z")
            ],
            "repos/AntoanetaStoyanova/cartograph-data/actions/runs/2/jobs": [
                job("2026-11-02T03:17:00Z", "2026-11-02T03:17:10Z"),
                job("2026-11-02T03:18:00Z", None),
            ],
        }
    )

    assert collect_runs("2026-11", fetch=fetch) == RunStats(
        runs=2, succeeded=1, failed=1, billed_minutes=64 + 1
    )


def test_collect_runs_of_a_month_without_runs() -> None:
    fetch = fake_fetch(
        {RUNS_PATH.replace("11-01..2026-11-30", "12-01..2026-12-31"): []}
    )

    assert collect_runs("2026-12", fetch=fetch) == RunStats(0, 0, 0, 0)


def test_gh_api_reads_every_page(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = "\n".join(json.dumps({"id": n}) for n in range(3)) + "\n"
    seen: list[list[str]] = []

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.append(args)
        return subprocess.CompletedProcess(args, 0, stdout=pages, stderr="")

    monkeypatch.setattr(actions.subprocess, "run", run)

    assert gh_api("repos/x/runs", "workflow_runs") == [{"id": 0}, {"id": 1}, {"id": 2}]
    assert seen[0][:4] == ["gh", "api", "--paginate", "--jq"]
    assert seen[0][4] == ".workflow_runs[]"
