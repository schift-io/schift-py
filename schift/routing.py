"""Routing module — configure embedding model routing rules."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from schift._http import HttpClient


class RoutingModule:

    def __init__(self, http: HttpClient):
        self._http = http

    def get(self) -> dict:
        return self._http.get("/routing")

    def set(
        self,
        primary: Optional[str] = None,
        fallback: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> dict:
        payload: dict = {}
        if primary is not None:
            payload["primary"] = primary
        if fallback is not None:
            payload["fallback"] = fallback
        if mode is not None:
            payload["mode"] = mode
        return self._http.put("/routing", payload)
