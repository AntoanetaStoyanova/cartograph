from datetime import UTC, date, datetime, timedelta
from typing import Any

import pyarrow as pa

from cartograph.bin.collect.catalogue import ListingDiff
from cartograph.bin.collect.incremental import (
    apply_listing,
    card_changes_table,
    changed_cards,
    count_changes,
    merge_catalogue,
    rotation_ids,
)
from cartograph.bin.collect.prices import PriceTarget
from cartograph.bin.collect.snapshot import CARD_SCHEMA, CHANGE_SCHEMA, catalogue_table
from tests.conftest import load_fixture, price_values

FETCHED_AT = datetime(2026, 11, 16, 3, 17, tzinfo=UTC)


def _base() -> Any:
    return catalogue_table(
        {
            "fr": [load_fixture("fr_swsh3-136"), load_fixture("fr_pop9-1")],
            "ja": [load_fixture("ja_SV7-065")],
        },
        FETCHED_AT,
    )


def test_changed_cards_separates_changed_and_identical() -> None:
    fresh = {**load_fixture("fr_swsh3-136"), "updated": "2026-11-18T08:00:00Z"}
    corrected = {**load_fixture("ja_SV7-065"), "rarity": "SAR"}

    changed, identical = changed_cards(_base(), {"fr": [fresh], "ja": [corrected]})

    assert changed == {"ja": [corrected]}
    assert identical == {"fr": ["swsh3-136"]}


def test_changed_cards_card_absent_from_base_is_changed() -> None:
    card = load_fixture("en_swsh3-136")

    changed, identical = changed_cards(_base(), {"en": [card]})

    assert changed == {"en": [card]}
    assert identical == {}


def test_changed_cards_nothing_read() -> None:
    assert changed_cards(_base(), {}) == ({}, {})


def _aged_base() -> pa.Table:
    table = catalogue_table(
        {
            "fr": [load_fixture(f"fr_{card_id}") for card_id in ("exu-%3F", "pop9-1")],
            "ja": [load_fixture(f"ja_{card_id}") for card_id in ("S7D-019", "SV7-065")],
            "en": [load_fixture("en_swsh3-136")],
        },
        FETCHED_AT,
    )
    days = {"exu-%3F": 3, "pop9-1": 1, "S7D-019": 3, "SV7-065": 2, "swsh3-136": 5}
    fetched_at = [
        FETCHED_AT - timedelta(days=days[card_id])
        for card_id in table.column("card_id").to_pylist()
    ]
    removed_on = [
        date(2026, 11, 17) if card_id == "swsh3-136" else None
        for card_id in table.column("card_id").to_pylist()
    ]
    table = table.set_column(
        table.schema.get_field_index("fetched_at"),
        "fetched_at",
        pa.array(fetched_at, table.schema.field("fetched_at").type),
    )
    return table.set_column(
        table.schema.get_field_index("removed_on"),
        "removed_on",
        pa.array(removed_on, pa.date32()),
    )


def test_rotation_ids_oldest_first_without_targets_and_removed() -> None:
    targets = [PriceTarget("ja", "S7D-019", 571601)]

    rotated = rotation_ids(_aged_base(), targets, 2)

    assert rotated == {"fr": ["exu-%3F"], "ja": ["SV7-065"]}


def test_rotation_ids_ties_ordered_by_card_id() -> None:
    rotated = rotation_ids(_aged_base(), [], 1)

    assert rotated == {"ja": ["S7D-019"]}


def test_rotation_ids_size_larger_than_base() -> None:
    rotated = rotation_ids(_aged_base(), [], 100)

    assert rotated == {
        "fr": ["exu-%3F", "pop9-1"],
        "ja": ["S7D-019", "SV7-065"],
    }


def test_rotation_ids_size_zero() -> None:
    assert rotation_ids(_aged_base(), [], 0) == {}


DAY = date(2026, 11, 18)
READ_AT = datetime(2026, 11, 18, 4, 0, tzinfo=UTC)


def _rows(table: pa.Table) -> dict[tuple[str, str], dict[str, Any]]:
    return {(row["language"], row["card_id"]): row for row in table.to_pylist()}


def test_apply_listing_sets_and_clears_removed_on() -> None:
    base = _aged_base()
    diff = ListingDiff(
        new={}, removed={"fr": ["pop9-1"]}, reappeared={"en": ["swsh3-136"]}
    )

    rows = _rows(apply_listing(base, diff, DAY))

    assert rows[("fr", "pop9-1")]["removed_on"] == DAY
    assert rows[("en", "swsh3-136")]["removed_on"] is None
    assert rows[("fr", "exu-%3F")]["removed_on"] is None


def test_merge_catalogue_updates_base() -> None:
    base = apply_listing(
        _aged_base(),
        ListingDiff(new={}, removed={"fr": ["pop9-1"]}, reappeared={}),
        DAY,
    )
    corrected = {**load_fixture("ja_SV7-065"), "rarity": "SAR"}
    new = load_fixture("ja_PMCG6-055")

    merged = merge_catalogue(
        base, {"ja": [corrected, new]}, {"fr": ["exu-%3F"]}, READ_AT
    )

    assert merged.schema == CARD_SCHEMA
    rows = _rows(merged)
    assert len(rows) == merged.num_rows == 6
    assert rows[("ja", "SV7-065")]["rarity"] == "SAR"
    assert rows[("ja", "SV7-065")]["fetched_at"] == READ_AT
    assert rows[("ja", "PMCG6-055")]["removed_on"] is None
    assert rows[("fr", "exu-%3F")]["fetched_at"] == READ_AT
    assert rows[("fr", "pop9-1")]["removed_on"] == DAY
    unread = _rows(base)[("ja", "S7D-019")]
    assert rows[("ja", "S7D-019")] == unread


def test_merge_catalogue_keeps_removed_on_of_replaced_card() -> None:
    base = _aged_base()

    merged = merge_catalogue(base, {"en": [load_fixture("en_swsh3-136")]}, {}, READ_AT)

    assert _rows(merged)[("en", "swsh3-136")]["removed_on"] == date(2026, 11, 17)


def test_card_changes_table_lists_each_change() -> None:
    base = _aged_base()
    listed = apply_listing(
        base,
        ListingDiff(
            new={}, removed={"fr": ["pop9-1"]}, reappeared={"en": ["swsh3-136"]}
        ),
        DAY,
    )
    corrected = {**load_fixture("en_swsh3-136"), "rarity": "Rare"}
    merged = merge_catalogue(
        listed,
        {"en": [corrected], "ja": [load_fixture("ja_PMCG6-055")]},
        {"ja": ["SV7-065"]},
        READ_AT,
    )

    changes = card_changes_table(base, merged)

    assert changes.schema == CHANGE_SCHEMA
    assert sorted(
        zip(
            changes.column("change_type").to_pylist(),
            changes.column("card_id").to_pylist(),
            strict=True,
        )
    ) == [
        ("new", "PMCG6-055"),
        ("reappeared", "swsh3-136"),
        ("removed", "pop9-1"),
        ("updated", "swsh3-136"),
    ]
    assert count_changes(changes) == {
        "new": 1,
        "updated": 1,
        "removed": 1,
        "reappeared": 1,
    }
    prices = price_values([load_fixture("en_swsh3-136"), load_fixture("ja_PMCG6-055")])
    text = str(changes.to_pylist())
    assert not [price for price in prices if price in text]
    assert "pricing" not in text


def test_card_changes_table_without_change() -> None:
    base = _aged_base()

    changes = card_changes_table(base, merge_catalogue(base, {}, {}, READ_AT))

    assert changes.num_rows == 0
    assert count_changes(changes) == dict.fromkeys(
        ("new", "updated", "removed", "reappeared"), 0
    )
