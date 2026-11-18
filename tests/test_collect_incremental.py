from datetime import UTC, datetime
from typing import Any

from cartograph.bin.collect.incremental import changed_cards
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
