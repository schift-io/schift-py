"""Base adapter interface — all vector stores implement this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

import numpy as np
from numpy.typing import NDArray


class EmbeddingBatch:
    """A batch of (id, embedding) pairs from a vector store."""

    __slots__ = ("ids", "embeddings", "metadata")

    def __init__(self, ids: list, embeddings: NDArray, metadata: list[dict] | None = None):
        self.ids = ids
        self.embeddings = embeddings
        self.metadata = metadata

    def __len__(self) -> int:
        return len(self.ids)


class Adapter(ABC):
    """Base class for vector store adapters.

    Every adapter can read and write embeddings, enabling:
        Source(pgvector) → Projection → Sink(qdrant)
    """

    adapter_name: str = ""

    @abstractmethod
    def count(self) -> int:
        """Total number of vectors in the store."""
        ...

    @abstractmethod
    def read_batches(self, batch_size: int = 1000) -> Iterator[EmbeddingBatch]:
        """Yield batches of (id, embedding) from the store."""
        ...

    @abstractmethod
    def write_batch(self, batch: EmbeddingBatch) -> int:
        """Write a batch of embeddings to the store. Returns rows written."""
        ...

    @abstractmethod
    def dimension(self) -> int:
        """Current embedding dimension in the store."""
        ...

    def prepare_target(self, target_dim: int) -> None:
        """Optional: prepare store for new dimension (e.g., create column, collection)."""
        pass

    def info(self) -> dict:
        """Return adapter info for diagnostics."""
        return {
            "adapter": self.adapter_name,
            "count": self.count(),
            "dimension": self.dimension(),
        }
