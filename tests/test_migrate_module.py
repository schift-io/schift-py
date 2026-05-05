"""MigrateModule — feasibility / start / status wire shape + error mapping.

We exercise the **/v1/migrate** API surface used by the Schift Cloud control
plane (not the legacy local-orchestration helpers, which are covered by
the existing schift.migrate function elsewhere).
"""

from __future__ import annotations

import numpy as np
import pytest

from schift._migrate_module import MigrateModule
from schift.client import QuotaError, SchiftError


class FakeHttp:
    def __init__(self):
        self.post_calls: list[tuple] = []
        self.get_calls: list[tuple] = []
        self.next_response: dict | list = {}
        self.raise_exc: Exception | None = None

    def post(self, path, data=None):
        self.post_calls.append((path, data))
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.next_response

    def get(self, path, params=None):
        self.get_calls.append((path, params))
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.next_response


# ── feasibility ───────────────────────────────────────────────────────


def test_feasibility_posts_vectors_as_lists():
    http = FakeHttp()
    http.next_response = {
        "cka": 0.81,
        "recommended_method": "ridge",
        "holdout_cosine": 0.94,
        "calibration_samples_recommended": 5000,
        "notes": "looks good",
    }
    m = MigrateModule(http)

    src = np.arange(8, dtype=np.float32).reshape(4, 2)
    tgt = np.arange(8, dtype=np.float32).reshape(4, 2) * 2

    result = m.feasibility(src, tgt, source_model="openai/3-small", target_model="schift-embed-1")
    assert result["recommended_method"] == "ridge"

    path, body = http.post_calls[0]
    assert path == "/migrate/feasibility"
    assert body["source_model"] == "openai/3-small"
    assert body["target_model"] == "schift-embed-1"
    assert body["source_vectors"] == src.tolist()
    assert body["target_vectors"] == tgt.tolist()


# ── start ─────────────────────────────────────────────────────────────


def test_start_posts_canonical_body():
    http = FakeHttp()
    http.next_response = {"job_id": "job_abc", "state": "queued"}
    m = MigrateModule(http)

    result = m.start(
        source={"kind": "pgvector", "config": {"dsn": "x"}},
        target_collection_id="col_abc",
        method="ridge",
        retain_on_cloud=True,
    )
    assert result == {"job_id": "job_abc", "state": "queued"}

    path, body = http.post_calls[0]
    assert path == "/migrate/start"
    assert body == {
        "source": {"kind": "pgvector", "config": {"dsn": "x"}},
        "target_collection_id": "col_abc",
        "method": "ridge",
        "retain_on_cloud": True,
    }


# ── status ────────────────────────────────────────────────────────────


def test_status_gets_job_endpoint():
    http = FakeHttp()
    http.next_response = {
        "state": "running",
        "progress": 0.42,
        "n_total": 1000,
        "n_projected": 420,
    }
    m = MigrateModule(http)

    result = m.status("job_abc")
    assert result["state"] == "running"
    assert http.get_calls == [("/migrate/job_abc", None)]


# ── error mapping ─────────────────────────────────────────────────────


def test_status_propagates_quota_error():
    http = FakeHttp()
    http.raise_exc = QuotaError("Quota exceeded")
    m = MigrateModule(http)
    with pytest.raises(QuotaError):
        m.status("job_abc")


def test_start_propagates_schift_error_on_4xx():
    http = FakeHttp()
    http.raise_exc = SchiftError("API error 400: bad config")
    m = MigrateModule(http)
    with pytest.raises(SchiftError, match="400"):
        m.start(
            source={"kind": "pgvector", "config": {}},
            target_collection_id="col_abc",
        )
