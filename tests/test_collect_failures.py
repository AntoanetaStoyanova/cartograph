import json
import logging
from collections.abc import Callable

import httpx
import pytest

from cartograph.bin.collect.catalogue import fetch_catalogue
from cartograph.bin.collect.client import TcgdexError
from cartograph.bin.collect.prices import PriceTarget, fetch_prices
from cartograph.config import MAX_CONSECUTIVE_FAILURES
from tests.conftest import fixture_route, load_fixture, mock_client


def _fail_on(fragment: str) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        if fragment in request.url.path:
            return httpx.Response(500)
        return fixture_route(request)

    return handler


def _targets(count: int) -> list[PriceTarget]:
    return [PriceTarget("fr", f"ko-{i}", i) for i in range(count)]


def test_fetch_catalogue_records_failed_card_and_continues() -> None:
    with mock_client(_fail_on("/pop9-1")) as client:
        result = fetch_catalogue(client, "fr")

    assert [card["id"] for card in result.items] == ["exu-%3F", "swsh3-136"]
    assert result.failed == ["pop9-1"]


def test_fetch_prices_records_failed_card_and_continues() -> None:
    targets = [
        PriceTarget("fr", "pop9-1", 278552),
        PriceTarget("fr", "swsh3-136", 483559),
    ]

    with mock_client(_fail_on("/pop9-1")) as client:
        result = fetch_prices(client, targets)

    assert [r["card_id"] for r in result.items] == ["swsh3-136"]
    assert result.failed == ["fr/pop9-1"]


def test_fetch_catalogue_with_empty_list_returns_nothing() -> None:
    with mock_client(lambda _: httpx.Response(200, json=[])) as client:
        result = fetch_catalogue(client, "fr")

    assert result.items == []
    assert result.failed == []


def test_fetch_prices_logs_no_price(caplog: pytest.LogCaptureFixture) -> None:
    names = ["fr_exu-%3F", "fr_pop9-1", "fr_swsh3-136", "ja_S7D-019", "ja_SV7-065"]
    cardmarkets = {name: load_fixture(name)["pricing"]["cardmarket"] for name in names}
    prices = {
        str(value)
        for cardmarket in cardmarkets.values()
        for value in cardmarket.values()
        if isinstance(value, float)
    }
    targets = [
        PriceTarget(name[:2], name[3:], cardmarket["idProduct"])
        for name, cardmarket in cardmarkets.items()
    ]
    caplog.set_level(logging.DEBUG)

    with mock_client(_fail_on("/pop9-1")) as client:
        result = fetch_prices(client, targets)

    assert len(result.items) == 4
    assert prices
    assert not any(price in caplog.text for price in prices)
    assert "en échec" in caplog.text
    assert json.dumps(result.items[0]["pricing"]) not in caplog.text


def test_list_card_ids_propagates_error() -> None:
    with (
        mock_client(lambda _: httpx.Response(500)) as client,
        pytest.raises(TcgdexError),
    ):
        fetch_catalogue(client, "fr")


def test_fetch_prices_stops_after_consecutive_failures() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(503)

    with mock_client(handler) as client, pytest.raises(TcgdexError, match="arrêt"):
        fetch_prices(client, _targets(MAX_CONSECUTIVE_FAILURES + 5))

    assert len(calls) == MAX_CONSECUTIVE_FAILURES


def test_fetch_catalogue_404s_do_not_stop_collection() -> None:
    card_ids = [f"inconnue-{i}" for i in range(MAX_CONSECUTIVE_FAILURES + 5)]

    with mock_client(fixture_route) as client:
        result = fetch_catalogue(client, "fr", card_ids=card_ids)

    assert result.items == []
    assert result.failed == card_ids


def test_consecutive_failure_counter_resets_on_success() -> None:
    failing = [f"ko-{i}" for i in range(MAX_CONSECUTIVE_FAILURES - 1)]
    card_ids = [*failing, "swsh3-136", *failing]

    with mock_client(_fail_on("/ko-")) as client:
        result = fetch_catalogue(client, "fr", card_ids=card_ids)

    assert [card["id"] for card in result.items] == ["swsh3-136"]
    assert len(result.failed) == 2 * len(failing)


def test_fetch_catalogue_logs_progress(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr("cartograph.bin.collect.batch.PROGRESS_EVERY", 2)
    caplog.set_level(logging.INFO)

    with mock_client(fixture_route) as client:
        fetch_catalogue(client, "fr")

    assert "catalogue fr : 2 / 3 cartes traitées" in caplog.text
    assert "catalogue fr : 3 récupérées, 0 en échec" in caplog.text


def test_fetch_prices_failed_ids_keep_language() -> None:
    targets = [PriceTarget("fr", "x-1", 1), PriceTarget("ja", "x-1", 2)]

    def ja_down(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/v2/ja/"):
            return httpx.Response(500)
        return httpx.Response(200, json={"id": "x-1", "pricing": None})

    with mock_client(ja_down) as client:
        result = fetch_prices(client, targets)

    assert [r["language"] for r in result.items] == ["fr"]
    assert result.failed == ["ja/x-1"]
