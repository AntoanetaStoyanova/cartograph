from datetime import UTC, date, datetime, timedelta
from typing import Any

import pyarrow as pa

from cartograph.bin.collect.incremental import changed_cards, rotation_ids
from cartograph.bin.collect.prices import PriceTarget
from cartograph.bin.collect.snapshot import catalogue_table
from tests.conftest import load_fixture

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
