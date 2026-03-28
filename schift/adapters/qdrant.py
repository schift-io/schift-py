"""Qdrant adapter — read/write embeddings from Qdrant."""

from __future__ import annotations

from typing import Iterator, Optional

import numpy as np

from schift.adapters.base import Adapter, EmbeddingBatch


class QdrantAdapter(Adapter):
    """Qdrant vector DB adapter.

    Usage:
        adapter = QdrantAdapter(
            url="http://localhost:6333",
            collection="documents",
        )
    """

    adapter_name = "qdrant"

    def __init__(
        self,
        url: str = "http://localhost:6333",
        collection: str = "",
        api_key: Optional[str] = None,
    ):
        try:
            from qdrant_client import QdrantClient
        except ImportError:
            raise ImportError("pip install schift[qdrant]")

        self._client = QdrantClient(url=url, api_key=api_key)
        self._collection = collection

    def count(self) -> int:
        info = self._client.get_collection(self._collection)
        return info.points_count

    def dimension(self) -> int:
        info = self._client.get_collection(self._collection)
        return info.config.params.vectors.size

    def read_batches(self, batch_size: int = 1000) -> Iterator[EmbeddingBatch]:
        offset = None
        while True:
            results, next_offset = self._client.scroll(
                collection_name=self._collection,
                limit=batch_size,
                offset=offset,
                with_vectors=True,
                with_payload=True,
            )
            if not results:
                break

            yield EmbeddingBatch(
                ids=[p.id for p in results],
                embeddings=np.array([p.vector for p in results], dtype=np.float32),
                metadata=[p.payload for p in results],
            )

            if next_offset is None:
                break
            offset = next_offset

    def write_batch(self, batch: EmbeddingBatch) -> int:
        from qdrant_client.models import PointStruct

        points = [
            PointStruct(
                id=pid,
                vector=vec.tolist(),
                payload=pay or {},
            )
            for pid, vec, pay in zip(
                batch.ids,
                batch.embeddings,
                batch.metadata or [{}] * len(batch.ids),
            )
        ]
        self._client.upsert(collection_name=self._collection, points=points)
        return len(points)

    def prepare_target(self, target_dim: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        # Recreate collection with new dimension
        self._client.recreate_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(size=target_dim, distance=Distance.COSINE),
        )
