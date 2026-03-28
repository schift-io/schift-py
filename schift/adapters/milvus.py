"""Milvus / Zilliz adapter — read/write embeddings from Milvus."""

from __future__ import annotations

from typing import Iterator, Optional

import numpy as np

from schift.adapters.base import Adapter, EmbeddingBatch


class MilvusAdapter(Adapter):
    """Milvus vector DB adapter.

    Usage:
        adapter = MilvusAdapter(
            uri="http://localhost:19530",
            collection="documents",
        )
    """

    adapter_name = "milvus"

    def __init__(
        self,
        uri: str = "http://localhost:19530",
        collection: str = "",
        token: Optional[str] = None,
    ):
        try:
            from pymilvus import MilvusClient
        except ImportError:
            raise ImportError("pip install schift[milvus]")

        self._client = MilvusClient(uri=uri, token=token or "")
        self._collection = collection

    def count(self) -> int:
        return self._client.num_entities(collection_name=self._collection)

    def dimension(self) -> int:
        info = self._client.describe_collection(self._collection)
        for field in info.get("fields", []):
            if field.get("type") in (101,):  # FLOAT_VECTOR
                return field["params"]["dim"]
        raise RuntimeError("Cannot determine dimension from collection schema")

    def read_batches(self, batch_size: int = 1000) -> Iterator[EmbeddingBatch]:
        total = self.count()
        offset = 0
        while offset < total:
            results = self._client.query(
                collection_name=self._collection,
                filter="",
                output_fields=["id", "embedding", "metadata"],
                limit=batch_size,
                offset=offset,
            )
            if not results:
                break
            ids = [r["id"] for r in results]
            embeddings = np.array([r["embedding"] for r in results], dtype=np.float32)
            metadata = [r.get("metadata", {}) for r in results]
            yield EmbeddingBatch(ids=ids, embeddings=embeddings, metadata=metadata)
            offset += len(results)

    def write_batch(self, batch: EmbeddingBatch) -> int:
        data = [
            {
                "id": pid,
                "embedding": vec.tolist(),
                "metadata": pay or {},
            }
            for pid, vec, pay in zip(
                batch.ids,
                batch.embeddings,
                batch.metadata or [{}] * len(batch.ids),
            )
        ]
        self._client.upsert(collection_name=self._collection, data=data)
        return len(data)

    def prepare_target(self, target_dim: int) -> None:
        from pymilvus import CollectionSchema, DataType, FieldSchema

        if self._client.has_collection(self._collection):
            self._client.drop_collection(self._collection)

        schema = CollectionSchema(fields=[
            FieldSchema("id", DataType.VARCHAR, is_primary=True, max_length=256),
            FieldSchema("embedding", DataType.FLOAT_VECTOR, dim=target_dim),
            FieldSchema("metadata", DataType.JSON),
        ])
        index_params = self._client.prepare_index_params()
        index_params.add_index(
            field_name="embedding", metric_type="COSINE", index_type="AUTOINDEX",
        )
        self._client.create_collection(
            collection_name=self._collection, schema=schema, index_params=index_params,
        )
