from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any

import httpx
import pyarrow as pa
import pytest

from cartograph.bin.collect.catalogue import (
    ListingDiff,
    fetch_catalogue,
    list_card_ids,
    listing_diff,
)
from cartograph.bin.collect.client import TcgdexClient
from cartograph.bin.collect.snapshot import catalogue_table
from tests.conftest import fixture_route, load_fixture, mock_client

FETCHED_AT = datetime(2026, 11, 16, 3, 17, tzinfo=UTC)
REMOVED_ON = date(2026, 11, 17)


def test_list_card_ids_returns_ids(tcgdex_client: TcgdexClient) -> None:
    assert list_card_ids(tcgdex_client, "fr") == ["exu-%3F", "pop9-1", "swsh3-136"]


def test_fetch_catalogue_returns_full_cards(tcgdex_client: TcgdexClient) -> None:
    result = fetch_catalogue(tcgdex_client, "ja")

    assert [card["id"] for card in result.items] == [
        "S7D-019",
        "SV7-065",
        "PMCG6-055",
    ]
    assert result.items[0] == load_fixture("ja_S7D-019")
    assert result.failed == []


def test_fetch_catalogue_rejects_unknown_language(
    tcgdex_client: TcgdexClient,
) -> None:
    with pytest.raises(ValueError, match="de"):
        fetch_catalogue(tcgdex_client, "de")


def test_fetch_catalogue_uses_given_card_ids(tcgdex_client: TcgdexClient) -> None:
    result = fetch_catalogue(tcgdex_client, "fr", card_ids=["exu-%3F", "swsh3-136"])

    assert [card["id"] for card in result.items] == ["exu-%3F", "swsh3-136"]


def _card(language: str, card_id: str) -> dict[str, Any]:
    if card_id == "base4-52":
        return {**load_fixture(f"{language}_pop9-1"), "id": card_id}
    return dict(load_fixture(f"{language}_{card_id}"))


def _catalogue(
    cards: dict[str, list[str]], removed: frozenset[str] = frozenset()
) -> pa.Table:
    table = catalogue_table(
        {
            language: [_card(language, card_id) for card_id in card_ids]
            for language, card_ids in cards.items()
        },
        FETCHED_AT,
    )
    removed_on = [
        REMOVED_ON if card_id in removed else None
        for card_id in table.column("card_id").to_pylist()
    ]
    return table.set_column(
        table.schema.get_field_index("removed_on"),
        "removed_on",
        pa.array(removed_on, pa.date32()),
    )


def _recording(requested: list[str]) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        return fixture_route(request)

    return handler


def test_listing_diff_finds_new_removed_and_reappeared() -> None:
    catalogue = _catalogue(
        {
            "fr": ["exu-%3F", "base4-52", "swsh3-136"],
            "ja": ["S7D-019", "SV7-065"],
        },
        removed=frozenset({"swsh3-136"}),
    )
    requested: list[str] = []

    with mock_client(_recording(requested)) as client:
        diff = listing_diff(client, ["fr", "ja"], catalogue)

    assert diff == ListingDiff(
        new={"fr": ["pop9-1"], "ja": ["PMCG6-055"]},
        removed={"fr": ["base4-52"], "ja": []},
        reappeared={"fr": ["swsh3-136"], "ja": []},
    )
    assert requested == ["/v2/fr/cards", "/v2/ja/cards"]


def test_listing_diff_skips_language_absent_from_catalogue() -> None:
    catalogue = _catalogue({"fr": ["exu-%3F", "pop9-1", "swsh3-136"]})
    requested: list[str] = []

    with mock_client(_recording(requested)) as client:
        diff = listing_diff(client, ["fr", "en"], catalogue)

    assert diff == ListingDiff(
        new={"fr": [], "en": []},
        removed={"fr": [], "en": []},
        reappeared={"fr": [], "en": []},
    )
    assert requested == ["/v2/fr/cards"]


def test_listing_diff_does_not_count_card_already_removed() -> None:
    catalogue = _catalogue(
        {"fr": ["exu-%3F", "pop9-1", "swsh3-136", "base4-52"]},
        removed=frozenset({"base4-52"}),
    )

    with mock_client(fixture_route) as client:
        diff = listing_diff(client, ["fr"], catalogue)

    assert diff == ListingDiff(
        new={"fr": []}, removed={"fr": []}, reappeared={"fr": []}
    )


def test_listing_diff_rejects_unknown_language() -> None:
    with mock_client(fixture_route) as client, pytest.raises(ValueError, match="de"):
        listing_diff(client, ["de"], _catalogue({"fr": ["pop9-1"]}))


def test_listing_diff_empty_listing_removes_nothing() -> None:
    catalogue = _catalogue({"fr": ["exu-%3F", "pop9-1"]})

    def empty(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    with mock_client(empty) as client:
        diff = listing_diff(client, ["fr"], catalogue)

    assert diff == ListingDiff(
        new={"fr": []}, removed={"fr": []}, reappeared={"fr": []}
    )
