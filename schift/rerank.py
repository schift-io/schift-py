"""Rerank module — rerank search results with a cross-encoder."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from schift._http import HttpClient


class RerankModule:

    def __init__(self, http: HttpClient):
        self._http = http

    def __call__(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        return self._http.post("/rerank", {
            "query": query,
            "documents": documents,
            "top_k": top_k,
        })
