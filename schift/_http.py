"""Shared HTTP client — single connection pool for all modules."""

from __future__ import annotations

from typing import Any, Optional

import httpx

from schift.client import AuthError, QuotaError, SchiftError

_DEFAULT_BASE_URL = "https://api.schift.io/v1"
_USER_AGENT = "schift-python/0.1.0"


class HttpClient:
    """Thin wrapper around httpx.Client with auth and error handling."""

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = 60.0,
    ):
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "User-Agent": _USER_AGENT,
            },
            timeout=timeout,
        )

    def get(self, path: str, params: Optional[dict] = None) -> Any:
        resp = self._client.get(path, params=params)
        return self._handle(resp)

    def post(self, path: str, data: Any = None) -> Any:
        resp = self._client.post(path, json=data)
        return self._handle(resp)

    def put(self, path: str, data: Any = None) -> Any:
        resp = self._client.put(path, json=data)
        return self._handle(resp)

    def patch(self, path: str, data: Any = None) -> Any:
        resp = self._client.patch(path, json=data)
        return self._handle(resp)

    def delete(self, path: str) -> Any:
        resp = self._client.delete(path)
        return self._handle(resp)

    def delete_json(self, path: str, data: Any = None) -> Any:
        """DELETE with a JSON request body (for endpoints that require a payload)."""
        resp = self._client.request("DELETE", path, json=data)
        return self._handle(resp)

    def post_multipart(self, path: str, files: list[tuple[str, tuple]]) -> Any:
        """POST multipart/form-data. ``files`` follows httpx's files= convention:
        [(field_name, (filename, file_bytes, content_type)), ...]
        """
        resp = self._client.post(path, files=files)
        return self._handle(resp)

    def _post_form_with_files(
        self,
        path: str,
        form_data: dict[str, str],
        files: list[tuple[str, tuple]],
    ) -> Any:
        """POST multipart/form-data with both plain form fields and file uploads.

        Args:
            path: URL path (relative to base_url).
            form_data: Plain string form fields (e.g. {"payload": json_str}).
            files: File tuples following httpx convention:
                   [(field_name, (filename, file_bytes, content_type)), ...]
        """
        resp = self._client.post(path, data=form_data, files=files)
        return self._handle(resp)

    def stream_post(self, path: str, data: Any = None):
        """POST with SSE streaming. Returns httpx response for iter_lines."""
        return self._client.stream("POST", path, json=data)

    def _handle(self, resp: httpx.Response) -> Any:
        if resp.status_code == 401:
            raise AuthError("Invalid API key")
        if resp.status_code == 402:
            detail = resp.json().get("detail", "Quota exceeded") if resp.text else "Quota exceeded"
            raise QuotaError(detail)
        if resp.status_code >= 400:
            raise SchiftError(f"API error {resp.status_code}: {resp.text}")
        if resp.status_code == 204:
            return None
        return resp.json()

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
