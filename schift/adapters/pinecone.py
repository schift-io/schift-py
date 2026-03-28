"""Pinecone adapter — read/write embeddings from Pinecone."""

from __future__ import annotations

from typing import Iterator, Optional

import numpy as np

from schift.adapters.base import Adapter, EmbeddingBatch


class PineconeAdapter(Adapter):
    """Pinecone vector DB adapter.

    Usage:
        adapter = PineconeAdapter(
            api_key="...",
            index_host="...",
            namespace="documents",
        )
    """

    adapter_name = "pinecone"

    def __init__(
        self,
        api_key: str = "",
        index_host: str = "",
        namespace: str = "",
    ):
        try:
            from pinecone import Pinecone
        except ImportError:
            raise ImportError("pip install schift[pinecone]")

        self._pc = Pinecone(api_key=api_key)
        self._index = self._pc.Index(host=index_host)
        self._namespace = namespace

    def count(self) -> int:
        stats = self._index.describe_index_stats()
        ns_stats = stats.namespaces.get(self._namespace)
        return ns_stats.vector_count if ns_stats else 0

    def dimension(self) -> int:
        stats = self._index.describe_index_stats()
        return stats.dimension

    def read_batches(self, batch_size: int = 1000) -> Iterator[EmbeddingBatch]:
        for id_list in self._index.list(namespace=self._namespace):
            ids = [v for v in id_list]
            for i in range(0, len(ids), batch_size):
                chunk = ids[i : i + batch_size]
                resp = self._index.fetch(ids=chunk, namespace=self._namespace)
                vectors = resp.vectors
                batch_ids = []
                batch_embs = []
                batch_meta = []
                for vid, vec in vectors.items():
                    batch_ids.append(vid)
                    batch_embs.append(vec.values)
                    batch_meta.append(vec.metadata or {})
                if batch_ids:
                    yield EmbeddingBatch(
                        ids=batch_ids,
                        embeddings=np.array(batch_embs, dtype=np.float32),
                        metadata=batch_meta,
                    )

    def write_batch(self, batch: EmbeddingBatch) -> int:
        vectors = [
            {
                "id": pid,
                "values": vec.tolist(),
                "metadata": pay or {},
            }
            for pid, vec, pay in zip(
                batch.ids,
                batch.embeddings,
                batch.metadata or [{}] * len(batch.ids),
            )
        ]
        for i in range(0, len(vectors), 100):
            self._index.upsert(vectors=vectors[i : i + 100], namespace=self._namespace)
        return len(vectors)

    def prepare_target(self, target_dim: int) -> None:
        # Pinecone index dimension is fixed at creation; namespace is cleared
        self._index.delete(delete_all=True, namespace=self._namespace)
