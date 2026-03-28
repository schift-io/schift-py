"""Redis (RediSearch) adapter — read/write embeddings from Redis Stack."""

from __future__ import annotations

import json
import struct
from typing import Iterator, Optional

import numpy as np

from schift.adapters.base import Adapter, EmbeddingBatch


def _float_list_to_bytes(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


class RedisAdapter(Adapter):
    """Redis vector search adapter.

    Usage:
        adapter = RedisAdapter(
            url="redis://localhost:6379",
            collection="documents",
        )
    """

    adapter_name = "redis"

    def __init__(
        self,
        url: str = "redis://localhost:6379",
        collection: str = "",
    ):
        try:
            import redis as _redis
        except ImportError:
            raise ImportError("pip install schift[redis]")

        self._client = _redis.Redis.from_url(url, decode_responses=False)
        self._collection = collection
        self._index_name = f"schift:{collection}"
        self._prefix = f"schift:{collection}:"

    def count(self) -> int:
        try:
            info = self._client.ft(self._index_name).info()
            return int(info["num_docs"])
        except Exception:
            return 0

    def dimension(self) -> int:
        info = self._client.ft(self._index_name).info()
        for attr in info.get("attributes", []):
            if attr[1] == b"embedding" or attr[1] == "embedding":
                # Find DIM in attribute definition
                for i, val in enumerate(attr):
                    if val in (b"DIM", "DIM") and i + 1 < len(attr):
                        return int(attr[i + 1])
        raise RuntimeError("Cannot determine dimension from index info")

    def read_batches(self, batch_size: int = 1000) -> Iterator[EmbeddingBatch]:
        cursor = 0
        while True:
            cursor, keys = self._client.scan(
                cursor, match=f"{self._prefix}*", count=batch_size,
            )
            if keys:
                pipe = self._client.pipeline(transaction=False)
                for key in keys:
                    pipe.hgetall(key)
                results = pipe.execute()

                ids, embeddings, metadata = [], [], []
                for data in results:
                    if not data:
                        continue
                    doc_id = data.get(b"doc_id", b"").decode()
                    emb_bytes = data.get(b"embedding", b"")
                    dim = len(emb_bytes) // 4
                    emb = np.array(struct.unpack(f"{dim}f", emb_bytes), dtype=np.float32)
                    meta = json.loads(data.get(b"metadata", b"{}"))
                    ids.append(doc_id)
                    embeddings.append(emb)
                    metadata.append(meta)

                if ids:
                    yield EmbeddingBatch(
                        ids=ids,
                        embeddings=np.array(embeddings, dtype=np.float32),
                        metadata=metadata,
                    )

            if cursor == 0:
                break

    def write_batch(self, batch: EmbeddingBatch) -> int:
        pipe = self._client.pipeline(transaction=False)
        for pid, vec, pay in zip(
            batch.ids,
            batch.embeddings,
            batch.metadata or [{}] * len(batch.ids),
        ):
            key = f"{self._prefix}{pid}"
            pipe.hset(
                key,
                mapping={
                    "doc_id": pid,
                    "metadata": json.dumps(pay or {}),
                    "embedding": _float_list_to_bytes(vec.tolist()),
                },
            )
        pipe.execute()
        return len(batch.ids)

    def prepare_target(self, target_dim: int) -> None:
        from redis.commands.search.field import TextField, VectorField
        from redis.commands.search.indexDefinition import IndexDefinition, IndexType

        # Drop existing index and keys
        try:
            self._client.ft(self._index_name).dropindex(delete_documents=True)
        except Exception:
            pass

        schema = (
            TextField("doc_id"),
            TextField("metadata"),
            VectorField(
                "embedding",
                "HNSW",
                {"TYPE": "FLOAT32", "DIM": target_dim, "DISTANCE_METRIC": "COSINE"},
            ),
        )
        self._client.ft(self._index_name).create_index(
            schema,
            definition=IndexDefinition(prefix=[self._prefix], index_type=IndexType.HASH),
        )
