"""DecisionReviewModule — call shape + error mapping."""

from __future__ import annotations

import pytest

from schift.client import EntitlementError, SchiftError
from schift.decision_review import DecisionReviewModule


class FakeHttp:
    def __init__(self):
        self.calls: list[tuple] = []
        self.next_response: dict | list = {}
        self.raise_exc: Exception | None = None

    def post(self, path, data=None):
        self.calls.append(("post", path, data))
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.next_response

    def get(self, path, params=None):
        self.calls.append(("get", path, params))
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.next_response


def test_decision_review_posts_minimal_body():
    """Only ``scenario`` + ``corpus_id`` are required; optional fields
    must be omitted from the wire body when not set."""
    http = FakeHttp()
    http.next_response = {"sub_issues": []}
    dr = DecisionReviewModule(http)

    scenario = {"subject": "s", "perspective": "p", "core_question": "q?"}
    dr(scenario=scenario, corpus_id="public--korean-standard-precedents")

    method, path, body = http.calls[0]
    assert method == "post"
    assert path == "/decision-review"
    assert body == {
        "scenario": scenario,
        "corpus_id": "public--korean-standard-precedents",
    }


def test_decision_review_includes_persona_and_caps_when_provided():
    http = FakeHttp()
    http.next_response = {"sub_issues": []}
    dr = DecisionReviewModule(http)

    dr(
        scenario={"subject": "s", "perspective": "p", "core_question": "q?"},
        corpus_id="corp",
        persona={"role": "lawyer", "language": "ko"},
        max_sub_issues=2,
        k_per_sub_issue=10,
        favorable_display_cap=3,
        counter_display_cap=3,
    )
    body = http.calls[0][2]
    assert body["persona"] == {"role": "lawyer", "language": "ko"}
    assert body["max_sub_issues"] == 2
    assert body["k_per_sub_issue"] == 10
    assert body["favorable_display_cap"] == 3
    assert body["counter_display_cap"] == 3


def test_decision_review_substrates_calls_get_endpoint():
    http = FakeHttp()
    http.next_response = {"substrates": []}
    dr = DecisionReviewModule(http)

    dr.substrates()
    assert http.calls == [("get", "/decision-review/substrates", None)]


def test_decision_review_propagates_entitlement_error():
    """403 -- decision-review is gated; surface a typed error."""
    http = FakeHttp()
    http.raise_exc = EntitlementError("Upgrade your plan")
    dr = DecisionReviewModule(http)
    with pytest.raises(EntitlementError):
        dr(
            scenario={"subject": "s", "perspective": "p", "core_question": "q?"},
            corpus_id="corp",
        )


def test_decision_review_propagates_generic_error():
    http = FakeHttp()
    http.raise_exc = SchiftError("API error 500: oops")
    dr = DecisionReviewModule(http)
    with pytest.raises(SchiftError):
        dr(
            scenario={"subject": "s", "perspective": "p", "core_question": "q?"},
            corpus_id="corp",
        )
