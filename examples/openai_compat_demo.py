"""OpenAI SDK drop-in demo against Schift.

Demonstrates that pointing the official `openai` Python SDK at Schift's
`/v1/openai` base URL unlocks vector_stores + files + search end-to-end
without any other code changes.

Setup:
    pip install openai
    export SCHIFT_API_KEY=sk-schift-...

Run:
    python sdk/python/examples/openai_compat_demo.py

Optional override:
    SCHIFT_BASE_URL=http://localhost:8000/v1/openai python ...
"""

from __future__ import annotations

import os
import sys
import time

try:
    from openai import OpenAI
except ImportError:
    sys.stderr.write("Install the OpenAI SDK first:  pip install openai\n")
    sys.exit(1)


BASE_URL = os.environ.get("SCHIFT_BASE_URL", "https://api.schift.io/v1/openai")
API_KEY = os.environ.get("SCHIFT_API_KEY") or os.environ.get("OPENAI_API_KEY")

if not API_KEY:
    sys.stderr.write("Set SCHIFT_API_KEY (or OPENAI_API_KEY) first.\n")
    sys.exit(1)

# This is the entire migration: change the base URL.
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def header(label: str) -> None:
    print(f"\n=== {label} ===")


# 1. Files API — global file storage (purpose=assistants).
header("Upload file")
file_obj = client.files.create(
    file=("policy.txt", (b"Refund policy: customers may request a full refund within 14 days of purchase. "
                       b"Partial refunds (50%) are available between 15 and 30 days. After 30 days, no "
                       b"refunds are issued. Contact support@example.com for any questions about this policy. ") * 8, "text/plain"),
    purpose="assistants",
)
print(f"file_id={file_obj.id}  bytes={file_obj.bytes}  purpose={file_obj.purpose}")

# 2. Vector store — create with metadata + expires_after (Schift autopilots
#    chunking but persists the strategy hint for round-trip).
header("Create vector store")
vs = client.vector_stores.create(
    name=f"demo-{int(time.time())}",
    metadata={"team": "support", "env": "demo"},
    expires_after={"anchor": "last_active_at", "days": 7},
)
print(f"vector_store={vs.id}  metadata={vs.metadata}  expires_after={vs.expires_after}")

# 3. Attach file to vector store with filterable attributes.
header("Attach file → vector store")
vsf = client.vector_stores.files.create(
    vector_store_id=vs.id,
    file_id=file_obj.id,
    attributes={"category": "refund", "priority": 5},
)
print(f"vector_store.file={vsf.id}  status={vsf.status}  attributes={vsf.attributes}")

# Wait for indexing (in real apps, poll until status='completed').
header("Wait for indexing")
for _ in range(30):
    refreshed = client.vector_stores.files.retrieve(
        vector_store_id=vs.id, file_id=vsf.id,
    )
    print(f"  status={refreshed.status}")
    if refreshed.status in ("completed", "failed"):
        break
    time.sleep(1)

# 4. Search with structured attribute filter.
header("Search with attribute filter")
results = client.vector_stores.search(
    vector_store_id=vs.id,
    query="refund policy",
    max_num_results=5,
    filters={
        "type": "and",
        "filters": [
            {"type": "eq", "key": "category", "value": "refund"},
            {"type": "gte", "key": "priority", "value": 1},
        ],
    },
)
for hit in results.data:
    print(f"  {hit.score:.3f}  {hit.filename}  attrs={hit.attributes}")

# 5. Modify the vector store metadata.
header("Modify vector store")
modified = client.vector_stores.update(
    vector_store_id=vs.id,
    metadata={"team": "support", "env": "demo", "owner": "jskang"},
)
print(f"updated metadata={modified.metadata}")

# 6. Cleanup.
header("Cleanup")
client.vector_stores.files.delete(vector_store_id=vs.id, file_id=vsf.id)
client.vector_stores.delete(vector_store_id=vs.id)
client.files.delete(file_id=file_obj.id)
print("done")
