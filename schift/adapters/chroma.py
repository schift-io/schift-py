"""ChromaDB adapter — read/write embeddings from ChromaDB."""

from __future__ import annotations

from typing import Iterator

import numpy as np

from schift.adapters.base import Adapter, EmbeddingBatch


class ChromaAdapter(Adapter):
    """ChromaDB adapter.

    Usage:
        adapter = ChromaAdapter(
            url="http://localhost:8000",
            collection="documents",
        )
    """

    adapter_name = "chroma"

    def __init__(
        self,
        url: str = "http://localhost:8000",
        collection: str = "",
    ):
        try:
            import chromadb
        except ImportError:
            raise ImportError("pip install schift[chroma]")

        host = url.replace("http://", "").replace("https://", "").split(":")[0]
        port = int(url.split(":")[-1]) if ":" in url.split("//")[-1] else 8000
        self._client = chromadb.HttpClient(host=host, port=port)
        self._collection_name = collection
        self._col = self._client.get_or_create_collection(
            name=collection, metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        return self._col.count()

    def dimension(self) -> int:
        result = self._col.peek(limit=1)
        if result["embeddings"] is not None and len(result["embeddings"]) > 0:
            return len(result["embeddings"][0])
        raise RuntimeError("Collection is empty — cannot determine dimension")

    def read_batches(self, batch_size: int = 1000) -> Iterator[EmbeddingBatch]:
        total = self.count()
        offset = 0
        while offset < total:
            result = self._col.get(
                include=["embeddings", "metadatas"],
                limit=batch_size,
                offset=offset,
            )
            if not result["ids"]:
                break
            yield EmbeddingBatch(
                ids=result["ids"],
                embeddings=np.array(result["embeddings"], dtype=np.float32),
                metadata=result["metadatas"],
            )
            offset += len(result["ids"])

    def write_batch(self, batch: EmbeddingBatch) -> int:
        self._col.upsert(
            ids=batch.ids,
            embeddings=[vec.tolist() for vec in batch.embeddings],
            metadatas=batch.metadata or [{}] * len(batch.ids),
        )
        return len(batch.ids)

    def prepare_target(self, target_dim: int) -> None:
        try:
            self._client.delete_collection(self._collection_name)
        except Exception:
            pass
        self._col = self._client.create_collection(
            name=self._collection_name, metadata={"hnsw:space": "cosine"},
        )
