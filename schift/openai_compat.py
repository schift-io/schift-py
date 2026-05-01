"""OpenAI SDK drop-in helper.

Schift exposes an OpenAI Vector Stores + Files compatible surface at
`/v1/openai/*`. `openai_client()` returns a stock `OpenAI` instance pointed at
that surface so existing OpenAI SDK code can target Schift by changing one
import — no new client to learn.

Example:
    from schift.openai_compat import openai_client

    client = openai_client()  # picks up SCHIFT_API_KEY from env
    vs = client.vector_stores.create(name="kb", metadata={"team": "support"})
    file = client.files.create(file=open("policy.pdf", "rb"), purpose="assistants")
    client.vector_stores.files.create(vector_store_id=vs.id, file_id=file.id)
    results = client.vector_stores.search(
        vector_store_id=vs.id, query="refund policy",
        filters={"type": "eq", "key": "category", "value": "refund"},
    )

Requires the optional `openai` package:
    pip install schift[openai]   # or: pip install openai
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openai import OpenAI


_DEFAULT_BASE_URL = "https://api.schift.io/v1/openai"


def openai_client(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    **kwargs: Any,
) -> "OpenAI":
    """Return an OpenAI client pointed at Schift's OpenAI-compat surface.

    Args:
        api_key: Schift API key. Falls back to ``SCHIFT_API_KEY`` then
            ``OPENAI_API_KEY`` env vars.
        base_url: Override the default ``https://api.schift.io/v1/openai``.
            Useful for staging or self-hosted Enterprise deployments.
        **kwargs: Forwarded to ``openai.OpenAI(...)`` (timeout, max_retries,
            http_client, default_headers, etc.).

    Raises:
        ImportError: if the optional ``openai`` package is not installed.
        ValueError: if no API key can be resolved.
    """
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - exercised at runtime
        raise ImportError(
            "schift.openai_compat requires the openai package. "
            "Install with: pip install openai"
        ) from exc

    resolved_key = (
        api_key
        or os.environ.get("SCHIFT_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    if not resolved_key:
        raise ValueError(
            "API key required. Pass api_key= or set SCHIFT_API_KEY / "
            "OPENAI_API_KEY in the environment."
        )

    return OpenAI(
        api_key=resolved_key,
        base_url=base_url or _DEFAULT_BASE_URL,
        **kwargs,
    )


__all__ = ["openai_client"]
