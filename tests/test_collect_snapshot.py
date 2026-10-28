import copy
import gzip
import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, BinaryIO

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from cartograph.bin.collect.snapshot import (
    CARD_SCHEMA,
    PRICE_SCHEMA,
    _write_atomic,
    card_table,
    price_table,
    snapshot_paths,
    strip_prices,
    write_json_gz,
    write_parquet,
)
from tests.conftest import load_fixture, price_values


def _table() -> pa.Table:
    return pa.table(
        {
            "card_id": ["swsh3-136", "exu-?", "swsh3-136", "exu-?"],
            "language": ["fr", "en", "en", "fr"],
            "value": [1, 2, 3, 4],
        }
    )


def test_snapshot_paths_are_dated(tmp_path: Path) -> None:
    paths = snapshot_paths(tmp_path, date(2026, 10, 28))

    assert paths.cards == tmp_path / "snapshots" / "cards-2026-10-28.parquet"
    assert paths.prices == tmp_path / "snapshots" / "prices-2026-10-28.parquet"
    assert paths.raw_cards == tmp_path / "raw" / "cards-2026-10-28.json.gz"
    assert paths.raw_prices == tmp_path / "raw" / "prices-2026-10-28.json.gz"
    assert paths.summary == tmp_path / "runs" / "collect-2026-10-28.json"


def test_write_parquet_sorts_and_compresses(tmp_path: Path) -> None:
    path = tmp_path / "snapshots" / "t.parquet"

    size = write_parquet(_table(), path, ["card_id", "language"])

    assert size == path.stat().st_size
    written = pq.read_table(path)
    assert written.column("card_id").to_pylist() == [
        "exu-?",
        "exu-?",
        "swsh3-136",
        "swsh3-136",
    ]
    assert written.column("language").to_pylist() == ["en", "fr", "en", "fr"]
    assert written.column("value").to_pylist() == [2, 4, 3, 1]
    column = pq.ParquetFile(path).metadata.row_group(0).column(0)
    assert column.compression == "ZSTD"


def test_write_parquet_replaces_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "t.parquet"
    write_parquet(_table(), path, ["card_id"])

    write_parquet(_table().slice(0, 1), path, ["card_id"])

    assert pq.read_table(path).num_rows == 1


def test_write_parquet_leaves_no_temporary_file(tmp_path: Path) -> None:
    path = tmp_path / "t.parquet"

    write_parquet(_table(), path, ["card_id"])

    assert list(tmp_path.iterdir()) == [path]


def test_write_atomic_failure_keeps_previous_file(tmp_path: Path) -> None:
    path = tmp_path / "t.parquet"
    write_parquet(_table(), path, ["card_id"])

    def fail(file: BinaryIO) -> None:
        file.write(b"partial")
        raise OSError("disque plein")

    with pytest.raises(OSError, match="disque plein"):
        _write_atomic(path, fail)

    assert pq.read_table(path).num_rows == 4
    assert list(tmp_path.iterdir()) == [path]


def test_write_json_gz_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "raw" / "cards.json.gz"
    payload = {"fr": [{"id": "exu-?", "name": "Zarbi ?"}]}

    size = write_json_gz(payload, path)

    assert size == path.stat().st_size
    with gzip.open(path, "rt", encoding="utf-8") as file:
        assert json.load(file) == payload
    assert list(path.parent.iterdir()) == [path]


def _price_record(language: str, card_id: str, pricing: Any) -> dict[str, Any]:
    return {
        "language": language,
        "card_id": card_id,
        "id_product": 483559,
        "fetched_at": "2026-10-28T09:30:00.123456+00:00",
        "pricing": pricing,
    }


def test_price_table_matches_schema() -> None:
    records = [
        _price_record("fr", "swsh3-136", load_fixture("fr_swsh3-136")["pricing"]),
        _price_record("ja", "S7D-019", load_fixture("ja_S7D-019")["pricing"]),
    ]

    table = price_table(records)

    assert table.schema == PRICE_SCHEMA
    assert table.num_rows == 2
    row = table.to_pylist()[0]
    assert row["fetched_at"] == datetime(2026, 10, 28, 9, 30, 0, 123456, tzinfo=UTC)
    assert row["cm_updated"] == datetime(2026, 10, 27, 22, 8, 34, 18000, tzinfo=UTC)
    assert row["cm_unit"] == "EUR"
    assert row["cm_avg"] == 4022.37
    assert row["cm_avg30"] == 4027.37
    assert row["tcgplayer_json"] is None


def test_price_table_maps_holo_fields() -> None:
    pricing = load_fixture("fr_swsh3-136")["pricing"]

    row = price_table([_price_record("fr", "swsh3-136", pricing)]).to_pylist()[0]

    assert row["cm_avg_holo"] == 4028.37
    assert row["cm_low_holo"] == 4029.37
    assert row["cm_trend_holo"] == 4030.37
    assert row["cm_avg1_holo"] == 4031.37
    assert row["cm_avg7_holo"] == 4032.37
    assert row["cm_avg30_holo"] == 4033.37


def test_price_table_missing_fields_are_null() -> None:
    records = [
        _price_record("ja", "a", None),
        _price_record("ja", "b", load_fixture("ja_PMCG6-055")["pricing"]),
        _price_record("ja", "c", {"cardmarket": {"avg": 4999}, "tcgplayer": None}),
    ]

    table = price_table(records)

    assert table.schema == PRICE_SCHEMA
    rows = table.to_pylist()
    price_columns = [name for name in PRICE_SCHEMA.names if name.startswith("cm_")]
    assert all(rows[0][name] is None for name in price_columns)
    assert all(rows[1][name] is None for name in price_columns)
    assert rows[2]["cm_avg"] == 4999.0
    assert rows[2]["cm_low"] is None
    assert rows[2]["cm_updated"] is None


def test_price_table_serializes_tcgplayer() -> None:
    tcgplayer = {"unit": "USD", "holofoil": {"marketPrice": 4999.37}}
    record = _price_record("en", "a", {"cardmarket": None, "tcgplayer": tcgplayer})

    row = price_table([record]).to_pylist()[0]

    assert json.loads(row["tcgplayer_json"]) == tcgplayer


def test_price_table_logs_unknown_field_names_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    cardmarket = {"avg": 4001.37, "avg-reverse": 4998.37, "low-reverse": 4997.37}
    records = [
        _price_record("fr", card_id, {"cardmarket": cardmarket}) for card_id in "ab"
    ]

    with caplog.at_level(logging.INFO):
        price_table(records)

    unknown = [r.getMessage() for r in caplog.records if "inconnus" in r.getMessage()]
    assert len(unknown) == 1
    assert "avg-reverse" in unknown[0]
    assert "low-reverse" in unknown[0]
    assert "4998.37" not in caplog.text
    assert "4997.37" not in caplog.text


def test_price_table_empty_records() -> None:
    table = price_table([])

    assert table.schema == PRICE_SCHEMA
    assert table.num_rows == 0


FR_CARDS = ["fr_exu-%3F", "fr_pop9-1", "fr_swsh3-136"]
JA_CARDS = ["ja_PMCG6-055", "ja_S7D-019", "ja_SV7-065"]
FETCHED_AT = datetime(2026, 10, 28, 9, 30, tzinfo=UTC)


def test_strip_prices_removes_nested_pricing() -> None:
    card = load_fixture("fr_swsh3-136")
    assert "pricing" in card["variants_detailed"][0]

    stripped = strip_prices(card)

    assert "pricing" not in stripped
    assert all("pricing" not in v for v in stripped["variants_detailed"])
    assert stripped["variants_detailed"][0]["thirdParty"]["cardmarket"] == 483559
    assert stripped["name"] == card["name"]


def test_strip_prices_does_not_modify_input() -> None:
    card = load_fixture("fr_swsh3-136")
    original = copy.deepcopy(card)

    strip_prices(card)

    assert card == original


def test_card_table_matches_schema() -> None:
    cards = [load_fixture(name) for name in FR_CARDS]

    table = card_table(cards, "fr", FETCHED_AT)

    assert table.schema == CARD_SCHEMA
    assert table.num_rows == 3
    row = table.to_pylist()[2]
    assert row["language"] == "fr"
    assert row["card_id"] == "swsh3-136"
    assert row["local_id"] == "136"
    assert row["name"] == "Fouinar"
    assert row["set_id"] == "swsh3"
    assert row["set_name"] == "Ténèbres Embrasées"
    assert row["rarity"] == "Peu Commune"
    assert row["category"] == "Pokémon"
    assert row["illustrator"] == "tetsuya koizumi"
    assert row["image"] == "https://assets.tcgdex.net/fr/swsh/swsh3/136"
    assert row["updated"] == datetime(2026, 7, 1, 20, 27, 44, tzinfo=UTC)
    assert row["fetched_at"] == FETCHED_AT
    assert json.loads(row["raw_json"]) == strip_prices(cards[2])


def test_card_table_contains_no_price() -> None:
    cards = [load_fixture(name) for name in FR_CARDS + JA_CARDS]
    prices = price_values(cards)
    assert "4022.37" in prices

    table = card_table(cards, "fr", FETCHED_AT)

    serialized = json.dumps(table.to_pylist(), default=str, ensure_ascii=False)
    assert not [price for price in prices if price in serialized]
    assert "pricing" not in serialized


def test_card_table_keeps_id_product() -> None:
    cards = [load_fixture(name) for name in JA_CARDS]

    rows = card_table(cards, "ja", FETCHED_AT).to_pylist()

    assert [row["id_product"] for row in rows] == [None, 571601, 779079]


def test_card_table_empty_cards() -> None:
    table = card_table([], "fr", FETCHED_AT)

    assert table.schema == CARD_SCHEMA
    assert table.num_rows == 0
