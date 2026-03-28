"""Weaviate adapter — read/write embeddings from Weaviate."""

from __future__ import annotations

from typing import Iterator, Optional

import numpy as np

from schift.adapters.base import Adapter, EmbeddingBatch


class WeaviateAdapter(Adapter):
    """Weaviate vector DB adapter.

    Usage:
        adapter = WeaviateAdapter(
            url="http://localhost:8080",
            collection="documents",
        )
    """

    adapter_name = "weaviate"

    def __init__(
        self,
        url: str = "http://localhost:8080",
        collection: str = "",
        api_key: Optional[str] = None,
    ):
        try:
            import weaviate
        except ImportError:
            raise ImportError("pip install schift[weaviate]")

        host = url.replace("http://", "").replace("https://", "").split(":")[0]
        port = int(url.split(":")[-1]) if ":" in url.split("//")[-1] else 8080

        if api_key:
            auth = weaviate.auth.AuthApiKey(api_key=api_key)
            self._client = weaviate.connect_to_custom(
                http_host=host,
                http_port=port,
                http_secure=url.startswith("https"),
                auth_credentials=auth,
            )
        else:
            self._client = weaviate.connect_to_local(host=host, port=port)

        self._collection_name = collection

    def _get_collection(self):
        return self._client.collections.get(self._collection_name)

    def count(self) -> int:
        col = self._get_collection()
        resp = col.aggregate.over_all(total_count=True)
        return resp.total_count or 0

    def dimension(self) -> int:
        col = self._get_collection()
        for obj in col.iterator(include_vector=True):
            if obj.vector:
                vec = obj.vector.get("default", obj.vector)
                if isinstance(vec, list):
                    return len(vec)
            break
        raise RuntimeError("Collection is empty — cannot determine dimension")

    def read_batches(self, batch_size: int = 1000) -> Iterator[EmbeddingBatch]:
        import uuid as _uuid

        col = self._get_collection()
        ids, embeddings, metadata = [], [], []

        for obj in col.iterator(include_vector=True):
            vec = obj.vector
            if isinstance(vec, dict):
                vec = vec.get("default", list(vec.values())[0])

            doc_id = obj.properties.get("doc_id", str(obj.uuid))
            meta_str = obj.properties.get("metadata", "{}")
            meta = meta_str if isinstance(meta_str, dict) else {}

            ids.append(doc_id)
            embeddings.append(vec)
            metadata.append(meta)

            if len(ids) >= batch_size:
                yield EmbeddingBatch(
                    ids=ids,
                    embeddings=np.array(embeddings, dtype=np.float32),
                    metadata=metadata,
                )
                ids, embeddings, metadata = [], [], []

        if ids:
            yield EmbeddingBatch(
                ids=ids,
                embeddings=np.array(embeddings, dtype=np.float32),
                metadata=metadata,
            )

    def write_batch(self, batch: EmbeddingBatch) -> int:
        import uuid as _uuid

        col = self._get_collection()
        with col.batch.dynamic() as wb:
            for pid, vec, pay in zip(
                batch.ids,
                batch.embeddings,
                batch.metadata or [{}] * len(batch.ids),
            ):
                wb.add_object(
                    properties={
                        "doc_id": pid,
                        "metadata": str(pay or {}),
                    },
                    vector=vec.tolist(),
                    uuid=_uuid.uuid5(_uuid.NAMESPACE_DNS, pid),
                )
        return len(batch.ids)

    def prepare_target(self, target_dim: int) -> None:
        from weaviate.classes.config import Configure, DataType, Property

        if self._client.collections.exists(self._collection_name):
            self._client.collections.delete(self._collection_name)
        self._client.collections.create(
            name=self._collection_name,
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(name="doc_id", data_type=DataType.TEXT),
                Property(name="metadata", data_type=DataType.TEXT),
            ],
        )
