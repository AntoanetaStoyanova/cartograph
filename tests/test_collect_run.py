import json
import logging
import runpy
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pyarrow.parquet as pq
import pytest

from cartograph.bin.collect import batch, client, run
from cartograph.bin.collect.catalogue import card_path
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


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz: Any = None) -> "_FrozenDatetime":
        return cls.combine(DAY, time(9, 30), tz)


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
    [(True, True, 3), (True, False, 2), (False, True, 4)],
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


@pytest.mark.usefixtures("isolated_logs")
def test_main_returns_one_when_new_cards_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _old_catalogue(tmp_path, "SV7-065")
    monkeypatch.setattr(run, "TcgdexClient", lambda: mock_client(_down("/v2/ja/cards")))

    assert main(["--data-dir", str(tmp_path)]) == 1


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
    assert steps["catalogue"]["status"] == "ok"
    assert steps["catalogue"]["source"] == "cards-2026-10-25.parquet"
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


def test_collect_prices_stopped_by_outage_writes_prices_received(
    tcgdex_client: TcgdexClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _collect(tcgdex_client, tmp_path, day=date(2026, 10, 25), prices=False)
    monkeypatch.setattr(batch, "MAX_CONSECUTIVE_FAILURES", 2)
    served: list[str] = []

    def first_card_only(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "/cards/" not in path:
            return fixture_route(request)
        if not served:
            served.append(path)
        return fixture_route(request) if path == served[0] else httpx.Response(500)

    with mock_client(first_card_only) as client:
        summary = _collect(client, tmp_path, catalogue=False)

    paths = snapshot_paths(tmp_path, DAY)
    prices = _steps(summary)["prices"]
    assert prices["status"] == "failed"
    assert "2 échecs d'affilée" in str(prices["error"])
    assert prices["fetched"] == 1
    assert [f["name"] for f in prices["files"]] == [
        paths.prices.name,
        paths.raw_prices.name,
    ]
    assert pq.read_table(paths.prices).num_rows == 1


def test_collect_interrupted_new_cards_marked_in_summary(
    tcgdex_client: TcgdexClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _old_catalogue(tmp_path, "SV7-065")

    def interrupted(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("délai dépassé")

    monkeypatch.setattr(run, "_collect_new_cards", interrupted)

    with pytest.raises(RuntimeError):
        _collect(tcgdex_client, tmp_path, catalogue=False)

    paths = snapshot_paths(tmp_path, DAY)
    steps = _steps(json.loads(paths.summary.read_text(encoding="utf-8")))
    assert steps["new_cards"]["status"] == "failed"
    assert steps["new_cards"]["error"] == "étape interrompue avant la fin"


@pytest.mark.filterwarnings("ignore:.*found in sys.modules:RuntimeWarning")
def test_main_run_as_module_logs_to_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, isolated_logs: Path
) -> None:
    class FixtureClient(TcgdexClient):
        def __init__(self) -> None:
            super().__init__(
                transport=httpx.MockTransport(fixture_route),
                max_retries=0,
                sleep=lambda _: None,
            )

    # Une sous-classe, pas une fonction : beartype lit l'annotation au chargement.
    monkeypatch.setattr(client, "TcgdexClient", FixtureClient)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run", "--catalogue", "--no-prices", "--languages", "fr"]
        + ["--data-dir", str(tmp_path)],
    )

    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("cartograph.bin.collect.run", run_name="__main__")

    assert exit_info.value.code == 0
    (log_file,) = isolated_logs.glob("cartograph_*.log")
    assert "Collecte terminée" in log_file.read_text(encoding="utf-8")


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
    monkeypatch: pytest.MonkeyPatch, isolated_logs: Path
) -> dict[str, Any]:
    calls: dict[str, Any] = {"status": "ok"}

    def fake(client: TcgdexClient, data_dir: Path, **kwargs: Any) -> dict[str, Any]:
        calls.update(data_dir=data_dir, **kwargs)
        return {"steps": {"catalogue": {"status": "skipped"}, "prices": calls}}

    monkeypatch.setattr(run, "collect", fake)
    return calls


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


def test_main_catalogue_without_prices(fake_collect: dict[str, Any]) -> None:
    main(["--catalogue", "--no-prices"])

    assert fake_collect["catalogue"] is True
    assert fake_collect["prices"] is False


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


def _rows(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (row["language"], row["card_id"]): row
        for row in pq.read_table(path).to_pylist()
    }


def _changes(path: Path) -> list[tuple[str, str, str]]:
    table = pq.read_table(path)
    return sorted(
        zip(
            table.column("change_type").to_pylist(),
            table.column("language").to_pylist(),
            table.column("card_id").to_pylist(),
            strict=True,
        )
    )


def test_collect_daily_writes_catalogue_and_changes(tmp_path: Path) -> None:
    _old_catalogue(tmp_path, "SV7-065")

    with mock_client(fixture_route) as client:
        summary = _collect(client, tmp_path, catalogue=False)

    paths = snapshot_paths(tmp_path, DAY)
    catalogue = _steps(summary)["catalogue"]
    assert catalogue["status"] == "ok"
    assert [f["name"] for f in catalogue["files"]] == [
        paths.cards.name,
        paths.card_changes.name,
    ]
    assert catalogue["changes"] == {
        "new": 1,
        "updated": 0,
        "removed": 0,
        "reappeared": 0,
        "rotated": 4,
    }
    assert pq.read_table(paths.cards).num_rows == 9
    assert _changes(paths.card_changes) == [("new", "ja", "SV7-065")]


def test_collect_daily_failed_price_card_keeps_previous_row(tmp_path: Path) -> None:
    old_day = date(2026, 10, 25)
    with mock_client(fixture_route) as client:
        _collect(client, tmp_path, day=old_day, prices=False)

    with mock_client(_down("/v2/fr/cards/pop9-1")) as client:
        _collect(client, tmp_path, catalogue=False)

    old = _rows(snapshot_paths(tmp_path, old_day).cards)
    rows = _rows(snapshot_paths(tmp_path, DAY).cards)
    assert rows[("fr", "pop9-1")] == old[("fr", "pop9-1")]
    assert (
        rows[("fr", "swsh3-136")]["fetched_at"] > old[("fr", "swsh3-136")]["fetched_at"]
    )


def test_collect_daily_marks_removed_card_and_skips_its_price(tmp_path: Path) -> None:
    with mock_client(fixture_route) as client:
        _collect(client, tmp_path, day=date(2026, 10, 25), prices=False)

    with mock_client(_without("pop9-1")) as client:
        summary = _collect(client, tmp_path, catalogue=False)

    paths = snapshot_paths(tmp_path, DAY)
    rows = _rows(paths.cards)
    assert rows[("fr", "pop9-1")]["removed_on"] == DAY
    assert rows[("en", "pop9-1")]["removed_on"] == DAY
    assert len(rows) == 9
    assert _changes(paths.card_changes) == [
        ("removed", "en", "pop9-1"),
        ("removed", "fr", "pop9-1"),
    ]
    assert _steps(summary)["prices"]["fetched"] == 4
    assert _steps(summary)["prices"]["failed"] == []


def test_collect_daily_rotation_reads_oldest_cards_outside_prices(
    tmp_path: Path,
) -> None:
    with mock_client(fixture_route) as client:
        _collect(client, tmp_path, day=date(2026, 10, 25), prices=False)
    requested: list[str] = []

    def recording(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.raw_path.decode())
        return fixture_route(request)

    with mock_client(recording) as client:
        summary = collect(
            client, tmp_path, False, True, LANGUAGES, now=_clock(), rotation=1
        )

    catalogue = _steps(summary)["catalogue"]
    assert catalogue["fetched"] == 1
    assert catalogue["changes"]["rotated"] == 1
    prices = pq.read_table(snapshot_paths(tmp_path, DAY).prices).to_pylist()
    priced = {f"/v2{card_path(row['language'], row['card_id'])}" for row in prices}
    cards = [path for path in requested if "/cards/" in path]
    assert len(cards) == len(set(cards))
    assert set(cards) - priced == {"/v2/ja/cards/PMCG6-055"}


@pytest.mark.usefixtures("isolated_logs")
def test_main_rotation_stopped_by_outage_writes_catalogue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with mock_client(fixture_route) as client:
        _collect(client, tmp_path, day=date(2026, 10, 25), prices=False)
    monkeypatch.setattr(batch, "MAX_CONSECUTIVE_FAILURES", 2)

    def rotation_down(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.startswith("/v2/en/cards/") or path == "/v2/ja/cards/PMCG6-055":
            return httpx.Response(500)
        return fixture_route(request)

    monkeypatch.setattr(run, "TcgdexClient", lambda: mock_client(rotation_down))
    monkeypatch.setattr(run, "datetime", _FrozenDatetime)

    code = main(["--data-dir", str(tmp_path)])

    paths = snapshot_paths(tmp_path, DAY)
    catalogue = _steps(json.loads(paths.summary.read_text(encoding="utf-8")))[
        "catalogue"
    ]
    assert code == 1
    assert catalogue["status"] == "failed"
    assert "2 échecs d'affilée" in str(catalogue["error"])
    assert [f["name"] for f in catalogue["files"]] == [
        paths.cards.name,
        paths.card_changes.name,
    ]
    assert pq.read_table(paths.cards).num_rows == 9


def test_collect_daily_without_rotation_reads_only_prices(tmp_path: Path) -> None:
    with mock_client(fixture_route) as client:
        _collect(client, tmp_path, day=date(2026, 10, 25), prices=False)

    with mock_client(fixture_route) as client:
        summary = collect(
            client, tmp_path, False, True, LANGUAGES, now=_clock(), rotation=0
        )

    catalogue = _steps(summary)["catalogue"]
    assert catalogue["status"] == "ok"
    assert catalogue["fetched"] == 0
    assert catalogue["changes"]["rotated"] == 0


def test_collect_full_catalogue_marks_removed_then_reappeared_card(
    tmp_path: Path,
) -> None:
    with mock_client(fixture_route) as client:
        _collect(client, tmp_path, day=date(2026, 10, 25), prices=False)
    with mock_client(_without("pop9-1")) as client:
        _collect(client, tmp_path, prices=False)

    removed = snapshot_paths(tmp_path, DAY)
    assert _rows(removed.cards)[("fr", "pop9-1")]["removed_on"] == DAY
    assert _changes(removed.card_changes) == [
        ("removed", "en", "pop9-1"),
        ("removed", "fr", "pop9-1"),
    ]

    with mock_client(fixture_route) as client:
        _collect(client, tmp_path, day=DAY + timedelta(days=1), prices=False)

    back = snapshot_paths(tmp_path, DAY + timedelta(days=1))
    assert _rows(back.cards)[("fr", "pop9-1")]["removed_on"] is None
    assert _changes(back.card_changes) == [
        ("reappeared", "en", "pop9-1"),
        ("reappeared", "fr", "pop9-1"),
    ]


def test_collect_catalogue_day_failed_card_keeps_previous_row(tmp_path: Path) -> None:
    old_day = date(2026, 10, 25)
    with mock_client(fixture_route) as client:
        _collect(client, tmp_path, day=old_day, prices=False)

    with mock_client(_down("/v2/ja/cards/S7D-019")) as client:
        summary = _collect(client, tmp_path, prices=False)

    paths = snapshot_paths(tmp_path, DAY)
    catalogue = _steps(summary)["catalogue"]
    assert catalogue["failed"] == ["ja/S7D-019"]
    assert catalogue["source"] == "cards-2026-10-25.parquet"
    old = _rows(snapshot_paths(tmp_path, old_day).cards)
    assert _rows(paths.cards)[("ja", "S7D-019")] == old[("ja", "S7D-019")]
    assert _changes(paths.card_changes) == []


def test_collect_same_day_rerun_starts_from_previous_catalogue(tmp_path: Path) -> None:
    _old_catalogue(tmp_path, "SV7-065")

    with mock_client(fixture_route) as client:
        _collect(client, tmp_path, catalogue=False)
        summary = _collect(client, tmp_path, catalogue=False)

    paths = snapshot_paths(tmp_path, DAY)
    assert _steps(summary)["catalogue"]["source"] == "cards-2026-10-25.parquet"
    assert _changes(paths.card_changes) == [("new", "ja", "SV7-065")]


def test_collect_two_daily_runs_chain_catalogues(tmp_path: Path) -> None:
    _old_catalogue(tmp_path, "SV7-065")
    first, second = date(2026, 10, 26), date(2026, 10, 27)
    corrected = _with_card("/v2/fr/cards/swsh3-136", {"rarity": "Rare"})

    with mock_client(fixture_route) as client:
        _collect(client, tmp_path, day=first, catalogue=False)
    with mock_client(corrected) as client:
        summary = _collect(client, tmp_path, day=second, catalogue=False)

    paths = snapshot_paths(tmp_path, second)
    assert _steps(summary)["catalogue"]["source"] == "cards-2026-10-26.parquet"
    assert _changes(paths.card_changes) == [("updated", "fr", "swsh3-136")]
    rows = _rows(paths.cards)
    assert len(rows) == 9
    assert rows[("fr", "swsh3-136")]["rarity"] == "Rare"
    assert rows[("ja", "SV7-065")]["removed_on"] is None


def test_collect_daily_catalogue_leaks_no_price(tmp_path: Path) -> None:
    _old_catalogue(tmp_path, "SV7-065")
    prices = price_values([load_fixture(n) for names in CARDS.values() for n in names])

    with mock_client(fixture_route) as client:
        _collect(client, tmp_path, catalogue=False)

    paths = snapshot_paths(tmp_path, DAY)
    for path in [paths.cards, paths.card_changes]:
        text = json.dumps(pq.read_table(path).to_pylist(), default=str)
        assert not [price for price in prices if price in text]
        assert "pricing" not in text
