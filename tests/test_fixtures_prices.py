import json
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import FIXTURES_DIR


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


def _numbers(node: Any) -> list[float]:
    """Every price nested in ``node``: floats and ints, ``idProduct`` aside."""
    if isinstance(node, (int, float)) and not isinstance(node, bool):
        return [node]
    if isinstance(node, dict):
        return [
            v
            for key, value in node.items()
            if key != "idProduct"
            for v in _numbers(value)
        ]
    if isinstance(node, list):
        return [v for item in node for v in _numbers(item)]
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
