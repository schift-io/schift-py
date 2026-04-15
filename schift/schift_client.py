"""Schift — the main entry point for the Schift SDK."""

from __future__ import annotations

import os
from functools import cached_property
from typing import Optional

from schift._http import HttpClient
from schift.aggregate import AggregateModule
from schift.artifacts import ArtifactsModule
from schift.bench import BenchModule
from schift.benchmark_suites import BenchmarkSuitesModule
from schift.buckets import BucketsModule
from schift.catalog import CatalogModule
from schift.chat import ChatModule
from schift.completions import CompletionsModule
from schift.db import DBModule
from schift.drift import DriftModule
from schift.embed import EmbedModule
from schift.jobs import JobsModule
from schift.query import QueryModule
from schift.rerank import RerankModule
from schift.routing import RoutingModule
from schift.search import SearchModule
from schift.tasks import TasksModule
from schift.usage import UsageModule
from schift.tools import SchiftTools
from schift.workflows import WorkflowsModule

_DEFAULT_BASE_URL = "https://api.schift.io/v1"


class Schift:
    """Schift SDK client — Cloudflare for Vector Search.

    Usage::

        from schift import Schift

        client = Schift(api_key="sch_xxx")
        # or: client = Schift()  # reads SCHIFT_API_KEY

        results = client.query("what is schift?", bucket="docs")
        models = client.catalog.list()
        embedding = client.embed("hello world", model="openai/text-embedding-3-small")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = 60.0,
    ):
        resolved_key = api_key or os.environ.get("SCHIFT_API_KEY", "")
        if not resolved_key:
            raise ValueError(
                "API key required. Pass api_key= or set SCHIFT_API_KEY env var."
            )
        self._http = HttpClient(api_key=resolved_key, base_url=base_url, timeout=timeout)

    # -- Modules (lazy-loaded) --

    @cached_property
    def catalog(self) -> CatalogModule:
        return CatalogModule(self._http)

    @cached_property
    def embed(self) -> EmbedModule:
        return EmbedModule(self._http)

    @cached_property
    def routing(self) -> RoutingModule:
        return RoutingModule(self._http)

    @cached_property
    def migrate(self) -> "MigrateModule":
        from schift._migrate_module import MigrateModule
        return MigrateModule(self._http)

    @cached_property
    def bench(self) -> BenchModule:
        return BenchModule(self._http)

    @cached_property
    def db(self) -> DBModule:
        return DBModule(self._http)

    @cached_property
    def query(self) -> QueryModule:
        return QueryModule(self._http)

    @cached_property
    def rerank(self) -> RerankModule:
        return RerankModule(self._http)

    @cached_property
    def search(self) -> SearchModule:
        """Convenience namespace: ``client.search.query()`` and ``client.search.rerank()``."""
        return SearchModule(self.query, self.rerank)

    @cached_property
    def chat(self) -> ChatModule:
        """RAG Chat — search + generate in one call."""
        return ChatModule(self._http)

    @cached_property
    def usage(self) -> UsageModule:
        return UsageModule(self._http)

    @cached_property
    def aggregate(self) -> AggregateModule:
        return AggregateModule(self._http)

    @cached_property
    def artifacts(self) -> ArtifactsModule:
        return ArtifactsModule(self._http)

    @cached_property
    def benchmark_suites(self) -> BenchmarkSuitesModule:
        return BenchmarkSuitesModule(self._http)

    @cached_property
    def buckets(self) -> BucketsModule:
        return BucketsModule(self._http)

    @cached_property
    def completions(self) -> CompletionsModule:
        return CompletionsModule(self._http)

    @cached_property
    def drift(self) -> DriftModule:
        return DriftModule(self._http)

    @cached_property
    def jobs(self) -> JobsModule:
        return JobsModule(self._http)

    @cached_property
    def tasks(self) -> TasksModule:
        return TasksModule(self._http)

    @cached_property
    def workflows(self) -> WorkflowsModule:
        return WorkflowsModule(self._http)

    @cached_property
    def tools(self) -> SchiftTools:
        """Tool calling helpers for OpenAI, Claude, LangChain."""
        return SchiftTools(
            search_fn=self.query,
            chat_fn=self.chat,
        )

    # -- Lifecycle --

    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __repr__(self) -> str:
        return f"Schift(base_url={self._http._client.base_url!r})"
