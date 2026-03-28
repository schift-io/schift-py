from __future__ import annotations

import json
from typing import Optional

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

    def search(self, bucket_id: str, query: str, top_k: int = 10, mode: str = "hybrid", rerank: bool = False, model: Optional[str] = None):
        payload = {"query": query, "top_k": top_k, "mode": mode, "rerank": rerank}
        if model is not None:
            payload["model"] = model
        return self._http.post(f"/buckets/{bucket_id}/search", data=payload)

    def graph(self, bucket_id: str, query: Optional[str] = None, top_k: int = 10):
        params = {"top_k": top_k}
        if query is not None:
            params["query"] = query
        return self._http.get(f"/buckets/{bucket_id}/graph", params=params)

    def upload(self, bucket_id: str, files, ocr_strategy: Optional[str] = None, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None):
        meta = {}
        if ocr_strategy is not None:
            meta["ocr_strategy"] = ocr_strategy
        if chunk_size is not None:
            meta["chunk_size"] = chunk_size
        if chunk_overlap is not None:
            meta["chunk_overlap"] = chunk_overlap
        form_data = {"payload": json.dumps(meta)} if meta else {}
        return self._http._post_form_with_files(f"/buckets/{bucket_id}/upload", form_data, files)

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
