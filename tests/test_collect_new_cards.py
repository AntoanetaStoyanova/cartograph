from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx

from cartograph.bin.collect.catalogue import new_card_ids
from cartograph.bin.collect.prices import PriceTarget, new_card_targets
from cartograph.bin.collect.snapshot import (
    SORT_BY,
    catalogue_table,
    latest_catalogue,
    write_parquet,
)
from tests.conftest import fixture_route, load_fixture, mock_client

FETCHED_AT = datetime(2026, 11, 16, 3, 17, tzinfo=UTC)


def _catalogue(tmp_path: Path, cards: dict[str, list[str]]) -> Path:
    fiches = {
        language: [load_fixture(f"{language}_{card_id}") for card_id in card_ids]
        for language, card_ids in cards.items()
    }
    path = tmp_path / "cards-2026-11-16.parquet"
    write_parquet(catalogue_table(fiches, FETCHED_AT), path, SORT_BY)
    return path


def _recording(requested: list[str]) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        return fixture_route(request)

    return handler


def test_new_card_ids_are_listed_minus_catalogue(tmp_path: Path) -> None:
    catalogue = _catalogue(
        tmp_path,
        {"fr": ["exu-%3F", "pop9-1"], "ja": ["PMCG6-055", "S7D-019", "SV7-065"]},
    )
    requested: list[str] = []

    with mock_client(_recording(requested)) as client:
        new = new_card_ids(client, ["fr", "ja"], catalogue)

    assert new == {"fr": ["swsh3-136"], "ja": []}
    assert requested == ["/v2/fr/cards", "/v2/ja/cards"]


def test_new_card_ids_skip_language_absent_from_catalogue(tmp_path: Path) -> None:
    catalogue = _catalogue(tmp_path, {"fr": ["exu-%3F", "pop9-1", "swsh3-136"]})
    requested: list[str] = []

    with mock_client(_recording(requested)) as client:
        new = new_card_ids(client, ["fr", "en"], catalogue)

    assert new == {"fr": [], "en": []}
    assert requested == ["/v2/fr/cards"]


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


def test_latest_catalogue_ignores_new_cards(tmp_path: Path) -> None:
    (tmp_path / "cards-2026-11-16.parquet").touch()
    (tmp_path / "new-cards-2026-11-18.parquet").touch()

    assert latest_catalogue(tmp_path) == tmp_path / "cards-2026-11-16.parquet"
