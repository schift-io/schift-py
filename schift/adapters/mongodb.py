"""MongoDB Atlas adapter — read/write embeddings via Atlas Vector Search."""

from __future__ import annotations

from typing import Iterator, Optional

import numpy as np

from schift.adapters.base import Adapter, EmbeddingBatch


class MongoDBAdapter(Adapter):
    """MongoDB Atlas Vector Search adapter.

    Usage:
        adapter = MongoDBAdapter(
            uri="mongodb+srv://...",
            database="mydb",
            collection="documents",
        )
    """

    adapter_name = "mongodb"

    def __init__(
        self,
        uri: str = "mongodb://localhost:27017",
        database: str = "schift",
        collection: str = "",
    ):
        try:
            from pymongo import MongoClient
        except ImportError:
            raise ImportError("pip install schift[mongodb]")

        self._client = MongoClient(uri)
        self._db = self._client[database]
        self._col = self._db[collection]
        self._collection_name = collection

    def count(self) -> int:
        return self._col.count_documents({})

    def dimension(self) -> int:
        doc = self._col.find_one({}, {"embedding": 1})
        if doc and "embedding" in doc:
            return len(doc["embedding"])
        raise RuntimeError("Collection is empty — cannot determine dimension")

    def read_batches(self, batch_size: int = 1000) -> Iterator[EmbeddingBatch]:
        cursor = self._col.find({}, {"_id": 1, "embedding": 1, "metadata": 1})
        batch_ids, batch_embs, batch_meta = [], [], []
        for doc in cursor:
            batch_ids.append(str(doc["_id"]))
            batch_embs.append(doc["embedding"])
            batch_meta.append(doc.get("metadata", {}))
            if len(batch_ids) >= batch_size:
                yield EmbeddingBatch(
                    ids=batch_ids,
                    embeddings=np.array(batch_embs, dtype=np.float32),
                    metadata=batch_meta,
                )
                batch_ids, batch_embs, batch_meta = [], [], []
        if batch_ids:
            yield EmbeddingBatch(
                ids=batch_ids,
                embeddings=np.array(batch_embs, dtype=np.float32),
                metadata=batch_meta,
            )

    def write_batch(self, batch: EmbeddingBatch) -> int:
        from pymongo import ReplaceOne

        ops = [
            ReplaceOne(
                {"_id": pid},
                {
                    "_id": pid,
                    "embedding": vec.tolist(),
                    "metadata": pay or {},
                },
                upsert=True,
            )
            for pid, vec, pay in zip(
                batch.ids,
                batch.embeddings,
                batch.metadata or [{}] * len(batch.ids),
            )
        ]
        self._col.bulk_write(ops)
        return len(ops)

    def prepare_target(self, target_dim: int) -> None:
        from pymongo.operations import SearchIndexModel

        self._col.drop()
        model = SearchIndexModel(
            definition={
                "fields": [
                    {
                        "type": "vector",
                        "numDimensions": target_dim,
                        "path": "embedding",
                        "similarity": "cosine",
                    }
                ]
            },
            name="vector_index",
            type="vectorSearch",
        )
        self._col.create_search_index(model)
