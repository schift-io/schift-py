"""Providers module — manage LLM provider API keys (BYOK).

Register your own OpenAI / Google / Anthropic API key so Schift's chat and
routing endpoints call the provider directly instead of using Schift Cloud's
shared quota.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional, TypedDict

if TYPE_CHECKING:
    from schift._http import HttpClient


ProviderName = Literal["openai", "google", "anthropic"]


class ProviderConfig(TypedDict):
    provider: ProviderName
    configured: bool
    endpoint_url: Optional[str]


class ProvidersModule:
    """Manage BYOK (bring-your-own-key) LLM provider credentials.

    Usage::

        client = Schift(api_key="sch_xxx")

        client.providers.set("google", api_key="AIza...")

        config = client.providers.get("openai")
        print(config["configured"])  # True / False
    """

    def __init__(self, http: HttpClient):
        self._http = http

    def get(self, provider: ProviderName) -> ProviderConfig:
        """Get the configuration status of a provider.

        The API key itself is never returned for security — only whether one
        is configured and the endpoint URL (if any).
        """
        return self._http.get(f"/providers/{provider}")

    def set(
        self,
        provider: ProviderName,
        api_key: str,
        endpoint_url: Optional[str] = None,
    ) -> ProviderConfig:
        """Register (or update) a provider API key.

        Once set, subsequent ``/v1/chat`` and ``/v1/chat/completions`` calls
        routed to this provider will use the BYOK key instead of Schift Cloud
        defaults.

        Note: the stored BYOK key shadows any env var / secret on the server.
        Rotating an env var will NOT affect an org that has a BYOK record;
        call ``set()`` again (or ``delete()``) to rotate.
        """
        payload: dict = {"api_key": api_key}
        if endpoint_url is not None:
            payload["endpoint_url"] = endpoint_url
        return self._http.put(f"/providers/{provider}", payload)
