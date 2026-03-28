"""Catalog module — browse available embedding models."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from schift._http import HttpClient


class CatalogModule:

    def __init__(self, http: HttpClient):
        self._http = http

    def list(self) -> list[dict]:
        return self._http.get("/catalog")

    def get(self, model_id: str) -> dict:
        return self._http.get(f"/catalog/{model_id}")
