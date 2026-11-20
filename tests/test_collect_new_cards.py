from datetime import UTC, datetime
from pathlib import Path

import pytest

from cartograph.bin.collect.prices import PriceTarget, new_card_targets
from cartograph.bin.collect.snapshot import (
    catalogue_table,
    latest_catalogue,
)
from tests.conftest import load_fixture

FETCHED_AT = datetime(2026, 11, 16, 3, 17, tzinfo=UTC)


def test_new_card_targets_exclude_known_products(tmp_path: Path) -> None:
    table = catalogue_table(
        {
            "fr": [load_fixture("fr_swsh3-136")],
            "ja": [load_fixture("ja_SV7-065"), load_fixture("ja_PMCG6-055")],
        },
        FETCHED_AT,
    )
    known = [PriceTarget("en", "swsh3-136", 483559)]

    assert new_card_targets(table, known) == [PriceTarget("ja", "SV7-065", 779079)]


@pytest.mark.regle("R-COL-07")
def test_latest_catalogue_ignores_new_cards(tmp_path: Path) -> None:
    (tmp_path / "cards-2026-11-16.parquet").touch()
    (tmp_path / "new-cards-2026-11-18.parquet").touch()

    assert latest_catalogue(tmp_path) == tmp_path / "cards-2026-11-16.parquet"
