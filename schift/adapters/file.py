"""File adapter — read/write embeddings from .npy / .csv files."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import numpy as np

from schift.adapters.base import Adapter, EmbeddingBatch


class NpyAdapter(Adapter):
    """NumPy .npy file adapter. Simplest option for bulk migration.

    Usage:
        source = NpyAdapter("old_embeddings.npy")
        sink = NpyAdapter("new_embeddings.npy")
    """

    adapter_name = "npy"

    def __init__(self, path: str | Path, ids: list | None = None):
        self._path = Path(path)
        self._ids = ids
        self._data: np.ndarray | None = None

    def _load(self) -> np.ndarray:
        if self._data is None:
            self._data = np.load(self._path)
        return self._data

    def count(self) -> int:
        return self._load().shape[0]

    def dimension(self) -> int:
        return self._load().shape[1]

    def read_batches(self, batch_size: int = 1000) -> Iterator[EmbeddingBatch]:
        data = self._load()
        ids = self._ids or list(range(len(data)))
        for i in range(0, len(data), batch_size):
            yield EmbeddingBatch(
                ids=ids[i:i + batch_size],
                embeddings=data[i:i + batch_size],
            )

    def write_batch(self, batch: EmbeddingBatch) -> int:
        # Accumulate, save on close
        if self._data is None:
            self._data = batch.embeddings
        else:
            self._data = np.vstack([self._data, batch.embeddings])
        np.save(self._path, self._data)
        return len(batch)
