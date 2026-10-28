import pytest

from cartograph.bin.collect.catalogue import fetch_catalogue, list_card_ids
from cartograph.bin.collect.client import TcgdexClient
from tests.conftest import load_fixture


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
