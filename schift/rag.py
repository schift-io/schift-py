"""RAG module — direct one-shot RAG calls via POST /v1/rag/run.

Equivalent to running a single-block workflow with a `rag` block, but skips
the workflow CRUD + run record. Use this for ad-hoc queries when you don't
need persistent workflow state.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from schift._http import HttpClient


class RagModule:
    """Direct RAG endpoint: retrieve + prompt + LLM in one HTTP call."""

    def __init__(self, http: HttpClient):
        self._http = http

    def run(
        self,
        query: str,
        bucket: str,
        *,
        # Retrieval
        top_k: int = 5,
        mode: str = "vector",
        filter: Optional[dict] = None,
        tags: Optional[Union[str, list[str]]] = None,
        rerank: bool = False,
        rerank_top_k: int = 3,
        rerank_model: Optional[str] = None,
        # LLM
        model: str = "gemini-2.5-flash-lite",
        temperature: float = 0.2,
        max_tokens: int = 1024,
        thinking_budget: Optional[int] = 0,
        # Prompting
        system_prompt: str = "",
        template: Optional[str] = None,
        # Structured output
        response_schema: Optional[dict] = None,
        response_mime_type: Optional[str] = None,
        # Output
        include_sources: bool = True,
    ) -> dict[str, Any]:
        """Run retrieve + LLM against `bucket` with `query`.

        Returns a dict with keys: answer, data, sources, results, usage.
        """
        payload: dict[str, Any] = {
            "query": query,
            "bucket": bucket,
            "top_k": top_k,
            "mode": mode,
            "rerank": rerank,
            "rerank_top_k": rerank_top_k,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "thinking_budget": thinking_budget,
            "system_prompt": system_prompt,
            "include_sources": include_sources,
        }
        if filter is not None:
            payload["filter"] = filter
        if tags is not None:
            payload["tags"] = tags
        if rerank_model is not None:
            payload["rerank_model"] = rerank_model
        if template is not None:
            payload["template"] = template
        if response_schema is not None:
            payload["response_schema"] = response_schema
        if response_mime_type is not None:
            payload["response_mime_type"] = response_mime_type
        return self._http.post("/rag/run", data=payload)
