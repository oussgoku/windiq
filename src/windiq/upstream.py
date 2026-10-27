"""Synchronous WindIQ HTTP client; response records are mapped by ingestion."""

from collections.abc import Iterator
from datetime import datetime
from math import isfinite
from time import monotonic, sleep
from typing import Any, Literal

import httpx
from pydantic import BaseModel, PositiveInt, SecretStr, field_validator

from windiq.config import Settings


class TokenResponse(BaseModel):
    access_token: SecretStr
    expires_in: PositiveInt
    token_type: Literal["Bearer"]

    @field_validator("access_token")
    @classmethod
    def token_must_not_be_empty(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value():
            raise ValueError("access_token must not be empty")
        return value


class WindIQClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._http = httpx.Client(
            base_url=settings.windiq_api_base_url.rstrip("/") + "/",
            timeout=30.0,
            transport=transport,
        )
        self._access_token: SecretStr | None = None
        self._expires_at = 0.0

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(3):
            retry_delay = 0.5 * (2**attempt)
            try:
                response = self._http.request(method, path, **kwargs)
            except httpx.TransportError:
                if attempt == 2:
                    raise
            else:
                if response.status_code not in {429, 500, 502, 503, 504}:
                    response.raise_for_status()
                    return response
                if attempt == 2:
                    response.raise_for_status()
                if response.status_code == 429:
                    try:
                        retry_after = float(response.headers.get("Retry-After", ""))
                    except ValueError:
                        pass
                    else:
                        if isfinite(retry_after):
                            retry_delay = max(
                                retry_delay, min(60.0, max(0.0, retry_after))
                            )
                response.close()
            sleep(retry_delay)
        raise RuntimeError("upstream request failed after retries")

    def __enter__(self) -> "WindIQClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self._http.close()

    def _bearer_token(self) -> str:
        if self._access_token is not None and monotonic() < self._expires_at:
            return self._access_token.get_secret_value()

        client_id = self._settings.windiq_client_id
        client_secret = self._settings.windiq_client_secret
        if not client_id or not client_secret:
            raise ValueError("WINDIQ_CLIENT_ID and WINDIQ_CLIENT_SECRET are required")

        response = self._request(
            "POST",
            "auth/token",
            json={
                "client_id": client_id.get_secret_value(),
                "client_secret": client_secret.get_secret_value(),
            },
        )
        try:
            token = TokenResponse.model_validate(response.json())
        except ValueError:
            raise ValueError("invalid authentication response") from None
        self._access_token = token.access_token
        self._expires_at = monotonic() + max(0, token.expires_in - 30)
        return token.access_token.get_secret_value()

    def get_measurements_page(
        self,
        *,
        updated_since: datetime | None = None,
        cursor: str | None = None,
        limit: int = 500,
    ) -> dict[str, Any]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        if updated_since is not None and updated_since.utcoffset() is None:
            raise ValueError("query timestamps must be timezone-aware")

        params: dict[str, str | int] = {"limit": limit}
        if updated_since is not None:
            params["updated_since"] = updated_since.isoformat()
        if cursor is not None:
            params["cursor"] = cursor

        response = self._request(
            "GET",
            "v1/measurements",
            params=params,
            headers={"Authorization": f"Bearer {self._bearer_token()}"},
        )
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("measurements response must be a JSON object")
        return payload

    def _get_object(self, path: str) -> dict[str, Any]:
        response = self._request(
            "GET",
            path,
            headers={"Authorization": f"Bearer {self._bearer_token()}"},
        )
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError(f"{path} response must be a JSON object")
        return payload

    def get_mast(self) -> dict[str, Any]:
        return self._get_object("v1/mast")

    def get_site(self) -> dict[str, Any]:
        return self._get_object("v1/site")

    def get_turbine(self) -> dict[str, Any]:
        return self._get_object("v1/turbine")

    def get_mast_id(self) -> str:
        payload = self.get_mast()
        mast_id = payload.get("id")
        if not isinstance(mast_id, str) or not mast_id:
            raise ValueError("mast response must include a nonempty id")
        return mast_id

    def iter_measurement_pages(
        self,
        *,
        updated_since: datetime | None = None,
        limit: int = 500,
    ) -> Iterator[dict[str, Any]]:
        cursor: str | None = None
        seen_cursors: set[str] = set()
        while True:
            page = self.get_measurements_page(
                updated_since=updated_since,
                cursor=cursor,
                limit=limit,
            )
            if "next_cursor" not in page:
                raise ValueError("measurements response is missing next_cursor")
            yield page
            next_cursor = page.get("next_cursor")
            if next_cursor is None:
                return
            if not isinstance(next_cursor, str) or not next_cursor:
                raise ValueError("next_cursor must be a nonempty string or null")
            if next_cursor in seen_cursors:
                raise ValueError("measurements pagination repeated a cursor")
            seen_cursors.add(next_cursor)
            cursor = next_cursor
