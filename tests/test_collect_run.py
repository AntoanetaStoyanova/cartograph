import json
import logging
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pyarrow.parquet as pq
import pytest

from cartograph.bin.collect import batch, run
from cartograph.bin.collect.client import TcgdexClient
from cartograph.bin.collect.run import collect, main
from cartograph.bin.collect.snapshot import snapshot_paths
from cartograph.config import LANGUAGES, ROTATION_SIZE
from tests.conftest import fixture_route, load_fixture, mock_client, price_values

DAY = date(2026, 10, 28)
CARDS = {
    "fr": ["fr_exu-%3F", "fr_pop9-1", "fr_swsh3-136"],
    "en": ["en_exu-%3F", "en_pop9-1", "en_swsh3-136"],
    "ja": ["ja_PMCG6-055", "ja_S7D-019", "ja_SV7-065"],
}


def _clock(day: date = DAY) -> Callable[[], datetime]:
    return lambda: datetime.combine(day, time(9, 30), UTC)


def _collect(
    client: TcgdexClient,
    data_dir: Path,
    day: date = DAY,
    catalogue: bool = True,
    prices: bool = True,
    languages: Sequence[str] = LANGUAGES,
) -> Any:
    return collect(client, data_dir, catalogue, prices, languages, now=_clock(day))


def _steps(summary: dict[str, object]) -> dict[str, dict[str, object]]:
    steps = summary["steps"]
    assert isinstance(steps, dict)
    return steps


def test_collect_with_catalogue_writes_all_files(
    tcgdex_client: TcgdexClient, tmp_path: Path
) -> None:
    summary = _collect(tcgdex_client, tmp_path)

    paths = snapshot_paths(tmp_path, DAY)
    for path in [
        paths.cards,
        paths.sets,
        paths.prices,
        paths.raw_cards,
        paths.raw_prices,
    ]:
        assert path.exists()
    assert json.loads(paths.summary.read_text(encoding="utf-8")) == summary
    steps = _steps(summary)
    assert steps["catalogue"]["status"] == "ok"
    assert steps["catalogue"]["fetched"] == 9
    assert steps["sets"]["status"] == "ok"
    assert steps["sets"]["fetched"] == 6
    assert steps["prices"]["status"] == "ok"
    assert steps["prices"]["source"] == paths.cards.name
    assert steps["prices"]["skipped_without_id_product"] == 1
    assert pq.read_table(paths.cards).num_rows == 9
    prices = pq.read_table(paths.prices)
    assert prices.num_rows == 5
    assert prices.column("card_id").to_pylist() == sorted(
        prices.column("card_id").to_pylist()
    )


def test_collect_interrupted_prices_keep_catalogue_summary(
    tcgdex_client: TcgdexClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def interrupted(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("délai dépassé")

    monkeypatch.setattr(run, "_collect_prices", interrupted)

    with pytest.raises(RuntimeError):
        _collect(tcgdex_client, tmp_path)

    paths = snapshot_paths(tmp_path, DAY)
    summary = json.loads(paths.summary.read_text(encoding="utf-8"))
    steps = _steps(summary)
    assert steps["catalogue"]["status"] == "ok"
    assert [f["name"] for f in steps["catalogue"]["files"]] == [
        paths.cards.name,
        paths.raw_cards.name,
    ]
    assert [f["name"] for f in steps["sets"]["files"]] == [paths.sets.name]
    assert steps["prices"]["status"] == "failed"
    assert steps["prices"]["error"] == "étape interrompue avant la fin"


@pytest.mark.parametrize(
    ("catalogue", "prices", "writes"),
    [(True, True, 3), (True, False, 2), (False, True, 3)],
)
def test_collect_writes_summary_after_each_step(
    tcgdex_client: TcgdexClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    catalogue: bool,
    prices: bool,
    writes: int,
) -> None:
    _collect(tcgdex_client, tmp_path, day=date(2026, 10, 25), prices=False)
    summaries: list[Path] = []
    write_json = run.write_json

    def spy(obj: Any, path: Path) -> int:
        summaries.append(path)
        return write_json(obj, path)

    monkeypatch.setattr(run, "write_json", spy)

    _collect(tcgdex_client, tmp_path, catalogue=catalogue, prices=prices)

    assert summaries == [snapshot_paths(tmp_path, DAY).summary] * writes


def test_collect_sets_stored_with_release_date(
    tcgdex_client: TcgdexClient, tmp_path: Path
) -> None:
    _collect(tcgdex_client, tmp_path, prices=False)

    table = pq.read_table(snapshot_paths(tmp_path, DAY).sets)
    assert table.num_rows == 6
    assert table.column("set_id").to_pylist() == sorted(
        table.column("set_id").to_pylist()
    )
    assert None not in table.column("release_date").to_pylist()


def test_collect_interrupted_sets_keep_catalogue_summary(
    tcgdex_client: TcgdexClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def interrupted(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("délai dépassé")

    monkeypatch.setattr(run, "_collect_sets", interrupted)

    with pytest.raises(RuntimeError):
        _collect(tcgdex_client, tmp_path)

    summary = json.loads(snapshot_paths(tmp_path, DAY).summary.read_text("utf-8"))
    steps = _steps(summary)
    assert steps["catalogue"]["status"] == "ok"
    assert steps["sets"]["error"] == "étape interrompue avant la fin"
    assert steps["prices"]["error"] == "étape interrompue avant la fin"


def test_collect_failed_sets_keep_catalogue_and_prices(tmp_path: Path) -> None:
    with mock_client(_down("/v2/ja/sets")) as client:
        summary = _collect(client, tmp_path)

    paths = snapshot_paths(tmp_path, DAY)
    steps = _steps(summary)
    assert steps["sets"]["status"] == "failed"
    assert "500" in str(steps["sets"]["error"])
    assert steps["sets"]["files"] == []
    assert not paths.sets.exists()
    assert steps["catalogue"]["status"] == "ok"
    assert steps["prices"]["status"] == "ok"
    assert paths.cards.exists()
    assert paths.prices.exists()


def test_collect_records_failed_sets_with_language(tmp_path: Path) -> None:
    with mock_client(_down("/v2/fr/sets/swsh3")) as client:
        summary = _collect(client, tmp_path, prices=False)

    sets = _steps(summary)["sets"]
    assert sets["status"] == "ok"
    assert sets["failed"] == ["fr/swsh3"]
    assert pq.read_table(snapshot_paths(tmp_path, DAY).sets).num_rows == 5


def test_collect_bad_set_fails_sets_only(tmp_path: Path) -> None:
    handler = _with_card("/v2/en/sets/swsh3", {"releaseDate": "14/08/2020"})

    with mock_client(handler) as client:
        summary = _collect(client, tmp_path)

    steps = _steps(summary)
    assert steps["sets"]["status"] == "failed"
    assert "conversion" in str(steps["sets"]["error"])
    assert not snapshot_paths(tmp_path, DAY).sets.exists()
    assert steps["catalogue"]["status"] == "ok"
    assert steps["prices"]["status"] == "ok"


def test_collect_without_catalogue_collects_sets_first(tmp_path: Path) -> None:
    _old_catalogue(tmp_path, "SV7-065")
    requested: list[str] = []

    def recording(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        return fixture_route(request)

    with mock_client(recording) as client:
        summary = _collect(client, tmp_path, catalogue=False)

    steps = _steps(summary)
    assert steps["sets"]["status"] == "ok"
    assert steps["sets"]["fetched"] == 6
    assert pq.read_table(snapshot_paths(tmp_path, DAY).sets).num_rows == 6
    last_set = max(i for i, path in enumerate(requested) if "/sets" in path)
    assert last_set < requested.index("/v2/fr/cards")
    assert steps["new_cards"]["status"] == "ok"
    assert steps["prices"]["status"] == "ok"


def test_collect_failed_sets_keep_new_cards_and_prices(tmp_path: Path) -> None:
    _old_catalogue(tmp_path, "SV7-065")

    with mock_client(_down("/v2/ja/sets")) as client:
        summary = _collect(client, tmp_path, catalogue=False)

    steps = _steps(summary)
    assert steps["sets"]["status"] == "failed"
    assert not snapshot_paths(tmp_path, DAY).sets.exists()
    assert steps["new_cards"]["status"] == "ok"
    assert steps["new_cards"]["fetched"] == 1
    assert steps["prices"]["status"] == "ok"


def test_collect_interrupted_prices_keep_sets_summary(
    tcgdex_client: TcgdexClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _old_catalogue(tmp_path, "SV7-065")

    def interrupted(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("délai dépassé")

    monkeypatch.setattr(run, "_collect_prices", interrupted)

    with pytest.raises(RuntimeError):
        _collect(tcgdex_client, tmp_path, catalogue=False)

    paths = snapshot_paths(tmp_path, DAY)
    steps = _steps(json.loads(paths.summary.read_text(encoding="utf-8")))
    assert [f["name"] for f in steps["sets"]["files"]] == [paths.sets.name]
    assert steps["new_cards"]["status"] == "ok"
    assert steps["prices"]["error"] == "étape interrompue avant la fin"


def _without(*card_ids: str) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        response = fixture_route(request)
        if not request.url.path.endswith("/cards"):
            return response
        kept = [card for card in response.json() if card["id"] not in card_ids]
        return httpx.Response(200, json=kept)

    return handler


def _old_catalogue(tmp_path: Path, *card_ids: str) -> None:
    with mock_client(_without(*card_ids)) as client:
        _collect(client, tmp_path, day=date(2026, 10, 25), prices=False)


def test_collect_new_card_has_card_and_price(tmp_path: Path) -> None:
    _old_catalogue(tmp_path, "SV7-065")
    requested: list[str] = []

    def recording(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        return fixture_route(request)

    with mock_client(recording) as client:
        summary = _collect(client, tmp_path, catalogue=False)

    paths = snapshot_paths(tmp_path, DAY)
    steps = _steps(summary)
    assert steps["new_cards"]["status"] == "ok"
    assert steps["new_cards"]["fetched"] == 1
    assert [f["name"] for f in steps["new_cards"]["files"]] == [
        paths.new_cards.name,
        paths.raw_new_cards.name,
    ]
    assert pq.read_table(paths.new_cards).column("card_id").to_pylist() == ["SV7-065"]
    assert requested.count("/v2/ja/cards/SV7-065") == 1
    prices = pq.read_table(paths.prices)
    assert prices.num_rows == 5
    assert 779079 in prices.column("id_product").to_pylist()
    assert steps["prices"]["status"] == "ok"
    assert steps["prices"]["fetched"] == 5


def test_collect_new_card_with_known_product_is_not_doubled(tmp_path: Path) -> None:
    with mock_client(_without_language_card("fr", "swsh3-136")) as client:
        _collect(client, tmp_path, day=date(2026, 10, 25), prices=False)

    with mock_client(fixture_route) as client:
        summary = _collect(client, tmp_path, catalogue=False)

    assert _steps(summary)["new_cards"]["fetched"] == 1
    ids = pq.read_table(snapshot_paths(tmp_path, DAY).prices).column("id_product")
    assert ids.to_pylist().count(483559) == 1
    assert len(ids) == 5


def _without_language_card(
    language: str, card_id: str
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        response = fixture_route(request)
        if request.url.path != f"/v2/{language}/cards":
            return response
        kept = [card for card in response.json() if card["id"] != card_id]
        return httpx.Response(200, json=kept)

    return handler


def test_collect_new_cards_leak_no_price(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _old_catalogue(tmp_path, "SV7-065")
    prices = price_values(load_fixture("ja_SV7-065"))
    assert prices

    with mock_client(fixture_route) as client, caplog.at_level(logging.DEBUG):
        _collect(client, tmp_path, catalogue=False)

    paths = snapshot_paths(tmp_path, DAY)
    public = json.dumps(pq.read_table(paths.new_cards).to_pylist(), default=str)
    for text in [paths.summary.read_text(encoding="utf-8"), caplog.text, public]:
        assert not [price for price in prices if price in text]
    assert "pricing" not in public


def test_collect_without_new_card_writes_no_file(
    tcgdex_client: TcgdexClient, tmp_path: Path
) -> None:
    _collect(tcgdex_client, tmp_path, day=date(2026, 10, 25), prices=False)

    summary = _collect(tcgdex_client, tmp_path, catalogue=False)

    new_cards = _steps(summary)["new_cards"]
    assert new_cards["status"] == "ok"
    assert new_cards["fetched"] == 0
    assert new_cards["files"] == []
    assert not snapshot_paths(tmp_path, DAY).new_cards.exists()


def test_collect_failed_card_list_keeps_prices(tmp_path: Path) -> None:
    _old_catalogue(tmp_path, "SV7-065")

    with mock_client(_down("/v2/ja/cards")) as client:
        summary = _collect(client, tmp_path, catalogue=False)

    steps = _steps(summary)
    assert steps["new_cards"]["status"] == "failed"
    assert "500" in str(steps["new_cards"]["error"])
    assert steps["prices"]["status"] == "ok"
    assert steps["prices"]["fetched"] == 4
    assert not snapshot_paths(tmp_path, DAY).new_cards.exists()


def test_main_returns_one_when_new_cards_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _old_catalogue(tmp_path, "SV7-065")
    monkeypatch.setattr(run, "TcgdexClient", lambda: mock_client(_down("/v2/ja/cards")))
    monkeypatch.setattr(run, "LOG_DIR", tmp_path / "logs")

    try:
        code = main(["--data-dir", str(tmp_path)])
    finally:
        logger = logging.getLogger("cartograph")
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    assert code == 1


def test_collect_bad_new_card_keeps_raw_and_catalogue_prices(tmp_path: Path) -> None:
    _old_catalogue(tmp_path, "SV7-065")
    handler = _with_card("/v2/ja/cards/SV7-065", {"updated": 12345})

    with mock_client(handler) as client:
        summary = _collect(client, tmp_path, catalogue=False)

    paths = snapshot_paths(tmp_path, DAY)
    steps = _steps(summary)
    assert steps["new_cards"]["status"] == "failed"
    assert "conversion" in str(steps["new_cards"]["error"])
    assert paths.raw_new_cards.exists()
    assert not paths.new_cards.exists()
    assert steps["prices"]["status"] == "ok"
    assert steps["prices"]["fetched"] == 4


def test_collect_catalogue_day_has_no_new_cards_step(
    tcgdex_client: TcgdexClient, tmp_path: Path
) -> None:
    _old_catalogue(tmp_path, "SV7-065")

    summary = _collect(tcgdex_client, tmp_path)

    assert _steps(summary)["new_cards"]["status"] == "skipped"
    assert not snapshot_paths(tmp_path, DAY).new_cards.exists()


def test_collect_prices_uses_latest_catalogue(
    tcgdex_client: TcgdexClient, tmp_path: Path
) -> None:
    _collect(tcgdex_client, tmp_path, day=date(2026, 10, 20), prices=False)
    _collect(tcgdex_client, tmp_path, day=date(2026, 10, 25), prices=False)

    summary = _collect(tcgdex_client, tmp_path, catalogue=False)

    steps = _steps(summary)
    assert steps["catalogue"]["status"] == "skipped"
    assert steps["prices"]["status"] == "ok"
    assert steps["prices"]["source"] == "cards-2026-10-25.parquet"
    assert pq.read_table(snapshot_paths(tmp_path, DAY).prices).num_rows == 5


def test_collect_prices_without_catalogue_fails(
    tcgdex_client: TcgdexClient, tmp_path: Path
) -> None:
    summary = _collect(tcgdex_client, tmp_path, catalogue=False)

    prices = _steps(summary)["prices"]
    assert prices["status"] == "failed"
    assert prices["error"] == "aucun catalogue disponible"
    assert not snapshot_paths(tmp_path, DAY).prices.exists()


def test_collect_failed_language_writes_no_catalogue_but_prices(
    tcgdex_client: TcgdexClient, tmp_path: Path
) -> None:
    _collect(tcgdex_client, tmp_path, day=date(2026, 10, 25), prices=False)

    def ja_list_down(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v2/ja/cards":
            return httpx.Response(503)
        return fixture_route(request)

    with mock_client(ja_list_down) as client:
        summary = _collect(client, tmp_path)

    paths = snapshot_paths(tmp_path, DAY)
    steps = _steps(summary)
    assert steps["catalogue"]["status"] == "failed"
    assert "503" in str(steps["catalogue"]["error"])
    assert not paths.cards.exists()
    assert not paths.raw_cards.exists()
    assert steps["prices"]["status"] == "ok"
    assert steps["prices"]["source"] == "cards-2026-10-25.parquet"
    assert paths.prices.exists()


def _down(*paths: str) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path in paths:
            return httpx.Response(500)
        return fixture_route(request)

    return handler


def test_collect_records_failed_cards_with_language(tmp_path: Path) -> None:
    with mock_client(_down("/v2/ja/cards/S7D-019")) as client:
        summary = _collect(client, tmp_path)

    steps = _steps(summary)
    assert steps["catalogue"]["status"] == "ok"
    assert steps["catalogue"]["failed"] == ["ja/S7D-019"]
    assert steps["prices"]["status"] == "ok"
    assert steps["prices"]["failed"] == []
    assert steps["prices"]["fetched"] == 4


def test_collect_prices_only_records_failed_cards_with_language(
    tcgdex_client: TcgdexClient, tmp_path: Path
) -> None:
    _collect(tcgdex_client, tmp_path, day=date(2026, 10, 25), prices=False)

    with mock_client(_down("/v2/fr/cards/pop9-1")) as client:
        summary = _collect(client, tmp_path, catalogue=False)

    prices = _steps(summary)["prices"]
    assert prices["status"] == "ok"
    assert prices["failed"] == ["fr/pop9-1"]
    assert prices["fetched"] == 4


def test_collect_with_catalogue_requests_each_card_once(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    requested: list[str] = []

    def recording(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        return fixture_route(request)

    with mock_client(recording) as client, caplog.at_level(logging.INFO):
        summary = _collect(client, tmp_path)

    paths = snapshot_paths(tmp_path, DAY)
    prices = _steps(summary)["prices"]
    assert len(requested) == len(set(requested)) == 3 + 9 + 3 + 6
    assert prices["status"] == "ok"
    assert prices["source"] == paths.cards.name
    assert prices["fetched"] == 5
    assert prices["skipped_without_id_product"] == 1
    assert "prix : 5 produits tirés du catalogue du jour" in caplog.text
    assert pq.read_table(paths.prices).num_rows == 5


def test_collect_same_day_replaces_files(
    tcgdex_client: TcgdexClient, tmp_path: Path
) -> None:
    _collect(tcgdex_client, tmp_path)
    files = sorted(tmp_path.rglob("*"))

    _collect(tcgdex_client, tmp_path)

    assert sorted(tmp_path.rglob("*")) == files
    paths = snapshot_paths(tmp_path, DAY)
    assert pq.read_table(paths.cards).num_rows == 9
    assert pq.read_table(paths.prices).num_rows == 5


def test_collect_summary_contains_no_price(
    tcgdex_client: TcgdexClient, tmp_path: Path
) -> None:
    prices = price_values([load_fixture(n) for names in CARDS.values() for n in names])

    _collect(tcgdex_client, tmp_path)

    text = snapshot_paths(tmp_path, DAY).summary.read_text(encoding="utf-8")
    assert not [price for price in prices if price in text]
    assert "pricing" not in text


def test_collect_uses_utc_timestamps(
    tcgdex_client: TcgdexClient, tmp_path: Path
) -> None:
    summary = _collect(tcgdex_client, tmp_path)

    assert (
        summary["started_at"] == datetime(2026, 10, 28, 9, 30, tzinfo=UTC).isoformat()
    )


def test_collect_day_is_utc_date_of_start(
    tcgdex_client: TcgdexClient, tmp_path: Path
) -> None:
    paris = timezone(timedelta(hours=2))
    start = datetime(2026, 10, 29, 0, 30, tzinfo=paris)

    summary = collect(tcgdex_client, tmp_path, True, False, LANGUAGES, lambda: start)

    assert summary["date"] == "2026-10-28"
    assert snapshot_paths(tmp_path, DAY).cards.exists()


def test_collect_prices_stopped_by_outage_writes_no_prices(
    tcgdex_client: TcgdexClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _collect(tcgdex_client, tmp_path, day=date(2026, 10, 25), prices=False)
    monkeypatch.setattr(batch, "MAX_CONSECUTIVE_FAILURES", 2)

    with mock_client(lambda _: httpx.Response(500)) as client:
        summary = _collect(client, tmp_path, catalogue=False)

    prices = _steps(summary)["prices"]
    assert prices["status"] == "failed"
    assert "2 échecs d'affilée" in str(prices["error"])
    assert not snapshot_paths(tmp_path, DAY).prices.exists()


def _with_card(
    path: str, change: dict[str, Any]
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        response = fixture_route(request)
        if request.url.path != path:
            return response
        return httpx.Response(200, json=_patched(response.json(), change))

    return handler


def _patched(card: Any, change: dict[str, Any]) -> Any:
    for key, value in change.items():
        target = card
        *parents, leaf = key.split(".")
        for parent in parents:
            target = target[parent]
        target[leaf] = value
    return card


@pytest.mark.parametrize("catalogue", [False, True])
def test_collect_bad_price_keeps_raw_prices_and_leaks_nothing(
    tcgdex_client: TcgdexClient,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    catalogue: bool,
) -> None:
    _collect(tcgdex_client, tmp_path, day=date(2026, 10, 25), prices=False)
    handler = _with_card(
        "/v2/fr/cards/swsh3-136", {"pricing.cardmarket.avg": "4999.37"}
    )

    with mock_client(handler) as client, caplog.at_level(logging.INFO):
        summary = _collect(client, tmp_path, catalogue=catalogue)

    paths = snapshot_paths(tmp_path, DAY)
    prices = _steps(summary)["prices"]
    assert prices["status"] == "failed"
    assert "conversion" in str(prices["error"])
    assert paths.raw_prices.exists()
    assert not paths.prices.exists()
    assert [f["name"] for f in prices["files"]] == [paths.raw_prices.name]
    assert "4999.37" not in paths.summary.read_text(encoding="utf-8")
    assert "4999.37" not in caplog.text


def test_collect_bad_card_keeps_raw_catalogue(tmp_path: Path) -> None:
    handler = _with_card("/v2/fr/cards/pop9-1", {"updated": 12345})

    with mock_client(handler) as client:
        summary = _collect(client, tmp_path)

    paths = snapshot_paths(tmp_path, DAY)
    steps = _steps(summary)
    assert steps["catalogue"]["status"] == "failed"
    assert paths.raw_cards.exists()
    assert not paths.cards.exists()
    assert steps["prices"]["error"] == "aucun catalogue disponible"


def test_collect_prices_reports_missing_languages(
    tcgdex_client: TcgdexClient, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _collect(
        tcgdex_client, tmp_path, date(2026, 10, 25), prices=False, languages=["fr"]
    )

    with caplog.at_level(logging.WARNING):
        summary = _collect(tcgdex_client, tmp_path, catalogue=False)

    prices = _steps(summary)["prices"]
    assert prices["status"] == "ok"
    assert prices["missing_languages"] == ["en", "ja"]
    assert "langues absentes" in caplog.text
    assert pq.read_table(snapshot_paths(tmp_path, DAY).prices).num_rows == 3


def test_collect_prices_fails_when_no_requested_language(
    tcgdex_client: TcgdexClient, tmp_path: Path
) -> None:
    _collect(
        tcgdex_client, tmp_path, date(2026, 10, 25), prices=False, languages=["fr"]
    )

    summary = _collect(tcgdex_client, tmp_path, catalogue=False, languages=["ja"])

    prices = _steps(summary)["prices"]
    assert prices["status"] == "failed"
    assert prices["missing_languages"] == ["ja"]
    assert not snapshot_paths(tmp_path, DAY).prices.exists()


@pytest.fixture
def fake_collect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[dict[str, Any]]:
    calls: dict[str, Any] = {"status": "ok"}

    def fake(client: TcgdexClient, data_dir: Path, **kwargs: Any) -> dict[str, Any]:
        calls.update(data_dir=data_dir, **kwargs)
        return {"steps": {"catalogue": {"status": "skipped"}, "prices": calls}}

    monkeypatch.setattr(run, "collect", fake)
    monkeypatch.setattr(run, "LOG_DIR", tmp_path / "logs")
    yield calls
    logger = logging.getLogger("cartograph")
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


def test_main_parses_options(fake_collect: dict[str, Any], tmp_path: Path) -> None:
    code = main(
        [
            "--catalogue",
            "--languages",
            "fr, ja",
            "--rotation",
            "250",
            "--data-dir",
            str(tmp_path),
        ]
    )

    assert code == 0
    assert fake_collect["rotation"] == 250
    assert fake_collect["catalogue"] is True
    assert fake_collect["prices"] is True
    assert fake_collect["languages"] == ("fr", "ja")
    assert fake_collect["data_dir"] == tmp_path
    assert list((tmp_path / "logs").glob("cartograph_*.log"))


def test_main_defaults(fake_collect: dict[str, Any]) -> None:
    main([])

    assert fake_collect["catalogue"] is False
    assert fake_collect["prices"] is True
    assert fake_collect["languages"] == LANGUAGES
    assert fake_collect["rotation"] == ROTATION_SIZE
    assert fake_collect["data_dir"] == run.DATA_DIR


def test_main_returns_one_when_a_step_fails(fake_collect: dict[str, Any]) -> None:
    fake_collect["status"] = "failed"

    assert main([]) == 1


@pytest.mark.parametrize(
    "argv",
    [
        ["--languages", "fr,de"],
        ["--languages", ","],
        ["--no-prices"],
        ["--rotation", "-1"],
        ["--rotation", "mille"],
    ],
)
def test_main_rejects_invalid_options(
    fake_collect: dict[str, Any], argv: list[str]
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(argv)

    assert exit_info.value.code == 2
    assert "data_dir" not in fake_collect
