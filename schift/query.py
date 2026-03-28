"""Query module — semantic search through Schift proxy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from schift._http import HttpClient


class QueryModule:

    def __init__(self, http: HttpClient):
        self._http = http

    def __call__(
        self,
        query: str,
        collection: Optional[str] = None,
        db: Optional[str] = None,
        model: Optional[str] = None,
        top_k: int = 10,
        rerank: bool = False,
        rerank_top_k: Optional[int] = None,
    ) -> list[dict]:
        """Run a semantic search query.

        Args:
            query: Natural language query text.
            collection: Collection name (for Schift-hosted collections).
            db: External database connection name (for passthrough mode).
            model: Embedding model to use. Defaults to the routing primary.
            top_k: Number of results to return.
            rerank: Whether to apply reranking to results.
            rerank_top_k: Number of results after reranking (defaults to top_k).
        """
        payload: dict = {"query": query, "top_k": top_k}
        if collection is not None:
            payload["collection"] = collection
        if db is not None:
            payload["db"] = db
        if model is not None:
            payload["model"] = model
        if rerank:
            payload["rerank"] = True
            if rerank_top_k is not None:
                payload["rerank_top_k"] = rerank_top_k
        return self._http.post("/query", payload)
