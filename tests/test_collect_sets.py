import json
from collections.abc import Callable
from datetime import UTC, date, datetime

import httpx
import pytest

from cartograph.bin.collect.client import TcgdexClient
from cartograph.bin.collect.sets import fetch_sets, list_set_ids
from cartograph.bin.collect.snapshot import SET_SCHEMA, set_table
from tests.conftest import fixture_route, load_fixture, mock_client

FETCHED_AT = datetime(2026, 11, 16, 3, 17, tzinfo=UTC)


def test_list_set_ids_returns_ids(tcgdex_client: TcgdexClient) -> None:
    assert list_set_ids(tcgdex_client, "fr") == ["base1", "swsh3"]


def test_fetch_sets_returns_full_sets(tcgdex_client: TcgdexClient) -> None:
    result = fetch_sets(tcgdex_client, "ja")

    assert result.items == [load_fixture("ja_sets_SM1+"), load_fixture("ja_sets_SV7")]
    assert result.failed == []


def test_fetch_sets_records_failed_set_with_language() -> None:
    def swsh3_down(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/en/sets/swsh3":
            return httpx.Response(500)
        return fixture_route(request)

    with mock_client(swsh3_down) as client:
        result = fetch_sets(client, "en")

    assert [item["id"] for item in result.items] == ["miscp"]
    assert result.failed == ["en/swsh3"]


@pytest.mark.parametrize("function", [list_set_ids, fetch_sets])
def test_sets_reject_unknown_language(
    tcgdex_client: TcgdexClient, function: Callable[[TcgdexClient, str], object]
) -> None:
    with pytest.raises(ValueError, match="de"):
        function(tcgdex_client, "de")


def test_set_table_matches_schema() -> None:
    sets = {"fr": [load_fixture("fr_sets_swsh3")], "ja": [load_fixture("ja_sets_SV7")]}

    table = set_table(sets, FETCHED_AT)

    assert table.schema == SET_SCHEMA
    assert table.column("language").to_pylist() == ["fr", "ja"]
    row = table.to_pylist()[0]
    assert row == row | {
        "set_id": "swsh3",
        "name": "Ténèbres Embrasées",
        "serie_id": "swsh",
        "serie_name": "Épée et Bouclier",
        "release_date": date(2020, 8, 14),
        "abbreviation_official": "DAA",
        "abbreviation_localized": "TEM",
        "card_count_total": 201,
        "card_count_official": 189,
        "logo": "https://assets.tcgdex.net/fr/swsh/swsh3/logo",
        "symbol": "https://assets.tcgdex.net/univ/swsh/swsh3/symbol",
        "fetched_at": FETCHED_AT,
    }


def test_set_table_raw_json_has_no_cards() -> None:
    swsh3 = load_fixture("fr_sets_swsh3")

    row = set_table({"fr": [swsh3]}, FETCHED_AT).to_pylist()[0]

    raw = json.loads(row["raw_json"])
    assert "cards" not in raw
    assert raw == {key: value for key, value in swsh3.items() if key != "cards"}


def test_set_table_missing_values_are_null() -> None:
    row = set_table({"ja": [{"id": "SM1+"}]}, FETCHED_AT).to_pylist()[0]

    assert row["set_id"] == "SM1+"
    assert [key for key, value in row.items() if value is None] == [
        "name",
        "serie_id",
        "serie_name",
        "release_date",
        "abbreviation_official",
        "abbreviation_localized",
        "card_count_total",
        "card_count_official",
        "logo",
        "symbol",
    ]


def test_set_table_empty() -> None:
    table = set_table({}, FETCHED_AT)

    assert table.schema == SET_SCHEMA
    assert table.num_rows == 0
