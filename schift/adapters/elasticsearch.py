"""Elasticsearch / OpenSearch adapter — read/write embeddings via kNN."""

from __future__ import annotations

from typing import Iterator, Optional

import numpy as np

from schift.adapters.base import Adapter, EmbeddingBatch


class ElasticsearchAdapter(Adapter):
    """Elasticsearch adapter.

    Usage:
        adapter = ElasticsearchAdapter(
            url="http://localhost:9200",
            index="documents",
        )
    """

    adapter_name = "elasticsearch"

    def __init__(
        self,
        url: str = "http://localhost:9200",
        index: str = "",
        api_key: Optional[str] = None,
    ):
        try:
            from elasticsearch import Elasticsearch
        except ImportError:
            raise ImportError("pip install schift[elasticsearch]")

        kwargs: dict = {"hosts": [url]}
        if api_key:
            kwargs["api_key"] = api_key
        self._client = Elasticsearch(**kwargs)
        self._index = index

    def count(self) -> int:
        resp = self._client.count(index=self._index)
        return resp["count"]

    def dimension(self) -> int:
        mapping = self._client.indices.get_mapping(index=self._index)
        props = list(mapping.values())[0]["mappings"]["properties"]
        return props["embedding"]["dims"]

    def read_batches(self, batch_size: int = 1000) -> Iterator[EmbeddingBatch]:
        resp = self._client.search(
            index=self._index,
            body={"query": {"match_all": {}}, "_source": ["doc_id", "metadata", "embedding"]},
            scroll="5m",
            size=batch_size,
        )
        scroll_id = resp["_scroll_id"]

        while True:
            hits = resp["hits"]["hits"]
            if not hits:
                break
            ids = [h["_source"].get("doc_id", h["_id"]) for h in hits]
            embeddings = np.array(
                [h["_source"]["embedding"] for h in hits], dtype=np.float32,
            )
            metadata = [h["_source"].get("metadata", {}) for h in hits]
            yield EmbeddingBatch(ids=ids, embeddings=embeddings, metadata=metadata)
            resp = self._client.scroll(scroll_id=scroll_id, scroll="5m")

        self._client.clear_scroll(scroll_id=scroll_id)

    def write_batch(self, batch: EmbeddingBatch) -> int:
        from elasticsearch.helpers import bulk

        actions = [
            {
                "_index": self._index,
                "_id": pid,
                "_source": {
                    "embedding": vec.tolist(),
                    "doc_id": pid,
                    "metadata": pay or {},
                },
            }
            for pid, vec, pay in zip(
                batch.ids,
                batch.embeddings,
                batch.metadata or [{}] * len(batch.ids),
            )
        ]
        bulk(self._client, actions)
        return len(actions)

    def prepare_target(self, target_dim: int) -> None:
        if self._client.indices.exists(index=self._index):
            self._client.indices.delete(index=self._index)
        self._client.indices.create(
            index=self._index,
            body={
                "mappings": {
                    "properties": {
                        "embedding": {
                            "type": "dense_vector",
                            "dims": target_dim,
                            "index": True,
                            "similarity": "cosine",
                        },
                        "doc_id": {"type": "keyword"},
                        "metadata": {"type": "object", "enabled": False},
                    }
                }
            },
        )
