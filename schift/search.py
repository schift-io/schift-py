"""Search module — convenience namespace wrapping query and rerank."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from schift.query import QueryModule
    from schift.rerank import RerankModule


class SearchModule:
    """Namespace that exposes query and rerank under ``client.search``.

    Both ``client.search.query(...)`` and ``client.query(...)`` work — this
    module is an additive alias so existing code is not broken.
    """

    def __init__(self, query_module: "QueryModule", rerank_module: "RerankModule"):
        self._query = query_module
        self._rerank = rerank_module

    def query(self, *args, **kwargs) -> list[dict]:
        """Run a semantic search query. See ``QueryModule.__call__`` for args."""
        return self._query(*args, **kwargs)

    def rerank(self, *args, **kwargs) -> list[dict]:
        """Rerank results with a cross-encoder. See ``RerankModule.__call__`` for args."""
        return self._rerank(*args, **kwargs)
