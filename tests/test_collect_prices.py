from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa

from cartograph.bin.collect.catalogue import fetch_catalogue
from cartograph.bin.collect.client import TcgdexClient
from cartograph.bin.collect.prices import (
    PriceSelection,
    PriceTarget,
    fetch_prices,
    price_targets_from_catalogue,
    price_targets_from_table,
    prices_from_cards,
)
from cartograph.bin.collect.snapshot import (
    SORT_BY,
    card_table,
    catalogue_table,
    price_table,
    write_parquet,
)
from tests.conftest import load_fixture

FETCHED_AT = datetime(2026, 10, 28, 9, 30, tzinfo=UTC)


def _card(card_id: str, id_product: int | None) -> dict[str, object]:
    cardmarket = None if id_product is None else {"idProduct": id_product}
    return {"id": card_id, "pricing": {"cardmarket": cardmarket}}


def price_targets(
    catalogues: Mapping[str, Sequence[dict[str, Any]]],
) -> list[PriceTarget]:
    table = pa.concat_tables(
        card_table(cards, language, FETCHED_AT)
        for language, cards in catalogues.items()
    )
    return price_targets_from_table(table)


def _catalogue_file(
    tmp_path: Path, catalogues: Mapping[str, Sequence[dict[str, Any]]]
) -> Path:
    table = pa.concat_tables(
        card_table(cards, language, FETCHED_AT)
        for language, cards in catalogues.items()
    )
    path = tmp_path / "cards-2026-10-28.parquet"
    write_parquet(table, path, SORT_BY)
    return path


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


def test_price_targets_from_catalogue_filters_requested_languages(
    tmp_path: Path,
) -> None:
    source = _catalogue_file(
        tmp_path,
        {
            "fr": [load_fixture("fr_swsh3-136")],
            "en": [load_fixture("en_swsh3-136")],
            "ja": [load_fixture("ja_S7D-019")],
        },
    )

    selection = price_targets_from_catalogue(source, ["en", "ja"])

    assert selection == PriceSelection(
        targets=[
            PriceTarget("en", "swsh3-136", 483559),
            PriceTarget("ja", "S7D-019", 571601),
        ],
        missing_languages=[],
        skipped_without_id_product=0,
    )


def test_price_targets_from_catalogue_reports_missing_languages(
    tmp_path: Path,
) -> None:
    source = _catalogue_file(tmp_path, {"fr": [load_fixture("fr_swsh3-136")]})

    selection = price_targets_from_catalogue(source, ["fr", "en", "ja"])

    assert selection.targets == [PriceTarget("fr", "swsh3-136", 483559)]
    assert selection.missing_languages == ["en", "ja"]


def test_price_targets_from_catalogue_counts_cards_without_id_product(
    tmp_path: Path,
) -> None:
    source = _catalogue_file(
        tmp_path,
        {
            "fr": [load_fixture("fr_swsh3-136"), _card("sans-cardmarket", None)],
            "ja": [load_fixture("ja_PMCG6-055")],
        },
    )

    selection = price_targets_from_catalogue(source, ["fr"])

    assert selection.skipped_without_id_product == 1
    assert selection.targets == [PriceTarget("fr", "swsh3-136", 483559)]


def test_price_targets_from_catalogue_without_requested_language(
    tmp_path: Path,
) -> None:
    source = _catalogue_file(tmp_path, {"fr": [load_fixture("fr_swsh3-136")]})

    selection = price_targets_from_catalogue(source, ["en", "ja"])

    assert selection == PriceSelection(
        targets=[], missing_languages=["en", "ja"], skipped_without_id_product=0
    )


def test_price_targets_from_catalogue_without_languages(tmp_path: Path) -> None:
    source = _catalogue_file(tmp_path, {"fr": [load_fixture("fr_swsh3-136")]})

    selection = price_targets_from_catalogue(source, [])

    assert selection == PriceSelection(
        targets=[], missing_languages=[], skipped_without_id_product=0
    )


def test_prices_from_cards_one_record_per_product() -> None:
    cards = {
        "fr": [load_fixture("fr_swsh3-136"), _card("sans-cardmarket", None)],
        "en": [load_fixture("en_swsh3-136")],
    }
    targets = price_targets_from_table(catalogue_table(cards, FETCHED_AT))

    result = prices_from_cards(cards, targets, FETCHED_AT)

    assert result.failed == []
    assert result.items == [
        {
            "language": "fr",
            "card_id": "swsh3-136",
            "id_product": 483559,
            "fetched_at": "2026-10-28T09:30:00+00:00",
            "pricing": load_fixture("fr_swsh3-136")["pricing"],
        }
    ]


def test_prices_from_cards_converts_fetched_at_to_utc() -> None:
    paris = timezone(timedelta(hours=1))
    cards = {"fr": [load_fixture("fr_swsh3-136")]}

    result = prices_from_cards(
        cards,
        [PriceTarget("fr", "swsh3-136", 483559)],
        datetime(2026, 10, 28, 9, 30, tzinfo=paris),
    )

    assert result.items[0]["fetched_at"] == "2026-10-28T08:30:00+00:00"


def test_prices_from_cards_keeps_missing_pricing() -> None:
    cards = {"fr": [{"id": "sans-pricing", "pricing": None}]}

    result = prices_from_cards(
        cards, [PriceTarget("fr", "sans-pricing", 1)], FETCHED_AT
    )

    assert result.items[0]["pricing"] is None


def test_prices_from_cards_reports_absent_cards() -> None:
    cards = {"fr": [load_fixture("fr_swsh3-136")]}
    targets = [
        PriceTarget("fr", "swsh3-136", 483559),
        PriceTarget("ja", "S7D-019", 571601),
    ]

    result = prices_from_cards(cards, targets, FETCHED_AT)

    assert [r["card_id"] for r in result.items] == ["swsh3-136"]
    assert result.failed == ["ja/S7D-019"]


def test_prices_from_cards_matches_fetch_prices(tcgdex_client: TcgdexClient) -> None:
    cards = {
        language: fetch_catalogue(tcgdex_client, language).items
        for language in ("fr", "en", "ja")
    }
    targets = price_targets_from_table(catalogue_table(cards, FETCHED_AT))

    fetched = fetch_prices(tcgdex_client, targets, now=lambda: FETCHED_AT)
    derived = prices_from_cards(cards, targets, FETCHED_AT)

    assert derived == fetched
    assert price_table(derived.items).equals(price_table(fetched.items))
