from datetime import UTC, datetime, timedelta, timezone

from cartograph.bin.collect.catalogue import fetch_catalogue
from cartograph.bin.collect.client import TcgdexClient
from cartograph.bin.collect.prices import PriceTarget, fetch_prices, price_targets
from tests.conftest import load_fixture


def _card(card_id: str, id_product: int | None) -> dict[str, object]:
    cardmarket = None if id_product is None else {"idProduct": id_product}
    return {"id": card_id, "pricing": {"cardmarket": cardmarket}}


def test_price_targets_deduplicates_european_products() -> None:
    catalogues = {
        "en": [load_fixture("en_swsh3-136")],
        "fr": [load_fixture("fr_swsh3-136")],
    }

    assert price_targets(catalogues) == [PriceTarget("fr", "swsh3-136", 483559)]


def test_price_targets_keeps_japanese_products() -> None:
    catalogues = {
        "fr": [load_fixture("fr_swsh3-136")],
        "ja": [load_fixture("ja_S7D-019"), load_fixture("ja_SV7-065")],
    }

    assert price_targets(catalogues) == [
        PriceTarget("fr", "swsh3-136", 483559),
        PriceTarget("ja", "S7D-019", 571601),
        PriceTarget("ja", "SV7-065", 779079),
    ]


def test_price_targets_skips_cards_without_id_product() -> None:
    catalogues = {
        "fr": [{"id": "sans-pricing"}, _card("sans-cardmarket", None)],
        "ja": [load_fixture("ja_PMCG6-055")],
    }

    assert price_targets(catalogues) == []


def test_fetch_prices_returns_one_record_per_target(
    tcgdex_client: TcgdexClient,
) -> None:
    catalogues = {
        language: fetch_catalogue(tcgdex_client, language).items
        for language in ("fr", "en", "ja")
    }
    targets = price_targets(catalogues)

    result = fetch_prices(tcgdex_client, targets)

    assert [(r["language"], r["card_id"]) for r in result.items] == [
        ("fr", "exu-%3F"),
        ("fr", "pop9-1"),
        ("fr", "swsh3-136"),
        ("ja", "S7D-019"),
        ("ja", "SV7-065"),
    ]
    assert result.items[2]["id_product"] == 483559
    assert result.items[2]["pricing"] == load_fixture("fr_swsh3-136")["pricing"]
    assert result.failed == []


def test_fetch_prices_sets_fetched_at_in_utc(tcgdex_client: TcgdexClient) -> None:
    paris = timezone(timedelta(hours=1))
    targets = [PriceTarget("fr", "swsh3-136", 483559)]

    result = fetch_prices(
        tcgdex_client, targets, now=lambda: datetime(2026, 10, 28, 9, 30, tzinfo=paris)
    )

    assert result.items[0]["fetched_at"] == "2026-10-28T08:30:00+00:00"
    assert datetime.fromisoformat(result.items[0]["fetched_at"]).tzinfo == UTC
