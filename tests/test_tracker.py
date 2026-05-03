"""Tests for client-side TokenTracker (Phase A)."""

from __future__ import annotations

import asyncio

from schift.tracker import TokenTracker, active_tracker, track


def test_tracker_starts_empty():
    t = TokenTracker()
    s = t.summary()
    assert s["call_count"] == 0
    assert s["llm_input_tokens"] == 0
    assert s["llm_output_tokens"] == 0
    assert s["cost_estimate_usd"] is None


def test_record_response_openai_style():
    t = TokenTracker()
    t.record_response({
        "id": "chatcmpl_x",
        "usage": {"prompt_tokens": 12, "completion_tokens": 34, "total_tokens": 46},
    })
    s = t.summary()
    assert s["call_count"] == 1
    assert s["llm_input_tokens"] == 12
    assert s["llm_output_tokens"] == 34
    # embed_tokens stays at 0 — chat shouldn't bleed into embed.
    assert s["embed_tokens"] == 0


def test_record_response_anthropic_style():
    t = TokenTracker()
    t.record_response({"usage": {"input_tokens": 7, "output_tokens": 9}})
    s = t.summary()
    assert s["llm_input_tokens"] == 7
    assert s["llm_output_tokens"] == 9


def test_record_response_embed_total_tokens_only():
    t = TokenTracker()
    # embed responses typically only carry total_tokens.
    t.record_response({"usage": {"total_tokens": 50}})
    s = t.summary()
    assert s["embed_tokens"] == 50
    assert s["llm_input_tokens"] == 0


def test_record_response_no_usage_still_counts_call():
    t = TokenTracker()
    t.record_response({"results": [{"id": "doc_1"}]})
    s = t.summary()
    assert s["call_count"] == 1
    # All token slots stay zero.
    for axis in (
        "llm_input_tokens",
        "llm_output_tokens",
        "embed_tokens",
        "search_calls",
    ):
        assert s[axis] == 0


def test_record_response_non_dict_body_is_safe():
    t = TokenTracker()
    t.record_response([1, 2, 3])  # list, not mapping
    t.record_response("string body")
    t.record_response(None)
    # call_count still bumped — we made the calls.
    assert t.summary()["call_count"] == 3


def test_unknown_axis_silently_ignored():
    t = TokenTracker()
    t.add_usage("not_a_real_axis", 500)
    assert t.summary()["call_count"] == 0
    # No new key, no error.


def test_context_manager_sets_active_tracker():
    assert active_tracker() is None
    with track() as t:
        assert active_tracker() is t
    assert active_tracker() is None


def test_context_manager_no_active_outside_block_is_noop():
    # Calls outside `with track():` find no active tracker.
    assert active_tracker() is None
    # Simulate what the HTTP hook does:
    tracker = active_tracker()
    if tracker is not None:  # pragma: no cover
        tracker.record_response({"usage": {"prompt_tokens": 999}})
    # Nothing should have happened.


def test_nested_trackers_inner_wins():
    with track() as outer:
        outer.record_response({"usage": {"prompt_tokens": 1, "completion_tokens": 1}})
        with track() as inner:
            # Inner is the active one now.
            assert active_tracker() is inner
            inner.record_response({"usage": {"prompt_tokens": 10, "completion_tokens": 20}})
        # Back to outer.
        assert active_tracker() is outer
        outer.record_response({"usage": {"prompt_tokens": 2, "completion_tokens": 2}})

    o = outer.summary()
    i = inner.summary()
    # Outer saw only its own two calls.
    assert o["call_count"] == 2
    assert o["llm_input_tokens"] == 1 + 2
    assert o["llm_output_tokens"] == 1 + 2
    # Inner saw only its own one call.
    assert i["call_count"] == 1
    assert i["llm_input_tokens"] == 10
    assert i["llm_output_tokens"] == 20


def test_reset_clears_counters():
    t = TokenTracker()
    t.record_response({"usage": {"prompt_tokens": 5, "completion_tokens": 7}})
    assert t.summary()["llm_input_tokens"] == 5
    t.reset()
    s = t.summary()
    assert s["call_count"] == 0
    assert s["llm_input_tokens"] == 0
    assert s["llm_output_tokens"] == 0


def test_asyncio_isolation_between_tasks():
    """Two concurrent asyncio tasks each get their own active tracker."""
    seen: dict[str, object] = {}

    async def task_a():
        with track() as t:
            await asyncio.sleep(0.01)
            seen["a"] = active_tracker()
            t.record_response({"usage": {"prompt_tokens": 100, "completion_tokens": 100}})
            await asyncio.sleep(0.01)
            seen["a_summary"] = t.summary()

    async def task_b():
        with track() as t:
            seen["b"] = active_tracker()
            t.record_response({"usage": {"prompt_tokens": 1, "completion_tokens": 1}})
            await asyncio.sleep(0.02)
            seen["b_summary"] = t.summary()

    async def main():
        await asyncio.gather(task_a(), task_b())

    asyncio.run(main())

    assert seen["a"] is not seen["b"]
    a = seen["a_summary"]  # type: ignore[index]
    b = seen["b_summary"]  # type: ignore[index]
    assert a["llm_input_tokens"] == 100  # type: ignore[index]
    assert b["llm_input_tokens"] == 1  # type: ignore[index]


def test_http_hook_records_into_active_tracker(monkeypatch):
    """End-to-end: the HttpClient._handle hook folds response usage in."""
    import httpx

    from schift._http import HttpClient

    # Build a mock transport that returns a chat-completions-style body.
    def transport_handler(request: httpx.Request) -> httpx.Response:
        body = {
            "id": "x",
            "usage": {"prompt_tokens": 11, "completion_tokens": 22},
        }
        return httpx.Response(200, json=body)

    transport = httpx.MockTransport(transport_handler)
    http = HttpClient(api_key="sch_test")
    # Swap the underlying client to use our mock transport.
    http._client = httpx.Client(
        base_url="https://api.schift.io/v1",
        transport=transport,
    )

    with track() as t:
        http.post("/chat", {"message": "hi"})
        http.post("/chat", {"message": "again"})

    s = t.summary()
    assert s["call_count"] == 2
    assert s["llm_input_tokens"] == 22  # 11 + 11
    assert s["llm_output_tokens"] == 44
