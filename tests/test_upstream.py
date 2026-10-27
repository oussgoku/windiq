import json
from datetime import UTC, datetime

import httpx
import pytest

from windiq.config import Settings
from windiq.upstream import WindIQClient


def test_authentication_and_paginated_measurements() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/auth/token":
            assert request.method == "POST"
            assert json.loads(request.content) == {
                "client_id": "test-id",
                "client_secret": "test-secret",
            }
            return httpx.Response(
                200,
                json={
                    "access_token": "test-token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )

        if request.url.path == "/v1/mast":
            assert request.headers["Authorization"] == "Bearer test-token"
            return httpx.Response(200, json={"id": "mast-1"})

        assert request.url.path == "/v1/measurements"
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.url.params["limit"] == "500"
        assert request.url.params["updated_since"] == "2026-10-01T00:00:00+00:00"
        if request.url.params.get("cursor") is None:
            return httpx.Response(200, json={"data": [], "next_cursor": "page-2"})
        assert request.url.params["cursor"] == "page-2"
        return httpx.Response(200, json={"data": [], "next_cursor": None})

    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unused/unused",
        windiq_api_base_url="https://example.test/",
        windiq_client_id="test-id",
        windiq_client_secret="test-secret",
    )
    with WindIQClient(settings, transport=httpx.MockTransport(handle)) as client:
        assert client.get_mast_id() == "mast-1"
        pages = list(
            client.iter_measurement_pages(
                updated_since=datetime(2026, 10, 1, tzinfo=UTC)
            )
        )

    assert len(pages) == 2
    assert [request.url.path for request in requests] == [
        "/auth/token",
        "/v1/mast",
        "/v1/measurements",
        "/v1/measurements",
    ]
    assert "test-secret" not in repr(settings)


def test_missing_credentials_fail_before_network_request() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unused/unused",
        windiq_api_base_url="https://example.test",
        windiq_client_id=None,
        windiq_client_secret=None,
    )

    def unexpected_request(_request: httpx.Request) -> httpx.Response:
        pytest.fail("network request should not have been sent")

    with WindIQClient(
        settings, transport=httpx.MockTransport(unexpected_request)
    ) as client:
        with pytest.raises(ValueError, match="WINDIQ_CLIENT_ID"):
            client.get_measurements_page()


def test_repeated_cursor_is_rejected() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )
        return httpx.Response(200, json={"data": [], "next_cursor": "same"})

    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unused/unused",
        windiq_api_base_url="https://example.test",
        windiq_client_id="id",
        windiq_client_secret="secret",
    )
    with WindIQClient(settings, transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ValueError, match="repeated a cursor"):
            list(client.iter_measurement_pages())


def test_missing_next_cursor_is_rejected() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )
        return httpx.Response(200, json={"data": []})

    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unused/unused",
        windiq_api_base_url="https://example.test",
        windiq_client_id="id",
        windiq_client_secret="secret",
    )
    with WindIQClient(settings, transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ValueError, match="missing next_cursor"):
            list(client.iter_measurement_pages())


def test_naive_query_timestamp_is_rejected() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unused/unused",
        windiq_api_base_url="https://example.test",
        windiq_client_id="id",
        windiq_client_secret="secret",
    )
    with WindIQClient(settings) as client:
        with pytest.raises(ValueError, match="timezone-aware"):
            client.get_measurements_page(updated_since=datetime(2026, 10, 1))


def test_transient_server_errors_are_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("windiq.upstream.sleep", lambda _seconds: None)
    calls: dict[str, int] = {"/auth/token": 0, "/v1/measurements": 0}

    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls[path] += 1
        if calls[path] == 1:
            return httpx.Response(503)
        if path == "/auth/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )
        return httpx.Response(200, json={"data": [], "next_cursor": None})

    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unused/unused",
        windiq_api_base_url="https://example.test",
        windiq_client_id="id",
        windiq_client_secret="secret",
    )
    with WindIQClient(settings, transport=httpx.MockTransport(handle)) as client:
        assert client.get_measurements_page() == {"data": [], "next_cursor": None}
    assert calls == {"/auth/token": 2, "/v1/measurements": 2}


def test_rate_limit_waits_for_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    delays: list[float] = []
    monkeypatch.setattr("windiq.upstream.sleep", delays.append)
    calls = 0

    def handle(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "60"})
        return httpx.Response(
            200,
            json={"access_token": "token", "expires_in": 3600, "token_type": "Bearer"},
        )

    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unused/unused",
        windiq_api_base_url="https://example.test",
        windiq_client_id="id",
        windiq_client_secret="secret",
    )
    with WindIQClient(settings, transport=httpx.MockTransport(handle)) as client:
        assert client._bearer_token() == "token"
    assert calls == 2
    assert delays == [60.0]
