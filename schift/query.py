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
        bucket: Optional[str] = None,
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
            bucket: Bucket name or ID. Preferred for Schift-hosted retrieval.
            collection: Deprecated alias for bucket.
            db: External database connection name (for passthrough mode).
            model: Embedding model to use. Defaults to the routing primary.
            top_k: Number of results to return.
            rerank: Whether to apply reranking to results.
            rerank_top_k: Number of results after reranking (defaults to top_k).
        """
        payload: dict = {"query": query, "top_k": top_k}
        resolved_bucket = bucket or collection
        if model is not None:
            payload["model"] = model
        if rerank:
            payload["rerank"] = True
            if rerank_top_k is not None:
                payload["rerank_top_k"] = rerank_top_k
        if resolved_bucket is not None and db is None:
            return self._http.post(f"/buckets/{resolved_bucket}/search", payload)
        if resolved_bucket is not None:
            # /v1/query keeps the legacy JSON key for external DB passthrough compatibility.
            payload["collection"] = resolved_bucket
        if db is not None:
            payload["db"] = db
        return self._http.post("/query", payload)
