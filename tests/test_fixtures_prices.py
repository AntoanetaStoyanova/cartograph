import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tests.conftest import FIXTURES_DIR

SAMPLE_DIR = Path(__file__).parents[1] / "dbt" / "sample" / "snapshots"


def _pricing_numbers(node: Any) -> list[float]:
    """Numbers found under every ``pricing`` key, at any depth."""
    if isinstance(node, dict):
        found: list[float] = []
        for key, value in node.items():
            if key == "pricing":
                found += _numbers(value)
            else:
                found += _pricing_numbers(value)
        return found
    if isinstance(node, list):
        return [v for item in node for v in _pricing_numbers(item)]
    return []


def _numbers(node: Any, skip: str = "idProduct") -> list[float]:
    """Every price nested in ``node``: floats and ints, the ``skip`` key aside."""
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        return [node]
    if isinstance(node, dict):
        return [
            v
            for key, value in node.items()
            if key != skip
            for v in _numbers(value, skip)
        ]
    if isinstance(node, list):
        return [v for item in node for v in _numbers(item, skip)]
    return []


def _is_fictitious(value: float) -> bool:
    """Fictitious prices are ``n + 0.37`` with ``n`` an integer >= 4000."""
    cents = round(value * 100)
    return cents % 100 == 37 and cents >= 400_000


def _real_looking(path: Path) -> list[str]:
    """File name repeated once per price outside the fictitious set."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [path.name for v in _pricing_numbers(data) if not _is_fictitious(v)]


@pytest.mark.parametrize(
    "path", sorted(FIXTURES_DIR.glob("*.json")), ids=lambda p: p.name
)
@pytest.mark.regle("R-QUA-04")
def test_fixture_prices_are_fictitious(path: Path) -> None:
    offending = _real_looking(path)

    assert not offending, f"{len(offending)} prix hors ensemble fictif dans {path.name}"


@pytest.mark.parametrize(
    "cardmarket",
    [{"idProduct": 1, "avg": 4001.37, "low": 2.5}, {"idProduct": 1, "avg": 12}],
    ids=["float", "int"],
)
def test_fixture_with_real_price_is_detected(
    tmp_path: Path, cardmarket: dict[str, Any]
) -> None:
    fixture = tmp_path / "fr_card.json"
    pricing = {"cardmarket": cardmarket}
    fixture.write_text(json.dumps({"id": "x", "pricing": pricing}), encoding="utf-8")

    assert _real_looking(fixture) == ["fr_card.json"]


def test_fixtures_contain_priced_cards() -> None:
    values = [
        v
        for path in FIXTURES_DIR.glob("*.json")
        for v in _pricing_numbers(json.loads(path.read_text(encoding="utf-8")))
    ]

    assert len(values) > 50


def _parquet_numbers(path: Path) -> list[float]:
    """``cm_*`` values and TCGplayer numbers (``productId`` aside) of a price file."""
    table = pq.read_table(path)
    found: list[float] = []
    for field in table.schema:
        if field.name.startswith("cm_") and pa.types.is_floating(field.type):
            found += table.column(field.name).drop_null().to_pylist()
    for raw in table.column("tcgplayer_json").drop_null().to_pylist():
        found += _numbers(json.loads(raw), skip="productId")
    return found


def _real_looking_parquet(path: Path) -> list[str]:
    """File name repeated once per price neither ``0`` nor fictitious."""
    return [
        path.name for v in _parquet_numbers(path) if v != 0 and not _is_fictitious(v)
    ]


@pytest.mark.parametrize(
    "path", sorted(SAMPLE_DIR.glob("prices-*.parquet")), ids=lambda p: p.name
)
@pytest.mark.regle("R-QUA-04")
def test_sample_prices_are_fictitious(path: Path) -> None:
    offending = _real_looking_parquet(path)

    assert not offending, f"{len(offending)} prix hors ensemble fictif dans {path.name}"


@pytest.mark.parametrize(
    ("cm_avg", "tcgplayer"),
    [
        (12.5, None),
        (None, {"normal": {"marketPrice": 3.2, "productId": 4001}}),
        (None, {"normal": {"lowPrice": 12, "productId": 4001}}),
    ],
    ids=["cardmarket", "tcgplayer-float", "tcgplayer-int"],
)
@pytest.mark.regle("R-QUA-04")
def test_sample_with_real_price_is_detected(
    tmp_path: Path, cm_avg: float | None, tcgplayer: dict[str, Any] | None
) -> None:
    path = tmp_path / "prices-2026-11-18.parquet"
    table = pa.table(
        {
            "cm_avg": pa.array([cm_avg, 4001.37, 0.0], pa.float64()),
            "tcgplayer_json": pa.array(
                [None if tcgplayer is None else json.dumps(tcgplayer), None, None],
                pa.string(),
            ),
        }
    )
    pq.write_table(table, path)

    assert _real_looking_parquet(path) == ["prices-2026-11-18.parquet"]


def test_sample_contains_prices() -> None:
    values = [
        v
        for path in SAMPLE_DIR.glob("prices-*.parquet")
        for v in _parquet_numbers(path)
    ]

    assert len(values) > 50
