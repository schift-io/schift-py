"""Decision-review module — adversarial RAG over a registered substrate.

Pipeline: scenario → sub-issue decomposition → per-aspect retrieval →
polarity classification (supporting / counter / neutral) → verbatim verify.

Usage::

    from schift import Schift
    client = Schift(api_key="sch_...")

    result = client.decision_review(
        scenario={
            "subject": "원고가 손해배상과 별개의 대여금 채권을 함께 청구",
            "perspective": "피고 측 관할위반 주장",
            "core_question": "병합청구가 신의칙에 위배되어 관할이 부정될 수 있는가?",
        },
        corpus_id="public--korean-standard-precedents",
        persona={"role": "lawyer", "language": "ko"},
        max_sub_issues=2,
    )
    for sub in result["sub_issues"]:
        print(sub["summary"], "favorable:", len(sub["favorable"]))
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from schift._http import HttpClient


class DecisionReviewModule:
    """Adversarial RAG endpoint."""

    def __init__(self, http: "HttpClient"):
        self._http = http

    def __call__(
        self,
        *,
        scenario: dict[str, str],
        corpus_id: str,
        persona: Optional[dict[str, Any]] = None,
        max_sub_issues: Optional[int] = None,
        k_per_sub_issue: Optional[int] = None,
        favorable_display_cap: Optional[int] = None,
        counter_display_cap: Optional[int] = None,
    ) -> dict[str, Any]:
        """Run a decision review.

        ``scenario`` keys: ``subject``, ``perspective``, ``core_question``.
        ``persona`` keys (all optional): ``role`` (lawyer/doctor/analyst/auditor/custom),
        ``language`` (ko/en/...), ``decomposition_hint``.

        Returns the full server response dict (see /v1/decision-review).
        """
        body: dict[str, Any] = {"scenario": scenario, "corpus_id": corpus_id}
        if persona is not None:
            body["persona"] = persona
        if max_sub_issues is not None:
            body["max_sub_issues"] = max_sub_issues
        if k_per_sub_issue is not None:
            body["k_per_sub_issue"] = k_per_sub_issue
        if favorable_display_cap is not None:
            body["favorable_display_cap"] = favorable_display_cap
        if counter_display_cap is not None:
            body["counter_display_cap"] = counter_display_cap
        return self._http.post("/decision-review", body)

    def substrates(self) -> dict[str, Any]:
        """Enumerate registered built-in substrates available to the caller."""
        return self._http.get("/decision-review/substrates")
