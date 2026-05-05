"""RagModule.run — wire shape + error mapping."""

from __future__ import annotations

import pytest

from schift.client import EntitlementError, SchiftError
from schift.rag import RagModule


class FakeHttp:
    def __init__(self, response: dict | None = None, raise_exc: Exception | None = None):
        self.calls: list[tuple] = []
        self.next_response = response or {"answer": "", "sources": []}
        self.raise_exc = raise_exc

    def post(self, path, data=None):
        self.calls.append(("post", path, data))
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.next_response


def test_rag_run_posts_to_v1_rag_run_with_default_body():
    http = FakeHttp(response={"answer": "x", "sources": [], "results": [], "usage": {}})
    rag = RagModule(http)

    result = rag.run("hello", bucket="my-docs")

    assert result == {"answer": "x", "sources": [], "results": [], "usage": {}}

    assert http.calls[0][0] == "post"
    assert http.calls[0][1] == "/rag/run"
    body = http.calls[0][2]

    # Required fields populated with the documented defaults.
    assert body["query"] == "hello"
    assert body["bucket"] == "my-docs"
    assert body["top_k"] == 5
    assert body["mode"] == "vector"
    assert body["rerank"] is False
    assert body["rerank_top_k"] == 3
    assert body["model"] == "gemini-2.5-flash-lite"
    assert body["temperature"] == 0.2
    assert body["max_tokens"] == 1024
    assert body["thinking_budget"] == 0
    assert body["system_prompt"] == ""
    assert body["include_sources"] is True

    # Optional knobs absent unless set.
    for missing in (
        "filter",
        "tags",
        "rerank_model",
        "template",
        "response_schema",
        "response_mime_type",
    ):
        assert missing not in body


def test_rag_run_includes_optional_knobs_when_provided():
    http = FakeHttp(response={"answer": "ok", "sources": []})
    rag = RagModule(http)

    rag.run(
        "q",
        bucket="b",
        filter={"tag": "x"},
        tags=["a", "b"],
        rerank=True,
        rerank_model="bge-reranker-v2-m3",
        template="answer concisely:\n{context}\n{query}",
        response_schema={"type": "object"},
        response_mime_type="application/json",
    )
    body = http.calls[0][2]
    assert body["filter"] == {"tag": "x"}
    assert body["tags"] == ["a", "b"]
    assert body["rerank"] is True
    assert body["rerank_model"] == "bge-reranker-v2-m3"
    assert body["template"].startswith("answer concisely")
    assert body["response_schema"] == {"type": "object"}
    assert body["response_mime_type"] == "application/json"


def test_rag_run_propagates_entitlement_error():
    """A 403 from the server (rerank gated behind plan, e.g.) should
    surface as a typed EntitlementError, not a silent dict."""
    http = FakeHttp(raise_exc=EntitlementError("Upgrade your plan"))
    rag = RagModule(http)

    with pytest.raises(EntitlementError):
        rag.run("q", bucket="b", rerank=True)


def test_rag_run_propagates_generic_schift_error():
    http = FakeHttp(raise_exc=SchiftError("API error 500: oops"))
    rag = RagModule(http)
    with pytest.raises(SchiftError):
        rag.run("q", bucket="b")
