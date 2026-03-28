"""Local projection — applies pre-learned matrix without server calls."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


class Projection:
    """A learned projection that transforms embeddings from one model space to another.

    This object is returned by Client.fit() and contains the projection matrix.
    transform() runs locally (pure matrix multiplication) — no API calls, no latency.
    """

    def __init__(
        self,
        W: NDArray,
        project_id: str,
        source_model: str,
        target_model: str,
        source_dim: int,
        target_dim: int,
        method: str,
        n_samples: int,
        quality: dict,
    ):
        self.W = W
        self.project_id = project_id
        self.source_model = source_model
        self.target_model = target_model
        self.source_dim = source_dim
        self.target_dim = target_dim
        self.method = method
        self.n_samples = n_samples
        self.quality = quality

    def transform(self, embeddings: NDArray) -> NDArray:
        """Transform embeddings from source model space to target model space.

        Runs locally — pure matrix multiplication. < 1ms for typical batches.

        Args:
            embeddings: Vectors from source model, shape (n, source_dim) or (source_dim,).

        Returns:
            Projected vectors compatible with target model, shape (n, target_dim).
            L2-normalized.
        """
        embeddings = np.asarray(embeddings, dtype=np.float64)

        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        if embeddings.shape[1] != self.source_dim:
            raise ValueError(
                f"Expected {self.source_dim}d embeddings (source: {self.source_model}), "
                f"got {embeddings.shape[1]}d"
            )

        projected = embeddings @ self.W
        norms = np.linalg.norm(projected, axis=1, keepdims=True)
        return (projected / np.maximum(norms, 1e-10)).astype(np.float32)

    def save(self, path: str | Path) -> None:
        """Save projection to disk for offline use."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        np.save(path / "W.npy", self.W)
        meta = {
            "project_id": self.project_id,
            "source_model": self.source_model,
            "target_model": self.target_model,
            "source_dim": self.source_dim,
            "target_dim": self.target_dim,
            "method": self.method,
            "n_samples": self.n_samples,
            "quality": self.quality,
        }
        (path / "meta.json").write_text(json.dumps(meta, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> Projection:
        """Load projection from disk."""
        path = Path(path)
        W = np.load(path / "W.npy")
        meta = json.loads((path / "meta.json").read_text())
        return cls(W=W, **meta)

    def __repr__(self) -> str:
        r10 = self.quality.get("recovery_r10", "?")
        return (
            f"Projection({self.source_model} → {self.target_model}, "
            f"{self.source_dim}d→{self.target_dim}d, "
            f"recovery={r10}%)"
        )
