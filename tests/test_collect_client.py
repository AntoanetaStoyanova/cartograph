from collections.abc import Callable

import httpx
import pytest

from cartograph.bin.collect.client import NotFoundError, TcgdexClient, TcgdexError
from cartograph.config import MAX_RETRY_AFTER_S, TCGDEX_USER_AGENT

Handler = Callable[[httpx.Request], httpx.Response]


def _client(handler: Handler, sleeps: list[float]) -> TcgdexClient:
    return TcgdexClient(
        base_url="https://test",
        pause=0.1,
        max_retries=2,
        backoff=1.0,
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
    )


def _responses(*responses: httpx.Response | Exception) -> tuple[Handler, list[str]]:
    queue = list(responses)
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return handler, paths


def test_get_json_returns_payload() -> None:
    handler, paths = _responses(httpx.Response(200, json=[{"id": "swsh3-136"}]))

    with _client(handler, []) as client:
        assert client.get_json("/fr/cards") == [{"id": "swsh3-136"}]
    assert paths == ["/fr/cards"]


def test_get_json_sends_user_agent() -> None:
    agents: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        agents.append(request.headers["User-Agent"])
        return httpx.Response(200, json={})

    with _client(handler, []) as client:
        client.get_json("/fr/cards")
    assert agents == [TCGDEX_USER_AGENT]


def test_get_json_pauses_between_requests() -> None:
    handler, _ = _responses(*(httpx.Response(200, json={}) for _ in range(3)))
    sleeps: list[float] = []

    with _client(handler, sleeps) as client:
        client.get_json("/a")
        assert sleeps == []
        client.get_json("/b")
        client.get_json("/c")
    assert sleeps == [0.1, 0.1]


def test_get_json_retries_then_succeeds() -> None:
    handler, paths = _responses(
        httpx.Response(503), httpx.Response(200, json={"ok": 1})
    )
    sleeps: list[float] = []

    with _client(handler, sleeps) as client:
        assert client.get_json("/a") == {"ok": 1}
    assert paths == ["/a", "/a"]
    assert sleeps == [1.0]


def test_get_json_retries_on_transport_error() -> None:
    handler, paths = _responses(
        httpx.ConnectError("refusé"), httpx.Response(200, json={"ok": 1})
    )

    with _client(handler, []) as client:
        assert client.get_json("/a") == {"ok": 1}
    assert len(paths) == 2


def test_get_json_respects_retry_after() -> None:
    handler, _ = _responses(
        httpx.Response(429, headers={"Retry-After": "7"}),
        httpx.Response(200, json={}),
    )
    sleeps: list[float] = []

    with _client(handler, sleeps) as client:
        client.get_json("/a")
    assert sleeps == [7.0]


def test_get_json_raises_after_max_retries() -> None:
    handler, paths = _responses(*(httpx.Response(500) for _ in range(3)))
    sleeps: list[float] = []

    with _client(handler, sleeps) as client, pytest.raises(TcgdexError):
        client.get_json("/a")
    assert len(paths) == 3
    assert sleeps == [1.0, 2.0]


def test_get_json_404_raises_card_not_found_without_retry() -> None:
    handler, paths = _responses(httpx.Response(404))

    with _client(handler, []) as client, pytest.raises(NotFoundError):
        client.get_json("/fr/cards/inconnue")
    assert len(paths) == 1


def test_get_json_other_4xx_raises_without_retry() -> None:
    handler, paths = _responses(httpx.Response(403))

    with _client(handler, []) as client, pytest.raises(TcgdexError) as excinfo:
        client.get_json("/a")
    assert not isinstance(excinfo.value, NotFoundError)
    assert len(paths) == 1


def test_get_json_non_json_body_raises_tcgdex_error() -> None:
    handler, _ = _responses(httpx.Response(200, text="<html>maintenance</html>"))

    with _client(handler, []) as client, pytest.raises(TcgdexError, match="JSON"):
        client.get_json("/a")


def test_get_json_follows_redirects() -> None:
    handler, paths = _responses(
        httpx.Response(301, headers={"Location": "/b"}),
        httpx.Response(200, json={"ok": 1}),
    )

    with _client(handler, []) as client:
        assert client.get_json("/a") == {"ok": 1}
    assert paths == ["/a", "/b"]


def test_get_json_caps_retry_after() -> None:
    handler, _ = _responses(
        httpx.Response(429, headers={"Retry-After": "3600"}),
        httpx.Response(200, json={}),
    )
    sleeps: list[float] = []

    with _client(handler, sleeps) as client:
        client.get_json("/a")
    assert sleeps == [MAX_RETRY_AFTER_S]


def test_get_json_retry_after_date_falls_back_to_backoff() -> None:
    handler, _ = _responses(
        httpx.Response(503, headers={"Retry-After": "Wed, 28 Oct 2026 07:28:00 GMT"}),
        httpx.Response(200, json={}),
    )
    sleeps: list[float] = []

    with _client(handler, sleeps) as client:
        client.get_json("/a")
    assert sleeps == [1.0]
