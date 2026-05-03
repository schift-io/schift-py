"""Client-side TokenTracker — accumulate per-call usage locally.

Phase A: in-process accumulator. Walks response bodies for a ``usage`` field
and folds it into the active :class:`TokenTracker`. The 6 axis slots map to
the server-side metering axes (``search``, ``ingest``, ``execution``,
``web_search``, ``llm``, ``storage``). Axes the server does not currently
expose per-response stay at zero; Phase B will fill those in via response
headers.

Inspired by LightRAG's ``TokenTracker`` pattern (lightrag/utils.py:2614-2670)
extended for our 6 axis slots and asyncio-safe via :mod:`contextvars`.

Example::

    from schift import Schift, track

    client = Schift(api_key="sch_xxx")
    with track() as t:
        client.chat.send(bucket="docs", message="hello")
        client.chat.send(bucket="docs", message="another")

    print(t.summary())
    # {
    #   "call_count": 2,
    #   "llm_input_tokens": 35,
    #   "llm_output_tokens": 412,
    #   "search_calls": 0,
    #   ...
    #   "cost_estimate_usd": None,
    # }
"""

from __future__ import annotations

import contextvars
import threading
from typing import Any, Dict, Mapping, Optional

__all__ = ["TokenTracker", "track", "active_tracker"]


# 6 axes mirroring api/server/billing/pricing.py + store/usage.py axis names.
# Names are SDK-local; map to server axes is documented in each comment.
_AXES: tuple[str, ...] = (
    "llm_input_tokens",   # server axis: "llm" (prompt tokens)
    "llm_output_tokens",  # server axis: "llm" (completion tokens)
    "search_calls",       # server axis: "search"
    "rerank_calls",       # surfaced in usage.py but not its own server axis yet
    "ingest_pages",       # server axis: "ingest"
    "execution_calls",    # server axis: "execution" (agent runs / workflow runs)
    "web_search_calls",   # server axis: "web_search"
    "storage_bytes",      # server axis: "storage" (rarely per-call; bucket totals)
    "embed_tokens",       # rolled under "llm" server-side today; SDK keeps it
                          # separate so dev can see embed-vs-llm split.
)


class TokenTracker:
    """In-process accumulator for client-side usage.

    Thread-safe via an internal lock. Multiple SDK calls within a ``with
    track():`` block fold into the same tracker. Nested trackers are
    independent — the innermost active tracker wins for each call.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._call_count = 0
        self._totals: Dict[str, int] = {axis: 0 for axis in _AXES}
        # Phase A: cost is not computed locally (price truth lives in
        # api/server/pricing.py + docs/research/PRICING.md). Phase B will
        # surface dollar value via response headers.
        self._cost_estimate_usd: Optional[float] = None

    # ---- public API ----

    def add_usage(self, axis: str, amount: int) -> None:
        """Add ``amount`` to ``axis``. Unknown axes are silently ignored."""
        if axis not in self._totals:
            return
        if not amount:
            return
        with self._lock:
            self._totals[axis] += int(amount)

    def add_call(self, *, count: int = 1) -> None:
        """Record one (or more) API calls. Called by the HTTP layer hook."""
        with self._lock:
            self._call_count += int(count)

    def record_response(self, body: Any) -> None:
        """Extract usage info from a response body and fold it in.

        Recognises:

        - ``{"usage": {"prompt_tokens": ..., "completion_tokens": ...}}`` —
          OpenAI-style chat/completions response (chat, completions, RAG).
        - ``{"usage": {"input_tokens": ..., "output_tokens": ...}}`` —
          Anthropic-style.
        - ``{"usage": {"total_tokens": ...}}`` — embed/rerank fallback,
          counted as ``embed_tokens``.

        Bodies without a ``usage`` field still increment ``call_count`` so
        dev can see "I made N calls today" even when token info is missing.
        """
        self.add_call()
        if not isinstance(body, Mapping):
            return
        usage = body.get("usage")
        if not isinstance(usage, Mapping):
            return

        # OpenAI-style
        prompt = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
        completion = usage.get("completion_tokens") or usage.get("output_tokens") or 0
        if prompt or completion:
            self.add_usage("llm_input_tokens", prompt)
            self.add_usage("llm_output_tokens", completion)
            return

        # Embed / rerank fallback — total_tokens with no split.
        total = usage.get("total_tokens") or 0
        if total:
            self.add_usage("embed_tokens", total)

    def summary(self) -> Dict[str, Any]:
        """Return a snapshot of the current totals.

        ``cost_estimate_usd`` is ``None`` in Phase A; Phase B will populate
        it from server-provided headers.
        """
        with self._lock:
            out: Dict[str, Any] = {"call_count": self._call_count}
            out.update(self._totals)
            out["cost_estimate_usd"] = self._cost_estimate_usd
            return out

    def reset(self) -> None:
        """Clear all accumulated counters."""
        with self._lock:
            self._call_count = 0
            for k in self._totals:
                self._totals[k] = 0
            self._cost_estimate_usd = None

    # ---- context manager ----

    def __enter__(self) -> "TokenTracker":
        self._token = _active_tracker.set(self)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _active_tracker.reset(self._token)

    def __repr__(self) -> str:  # pragma: no cover - debug only
        return f"TokenTracker(calls={self._call_count}, totals={self._totals})"


# Active tracker is per-context (asyncio task / thread / sync). Using
# contextvars.ContextVar means concurrent asyncio coroutines each see their
# own tracker without bleeding across.
_active_tracker: "contextvars.ContextVar[Optional[TokenTracker]]" = (
    contextvars.ContextVar("schift_active_tracker", default=None)
)


def track() -> TokenTracker:
    """Create a new :class:`TokenTracker` bound to the current context.

    Use as a context manager::

        with track() as t:
            client.chat.send(...)
        print(t.summary())
    """
    return TokenTracker()


def active_tracker() -> Optional[TokenTracker]:
    """Return the currently-active tracker for this context, if any."""
    return _active_tracker.get()
