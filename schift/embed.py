"""Embed module — generate embeddings via Schift proxy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from schift._http import HttpClient


class EmbedModule:

    def __init__(self, http: HttpClient):
        self._http = http

    def __call__(self, text: str, model: str, dimensions: Optional[int] = None) -> NDArray:
        payload: dict = {"text": text, "model": model}
        if dimensions is not None:
            payload["dimensions"] = dimensions
        resp = self._http.post("/embed", payload)
        return np.asarray(resp["embedding"], dtype=np.float32)

    def batch(self, texts: list[str], model: str, dimensions: Optional[int] = None) -> NDArray:
        payload: dict = {"texts": texts, "model": model}
        if dimensions is not None:
            payload["dimensions"] = dimensions
        resp = self._http.post("/embed/batch", payload)
        return np.asarray(resp["embeddings"], dtype=np.float32)

    def list_models(self) -> list[dict]:
        """List all available embedding models from the catalog.

        Convenience alias for ``client.catalog.list()``. Both methods hit
        the same ``/catalog`` endpoint; prefer ``client.catalog.list()`` for
        clarity in new code.

        Returns:
            List of catalog model dicts. Each dict has ``model_id``,
            ``display_name``, ``provider``, ``dimensions``, and other fields.
        """
        from schift.catalog import CatalogModule
        return CatalogModule(self._http).list()

    def get_model(self, model_id: str) -> dict:
        """Retrieve a single model's catalog entry by its canonical ID.

        Convenience alias for ``client.catalog.get(model_id)``. Both methods
        hit the same ``/catalog/{model_id}`` endpoint; prefer
        ``client.catalog.get()`` for clarity in new code.

        Args:
            model_id: Canonical model ID, e.g. ``"openai/text-embedding-3-large"``.

        Returns:
            Catalog model dict.

        Raises:
            SchiftError: If the model is not found (HTTP 404).
        """
        from schift.catalog import CatalogModule
        return CatalogModule(self._http).get(model_id)
