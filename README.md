# Schift Python SDK

Python client and local migration toolkit for Schift.

The package currently exposes two public client styles:

- `Schift`: modular client for live API operations such as catalog lookup, embedding, routing, search, usage, and hosted collection management.
- `Client`: legacy projection client for fitting and downloading `Projection` objects that run locally.

## Install

Base package:

```bash
pip install schift
```

Optional adapters:

```bash
pip install "schift[postgres]"
pip install "schift[qdrant]"
pip install "schift[all]"
```

Development extras:

```bash
pip install -e ".[dev]"
```

## Authentication And Base URLs

The modular client reads `SCHIFT_API_KEY` automatically:

```bash
export SCHIFT_API_KEY=sch_your_key_here
```

Equivalent explicit construction:

```python
from schift import Schift

client = Schift(
    api_key="sch_your_key_here",
    base_url="https://api.schift.io/v1",
    timeout=60.0,
)
```

Notes:

- `Schift` expects a `/v1` base URL.
- The legacy `Client` defaults to `https://api.schift.io` and appends `/v1/...` internally.

## Client Lifecycle

`Schift` holds a shared `httpx.Client`, so prefer a context manager for short-lived scripts:

```python
from schift import Schift

with Schift() as client:
    models = client.catalog.list()
```

For long-running processes, keep one `Schift` instance and call `close()` during shutdown.

## Quickstart

```python
from schift import Schift

with Schift() as client:
    models = client.catalog.list()
    vector = client.embed(
        "quarterly revenue report",
        model="openai/text-embedding-3-small",
    )

    client.db.create_collection(name="finance-docs", dimension=len(vector))
    client.db.upsert(
        collection="finance-docs",
        vectors=[
            {
                "id": "doc-1",
                "values": vector.tolist(),
                "metadata": {"source": "q1-report"},
            }
        ],
    )

    hits = client.query(
        "revenue guidance",
        collection="finance-docs",
        top_k=5,
    )

    print(models[0]["id"] if models else "no models")
    print(hits[0] if hits else "no hits")
```

## Module Reference

### `catalog`

List available models and inspect one model by ID.

```python
from schift import Schift

with Schift() as client:
    models = client.catalog.list()
    model = client.catalog.get("openai/text-embedding-3-small")
```

### `embed`

The embed module is callable for single-text requests and exposes `batch()` for multiple texts.

```python
from schift import Schift

with Schift() as client:
    one = client.embed(
        "hello world",
        model="openai/text-embedding-3-small",
    )

    many = client.embed.batch(
        texts=["hello", "goodbye"],
        model="openai/text-embedding-3-small",
        dimensions=1024,
    )
```

Return values are NumPy arrays.

### `routing`

Read or update the server-side routing policy used by Schift when a model is omitted.

```python
from schift import Schift

with Schift() as client:
    current = client.routing.get()
    updated = client.routing.set(
        primary="openai/text-embedding-3-small",
        fallback="google/gemini-embedding-001",
        mode="failover",
    )
```

### `bench`

Run a server-side benchmark between two model IDs. The SDK returns `BenchReport`.

```python
from schift import Schift

with Schift() as client:
    report = client.bench.run(
        source="openai/text-embedding-3-small",
        target="google/gemini-embedding-001",
        data="./eval_queries.jsonl",
    )

    print(report.verdict)
    print(report.summary())
```

### `db`

Manage hosted collections and write vectors or raw documents.

```python
from schift import Schift

with Schift() as client:
    vector = client.embed(
        "Schift reduces vector migration downtime.",
        model="openai/text-embedding-3-small",
    )

    collection = client.db.create_collection(
        name="product-docs",
        dimension=len(vector),
    )

    client.db.upsert(
        collection="product-docs",
        vectors=[
            {
                "id": "doc-1",
                "values": vector.tolist(),
                "metadata": {"title": "Launch plan"},
            }
        ],
    )

    client.db.upsert_text(
        collection="product-docs",
        documents=[
            {
                "id": "doc-2",
                "text": "Schift reduces vector migration downtime.",
                "metadata": {"title": "Overview"},
            }
        ],
        model="openai/text-embedding-3-small",
    )

    stats = client.db.collection_stats("product-docs")
```

Available methods:

- `create_collection(name, dimension)`
- `list_collections()`
- `get_collection(name)`
- `collection_stats(name)`
- `delete_collection(name)`
- `upsert(collection, vectors)`
- `upsert_text(collection, documents, model)`

### `query`

The query module is callable and supports hosted collections or an external DB handle.

```python
from schift import Schift

with Schift() as client:
    hosted = client.query(
        "vector migration rollback plan",
        collection="product-docs",
        top_k=10,
        rerank=True,
        rerank_top_k=5,
    )

    passthrough = client.query(
        "incident response",
        db="prod-search-db",
        model="openai/text-embedding-3-small",
        top_k=5,
    )
```

### `rerank`

Rerank a list of candidate documents with a cross-encoder style endpoint.

```python
from schift import Schift

with Schift() as client:
    reranked = client.rerank(
        "incident response",
        documents=[
            {"id": "doc-1", "text": "..."},
            {"id": "doc-2", "text": "..."},
        ],
        top_k=2,
    )
```

### `usage`

Fetch aggregate usage for billing or dashboards.

```python
from schift import Schift

with Schift() as client:
    usage = client.usage.get(period="30d", granularity="day")
```

## Workflows

Build and run RAG pipelines as composable DAGs.

### Quick Start

```python
from schift import Schift

with Schift() as client:
    # Create from template
    wf = client.workflow.create_rag("Product Search")

    # Run with inputs
    result = client.workflow.run(wf.id, inputs={"query": "best laptop"})
    print(result.outputs["answer"])
```

### CRUD

```python
wf = client.workflow.create("My Pipeline", description="Custom RAG")
workflows = client.workflow.list()
wf = client.workflow.get(wf.id)
wf = client.workflow.update(wf.id, name="Renamed")
client.workflow.delete(wf.id)
```

### Building a Graph

```python
wf = client.workflow.create("Custom RAG")

# Add blocks
start = client.workflow.add_block(wf.id, "start", title="Start")
retriever = client.workflow.add_block(wf.id, "retriever", config={
    "collection": "my-docs",
    "top_k": 5,
    "rerank": True,
    "rerank_top_k": 3,
})
prompt = client.workflow.add_block(wf.id, "prompt_template", config={
    "template": "Answer based on:\n{{results}}\n\nQuestion: {{query}}",
})
llm = client.workflow.add_block(wf.id, "llm", config={
    "model": "openai/gpt-4o-mini",  # or "anthropic/claude-sonnet-4-20250514", "gemini-2.5-flash"
    "temperature": 0.7,
})
end = client.workflow.add_block(wf.id, "end")

# Connect blocks
client.workflow.add_edge(wf.id, start["id"], retriever["id"])
client.workflow.add_edge(wf.id, retriever["id"], prompt["id"])
client.workflow.add_edge(wf.id, prompt["id"], llm["id"])
client.workflow.add_edge(wf.id, llm["id"], end["id"])
```

### Multiple Inputs

The start node forwards all input variables to downstream blocks:

```python
result = client.workflow.run(wf.id, inputs={
    "query": "maternity leave policy",
    "user_id": "u-123",
    "language": "ko",
})
```

Reference variables in prompt templates with `{{variable}}` syntax.

### Validation & Run History

```python
# Validate graph (cycles, missing connections, etc.)
v = client.workflow.validate(wf.id)
print(v.valid, v.errors)

# List past runs
runs = client.workflow.runs(wf.id)
for r in runs:
    print(r.run_id, r.status, r.outputs)
```

### YAML Import / Export

```python
# Export to YAML
yaml_str = client.workflow.to_yaml(wf.id, path="pipeline.yaml")

# Load from file
definition = client.workflow.from_yaml("pipeline.yaml")

# Push YAML to create on server
wf = client.workflow.push_yaml("pipeline.yaml")
```

### Templates

| Method | Template |
|--------|----------|
| `create_rag(name)` | Retriever -> Prompt -> LLM |
| `create_doc_qa(name)` | Document QA with sources |
| `create_chat(name)` | Conversational RAG |
| `create_ocr_ingest(name)` | OCR -> Chunk -> Embed |

### Async Workflows

```python
from schift import AsyncSchift

async with AsyncSchift() as client:
    wf = await client.workflow.create_rag("Async RAG")
    result = await client.workflow.run(wf.id, inputs={"query": "hello"})
```

### Block Types

| Category | Types |
|----------|-------|
| Control | `start`, `end`, `conditional`, `loop` |
| Retrieval | `retriever` (with rerank toggle), `reranker` |
| LLM | `llm` (OpenAI/Anthropic/Google), `prompt_template`, `answer` |
| Data | `document_loader`, `chunker`, `embedder`, `text_processor` |
| Integration | `api_call`, `webhook`, `code_executor` |
| Storage | `vector_store`, `cache` |

### API Reference

| Method | Description |
|--------|-------------|
| `workflow.create(name)` | Create workflow |
| `workflow.get(id)` | Get workflow |
| `workflow.list()` | List workflows |
| `workflow.update(id, **kw)` | Update workflow |
| `workflow.delete(id)` | Delete workflow |
| `workflow.run(id, inputs)` | Run workflow |
| `workflow.runs(id)` | List past runs |
| `workflow.validate(id)` | Validate graph |
| `workflow.add_block(id, type, config)` | Add block |
| `workflow.add_edge(id, src, tgt)` | Add edge |
| `workflow.to_yaml(id)` | Export as YAML |
| `workflow.from_yaml(path)` | Load YAML definition |
| `workflow.push_yaml(path)` | Import YAML to server |

## Projection Workflow

Projection creation still lives in the legacy `Client` API. It returns a local `Projection` object that can transform vectors without further API calls.

```python
from schift import Client

legacy = Client(api_key="sch_your_key_here")

# Embed the same sample texts with both providers before fitting.
source_pairs = old_model_embeddings
target_pairs = new_model_embeddings

projection = legacy.fit(
    source=source_pairs,
    target=target_pairs,
    source_model="openai/text-embedding-3-small",
    target_model="google/gemini-embedding-001",
    project_name="openai-to-gemini",
)

converted = projection.transform(source_pairs[:10])
projection.save("./projection-openai-to-gemini")
```

You can later reload a saved projection:

```python
from schift import Projection

projection = Projection.load("./projection-openai-to-gemini")
```

The legacy client also supports:

- `fit(...)`
- `bench(...)`
- `list_projections()`
- `get_projection(project_id)`

## Local Migration With Adapters

The local migration engine reads vectors from a source adapter, applies a `Projection`, and writes to a sink adapter. This path does not depend on hosted collection APIs.

```python
from schift import Projection
from schift.migrate import migrate
from schift.adapters.file import NpyAdapter

projection = Projection.load("./projection-openai-to-gemini")

source = NpyAdapter("old_embeddings.npy")
sink = NpyAdapter("new_embeddings.npy")

result = migrate(
    source=source,
    sink=sink,
    projection=projection,
    batch_size=2048,
    dry_run=True,
)

print(result)
```

The same engine is exposed through `Schift().migrate.run(...)`.

### Built-in Adapters

#### NumPy files

```python
from schift.adapters.file import NpyAdapter

adapter = NpyAdapter("embeddings.npy")
```

#### pgvector

Requires `pip install "schift[postgres]"`.

```python
from schift.adapters.pgvector import PgVectorAdapter

adapter = PgVectorAdapter(
    conninfo="postgresql://user:password@localhost/mydb",
    table="documents",
    embedding_column="embedding",
    id_column="id",
)
```

#### Qdrant

Requires `pip install "schift[qdrant]"`.

```python
from schift.adapters.qdrant import QdrantAdapter

adapter = QdrantAdapter(
    url="http://localhost:6333",
    collection="documents",
    api_key=None,
)
```

#### Registry Helpers

```python
from schift.adapters import get_adapter, list_adapters

print(list_adapters())

adapter = get_adapter(
    {
        "type": "npy",
        "path": "embeddings.npy",
    }
)
```

## Errors

Both client styles raise exceptions from `schift.client`:

- `AuthError`
- `QuotaError`
- `SchiftError`

Example:

```python
from schift import Schift
from schift.client import AuthError, QuotaError, SchiftError

try:
    with Schift() as client:
        client.catalog.list()
except AuthError:
    ...
except QuotaError:
    ...
except SchiftError:
    ...
```

## Development

From `sdk/python/`:

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest
```

## Source Layout

```text
sdk/python/
├── schift/
│   ├── schift_client.py   # modular SDK entry point
│   ├── client.py          # legacy projection client
│   ├── projection.py      # local projection object
│   ├── adapters/          # npy, pgvector, qdrant
│   ├── workflow.py         # workflow CRUD, blocks, edges, YAML, templates
│   └── *.py               # catalog, embed, routing, db, query, rerank, usage
└── docs/                  # request/response contracts and schemas
```
