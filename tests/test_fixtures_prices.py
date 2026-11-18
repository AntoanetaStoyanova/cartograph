import json
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import FIXTURES_DIR


def _pricing_floats(node: Any) -> list[float]:
    """Floats found under every ``pricing`` key, at any depth."""
    if isinstance(node, dict):
        found: list[float] = []
        for key, value in node.items():
            if key == "pricing":
                found += _floats(value)
            else:
                found += _pricing_floats(value)
        return found
    if isinstance(node, list):
        return [v for item in node for v in _pricing_floats(item)]
    return []


def _floats(node: Any) -> list[float]:
    """Every float nested in ``node``."""
    if isinstance(node, float):
        return [node]
    if isinstance(node, dict):
        return [v for value in node.values() for v in _floats(value)]
    if isinstance(node, list):
        return [v for item in node for v in _floats(item)]
    return []


def _is_fictitious(value: float) -> bool:
    """Fictitious prices are ``n + 0.37`` with ``n`` an integer >= 4000."""
    cents = round(value * 100)
    return cents % 100 == 37 and cents >= 400_000


def _real_looking(path: Path) -> list[str]:
    """File name repeated once per price outside the fictitious set."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [path.name for v in _pricing_floats(data) if not _is_fictitious(v)]


@pytest.mark.parametrize(
    "path", sorted(FIXTURES_DIR.glob("*.json")), ids=lambda p: p.name
)
def test_fixture_prices_are_fictitious(path: Path) -> None:
    offending = _real_looking(path)

    assert not offending, f"{len(offending)} prix hors ensemble fictif dans {path.name}"


def test_fixture_with_real_price_is_detected(tmp_path: Path) -> None:
    fixture = tmp_path / "fr_card.json"
    pricing = {"cardmarket": {"idProduct": 1, "avg": 4001.37, "low": 2.5}}
    fixture.write_text(json.dumps({"id": "x", "pricing": pricing}), encoding="utf-8")

    assert _real_looking(fixture) == ["fr_card.json"]


def test_fixtures_contain_priced_cards() -> None:
    values = [
        v
        for path in FIXTURES_DIR.glob("*.json")
        for v in _pricing_floats(json.loads(path.read_text(encoding="utf-8")))
    ]

    assert len(values) > 50
