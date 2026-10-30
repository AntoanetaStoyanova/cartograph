import json
import re
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from cartograph.bin.collect.client import TcgdexClient

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "tcgdex"
REAL_SUMMARY = Path(__file__).parent / "fixtures" / "collect-summary.json"
PRICE_MARKERS = ("cm_", "avg", "trend", "low", "€")
SUMMARY_DAY = "2026-10-28"
_ROUTE = re.compile(r"^/v2/(?P<language>[^/]+)/cards(?:/(?P<card_id>.+))?$")


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text(encoding="utf-8"))


def fixture_route(request: httpx.Request) -> httpx.Response:
    match = _ROUTE.match(request.url.path)
    if match is None:
        return httpx.Response(404)
    language, card_id = match["language"], match["card_id"]
    name = f"{language}_cards" if card_id is None else f"{language}_{card_id}"
    if not (FIXTURES_DIR / f"{name}.json").exists():
        return httpx.Response(404)
    return httpx.Response(200, json=load_fixture(name))


def mock_client(handler: Callable[[httpx.Request], httpx.Response]) -> TcgdexClient:
    return TcgdexClient(
        transport=httpx.MockTransport(handler), max_retries=0, sleep=lambda _: None
    )


@pytest.fixture
def tcgdex_client() -> Iterator[TcgdexClient]:
    with TcgdexClient(
        transport=httpx.MockTransport(fixture_route), sleep=lambda _: None
    ) as client:
        yield client


def price_values(node: Any) -> set[str]:
    if isinstance(node, dict):
        values = set()
        for key, value in node.items():
            if key == "pricing" and value is not None:
                cardmarket = value.get("cardmarket") or {}
                values |= {
                    str(v)
                    for k, v in cardmarket.items()
                    if isinstance(v, float) and k != "idProduct"
                }
            values |= price_values(value)
        return values
    if isinstance(node, list):
        return set().union(*(price_values(item) for item in node))
    return set()


def make_step(**overrides: Any) -> dict[str, Any]:
    step: dict[str, Any] = {
        "status": "ok",
        "fetched": 18254,
        "failed": [],
        "skipped_without_id_product": 2978,
        "files": [
            {"name": f"prices-{SUMMARY_DAY}.parquet", "rows": 18254, "bytes": 550831},
            {"name": f"prices-{SUMMARY_DAY}.json.gz", "rows": 18254, "bytes": 742904},
        ],
        "source": f"cards-{SUMMARY_DAY}.parquet",
        "missing_languages": [],
        "error": None,
    }
    return step | overrides


def make_summary(**steps: dict[str, Any]) -> dict[str, Any]:
    skipped = make_step(status="skipped", fetched=0, files=[], source=None)
    return {
        "date": SUMMARY_DAY,
        "started_at": f"{SUMMARY_DAY}T03:17:05+00:00",
        "finished_at": f"{SUMMARY_DAY}T04:30:05+00:00",
        "steps": {"catalogue": skipped, "prices": make_step()} | steps,
    }
