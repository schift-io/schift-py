"""ProvidersModule — BYOK get/set wire shape + error mapping."""

from __future__ import annotations

import pytest

from schift.client import AuthError, SchiftError
from schift.providers import ProvidersModule


class FakeHttp:
    def __init__(self):
        self.calls: list[tuple] = []
        self.next_response: dict = {}
        self.raise_exc: Exception | None = None

    def get(self, path, params=None):
        self.calls.append(("get", path, params))
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.next_response

    def put(self, path, data=None):
        self.calls.append(("put", path, data))
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.next_response


def test_providers_get_calls_provider_endpoint():
    http = FakeHttp()
    http.next_response = {
        "provider": "openai",
        "configured": True,
        "endpoint_url": None,
    }
    p = ProvidersModule(http)

    cfg = p.get("openai")
    assert cfg["provider"] == "openai"
    assert cfg["configured"] is True
    assert http.calls == [("get", "/providers/openai", None)]


def test_providers_set_puts_api_key_body():
    http = FakeHttp()
    http.next_response = {"provider": "google", "configured": True, "endpoint_url": None}
    p = ProvidersModule(http)

    p.set("google", api_key="AIza-fake")
    assert http.calls == [
        ("put", "/providers/google", {"api_key": "AIza-fake"}),
    ]


def test_providers_set_includes_endpoint_url_when_passed():
    http = FakeHttp()
    http.next_response = {
        "provider": "openai",
        "configured": True,
        "endpoint_url": "https://proxy.example.com",
    }
    p = ProvidersModule(http)

    p.set("openai", api_key="sk-x", endpoint_url="https://proxy.example.com")
    assert http.calls == [
        (
            "put",
            "/providers/openai",
            {"api_key": "sk-x", "endpoint_url": "https://proxy.example.com"},
        ),
    ]


def test_providers_get_propagates_auth_error():
    http = FakeHttp()
    http.raise_exc = AuthError("Invalid API key")
    p = ProvidersModule(http)
    with pytest.raises(AuthError):
        p.get("openai")


def test_providers_set_propagates_generic_error():
    http = FakeHttp()
    http.raise_exc = SchiftError("API error 500: oops")
    p = ProvidersModule(http)
    with pytest.raises(SchiftError):
        p.set("openai", api_key="sk-x")
