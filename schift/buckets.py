from __future__ import annotations

import json
import time
from typing import Any, Mapping, Optional, Union

from schift._http import HttpClient


class BucketsModule:
    def __init__(self, http: HttpClient):
        self._http = http

    def create(self, name: str, description: Optional[str] = None):
        payload = {"name": name}
        if description is not None:
            payload["description"] = description
        return self._http.post("/buckets", data=payload)

    def list(self):
        return self._http.get("/buckets")

    def delete(self, bucket_id: str):
        return self._http.delete(f"/buckets/{bucket_id}")

    def search(
        self,
        bucket_id: str,
        query: str,
        top_k: int = 10,
        mode: str = "hybrid",
        rerank: bool = False,
        model: Optional[str] = None,
        filter: Optional[dict[str, Any]] = None,
    ):
        payload = {"query": query, "top_k": top_k, "mode": mode, "rerank": rerank}
        if model is not None:
            payload["model"] = model
        if filter is not None:
            payload["filter"] = filter
        return self._http.post(f"/buckets/{bucket_id}/search", data=payload)

    def graph(self, bucket_id: str, query: Optional[str] = None, top_k: int = 10):
        params = {"top_k": top_k}
        if query is not None:
            params["query"] = query
        return self._http.get(f"/buckets/{bucket_id}/graph", params=params)

    def upload(
        self,
        bucket_id: str,
        files,
        ocr_strategy: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        metadata: Optional[Mapping[str, Union[str, int, float, bool]]] = None,
        collection_id: Optional[str] = None,
    ):
        meta = {}
        if ocr_strategy is not None:
            meta["ocr_strategy"] = ocr_strategy
        if chunk_size is not None:
            meta["chunk_size"] = chunk_size
        if chunk_overlap is not None:
            meta["chunk_overlap"] = chunk_overlap
        form_data = {"payload": json.dumps(meta)} if meta else {}
        if metadata:
            form_data["metadata"] = json.dumps(dict(metadata))
        if collection_id is not None:
            form_data["collection_id"] = collection_id
        return self._http._post_form_with_files(f"/buckets/{bucket_id}/upload", form_data, files)

    def list_collections(self, bucket_id: str):
        return self._http.get(f"/buckets/{bucket_id}/collections")

    def create_collection(self, bucket_id: str, name: str, description: Optional[str] = None):
        payload = {"name": name}
        if description is not None:
            payload["description"] = description
        return self._http.post(f"/buckets/{bucket_id}/collections", data=payload)

    def grant_collection_access(
        self,
        bucket_id: str,
        collection_id: str,
        subject_type: str,
        subject_id: str,
        permission: str = "search",
    ):
        return self._http.post(
            f"/buckets/{bucket_id}/collections/{collection_id}/grants",
            data={
                "subject_type": subject_type,
                "subject_id": subject_id,
                "permission": permission,
            },
        )

    def get_job(self, job_id: str):
        return self._http.get(f"/jobs/{job_id}")

    def list_jobs(
        self,
        bucket_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        params = {}
        if bucket_id is not None:
            params["bucket_id"] = bucket_id
        if status is not None:
            params["status"] = status
        if limit is not None:
            params["limit"] = limit
        return self._http.get("/jobs", params=params)

    def wait_for_job(
        self,
        job_id: str,
        poll_interval: float = 1.0,
        timeout: float = 300.0,
        terminal_statuses: tuple[str, ...] = ("ready", "failed", "cancelled"),
    ):
        deadline = time.monotonic() + timeout
        while True:
            job = self.get_job(job_id)
            status = job.get("status") if isinstance(job, dict) else None
            if status in terminal_statuses:
                return job
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for job {job_id}")
            time.sleep(poll_interval)

    def poll_job(
        self,
        job_id: str,
        poll_interval: float = 1.0,
        timeout: float = 300.0,
        terminal_statuses: tuple[str, ...] = ("ready", "failed", "cancelled"),
    ):
        return self.wait_for_job(
            job_id,
            poll_interval=poll_interval,
            timeout=timeout,
            terminal_statuses=terminal_statuses,
        )

    def add_edges(self, bucket_id: str, edges: list):
        return self._http.post(f"/buckets/{bucket_id}/edges", data={"edges": edges})

    def list_edges(self, bucket_id: str, node_id: str, direction: Optional[str] = None, relation: Optional[str] = None):
        params = {}
        if direction is not None:
            params["direction"] = direction
        if relation is not None:
            params["relation"] = relation
        return self._http.get(f"/buckets/{bucket_id}/edges/{node_id}", params=params)

    def delete_edge(self, bucket_id: str, source: str, target: str, relation: Optional[str] = None):
        payload = {"source": source, "target": target}
        if relation is not None:
            payload["relation"] = relation
        return self._http.delete_json(f"/buckets/{bucket_id}/edges", data=payload)

    def context(
        self,
        bucket_id: str,
        query: str,
        *,
        token_budget: int = 2000,
        mode: str = "auto",
        session_id: Optional[str] = None,
        filters: Optional[dict] = None,
        include_messages: int = 0,
        top_k: int = 10,
    ) -> dict:
        """Single-call RAG context — returns paste-ready context with citations.

        Args:
            bucket_id:       Bucket ID to search.
            query:           User query.
            token_budget:    Max tokens in returned context block (default 2000).
            mode:            Pipeline mode: auto | naive | hyde | rerank | decision-review.
            session_id:      Optional session ID for prepending recent turns.
            filters:         Metadata filter dict passed to search.
            include_messages: N most recent session turns to prepend.
            top_k:           Number of chunks to retrieve before budget packing.

        Returns:
            dict with keys:
                text           — paste-ready context string with [1] [2] citations
                tokens         — estimated token count of text
                chunks         — list of dicts with id/text/score/metadata
                session_turns  — list of dicts with role/content
                truncated_count — chunks truncated to fit budget
                skipped_count   — chunks skipped due to budget
                mode_used       — mode actually executed
                cache_hit       — True if served from semantic cache
        """
        payload: dict = {
            "query": query,
            "token_budget": token_budget,
            "mode": mode,
            "include_messages": include_messages,
            "top_k": top_k,
        }
        if session_id is not None:
            payload["session_id"] = session_id
        if filters is not None:
            payload["filters"] = filters
        return self._http.post(f"/buckets/{bucket_id}/context", data=payload)
