# Schift Python SDK Function Inventory

> Status: Draft
> Date: 2026-03-13
> Scope: BM -> DOC -> implementation

## 1. Goal

이 문서는 Python SDK에서 최종적으로 제공해야 할 함수 표면을 먼저 고정하기 위한 초안이다.
구현 순서는 다음 기준을 따른다.

1. BM에서 직접 매출/도입 가치가 생기는 기능부터
2. 현재 코드와 가장 가까운 기능부터
3. 서버 경계가 명확한 기능부터

## 2. Product Line -> SDK Surface

| BM line | SDK area | Why it exists | Priority |
|---|---|---|---|
| Migration Fee | `client.migrate.*` | 기존 벡터를 재임베딩 없이 전환 | P0 |
| Routing Fee | `client.embed.*`, `client.routing.*` | 임베딩 호출을 Schift 경유로 통합하고 정책적으로 라우팅 | P1 |
| Layer API | `client.search.*` | query transform + retrieval + rerank | P2 |
| Schift DB | `client.db.*` | managed vector store 제공 | P3 |
| Auth/Billing | `Client(...)`, `client.usage()` | 인증과 사용량 확인 | P0-P1 |

## 2-1. Cross-surface workflow

`migrate`는 SDK 함수 하나가 아니라, 웹과 SDK가 같은 파이프라인을 다른 표면으로 노출하는 구조로 보는 게 맞다.

공통 플로우:

1. Benchmark dataset or suite 준비
2. Bench run 실행
3. Verdict 확인: `SAFE | WARN | FAIL`
4. Projection 생성
5. Dry-run migration
6. Live migration
7. 이후 모니터링 or 반복 bench

표면별 대응:

| Step | Web | SDK | Server |
|---|---|---|---|
| 데이터셋/설정 | benchmark suite 생성 화면 | `client.migrate.create_benchmark_suite(...)` | `POST /v1/benchmark-suites` |
| 반복 bench 실행 | bench run 실행 | `client.migrate.run_benchmark_suite(...)` | `POST /v1/benchmark-suites/{suite_id}/runs` |
| 단발 bench | bench 화면/CTA | `client.migrate.bench(...)` | `POST /v1/bench` |
| projection 생성 | projection 생성 UI | `client.migrate.fit(...)` | `POST /v1/projections` |
| projection 목록/상세 | projections table | `client.migrate.list_projections()`, `client.migrate.get_projection(...)` | `GET /v1/projections*` |
| migration 실행 | migrate wizard/run page | `client.migrate.run(...)` | SDK orchestration + transform API |

즉 P0 문서에는 단발 `bench/fit/run`만이 아니라, 웹에서 이어지는 "suite -> run -> projection -> migrate" 체인도 같이 있어야 한다.

## 3. Public API Shape

### 3-1. Client bootstrap

이 부분은 모든 기능의 진입점이다.

```python
from schift import Client

client = Client(
    api_key="sch_xxx",
    base_url="https://api.schift.io",
    timeout=60.0,
)
```

필수 함수:

- `Client(api_key, base_url=_DEFAULT_BASE_URL, timeout=60.0)`

추가 예정:

- `Client.from_env()`
- `client.ping()`
- `client.usage()`
- `client.usage_limits()`

원칙:

- API key는 `Client` bootstrap에서만 처리
- `client.usage()`는 고객 조회용 aggregate API
- 내부 raw usage/ledger는 public SDK에서 직접 다루지 않음

### 3-2. Migration API

이 라인이 현재 BM과 가장 직접적으로 연결된다.

```python
report = client.migrate.bench(...)
projection = client.migrate.fit(...)
result = client.migrate.run(...)
```

필수 함수:

- `client.migrate.bench(...)`
  - 내 데이터 기준 projection 품질 검증
  - 반환: `BenchReport`
- `client.migrate.create_benchmark_suite(...)`
  - 반복 실행 가능한 benchmark 설정 저장
  - 반환: `BenchmarkSuite`
- `client.migrate.list_benchmark_suites()`
- `client.migrate.get_benchmark_suite(suite_id)`
- `client.migrate.run_benchmark_suite(suite_id, ...)`
  - suite 기반 bench 실행
  - 반환: `BenchmarkRun`
- `client.migrate.list_benchmark_runs(suite_id)`
- `client.migrate.get_benchmark_run(run_id)`
- `client.migrate.fit(...)`
  - source/target 샘플로 projection 생성 요청
  - 반환: `ProjectionHandle` 또는 `Projection`
- `client.migrate.run(...)`
  - DB/파일 어댑터를 통해 실제 벡터 전환 수행
  - 반환: `MigrationResult`
- `client.migrate.list_projections()`
- `client.migrate.get_projection(projection_id)`

보조 함수:

- `schift.migrate(source, sink, projection, batch_size=1000, dry_run=False, on_batch=None)`
  - 로컬 배치 실행 엔진

현재 코드와 매핑:

- 현재 `Client.fit()` -> 최종적으로 `client.migrate.fit()`로 이동 또는 alias 유지
- 현재 `Client.bench()` -> 최종적으로 `client.migrate.bench()`로 이동 또는 alias 유지
- 현재 `list_projections()` / `get_projection()` -> `client.migrate.*` namespace로 정리
- 서버에는 이미 `benchmark suite/run` API가 있으므로 SDK도 동일 개념을 노출해야 함
- 현재 top-level `migrate(...)` 함수는 low-level engine으로 유지 가능

### 3-3. Embedding Router API

이 라인은 "OpenRouter for embeddings" 포지션이다.

```python
vector = client.embed.create(
    text="quarterly revenue report",
    model="openai/text-embedding-3-large",
)

vectors = client.embed.batch(
    texts=["a", "b", "c"],
    model="auto",
)

models = client.embed.list_models()
```

필수 함수:

- `client.embed.create(text, model, dimensions=None, metadata=None)`
- `client.embed.batch(texts, model, dimensions=None, metadata=None)`
- `client.embed.list_models()`
- `client.embed.get_model(model_id)`

후속 함수:

- `client.embed.auto(text, objective="quality" | "cost" | "latency")`
- `client.embed.providers()`

### 3-4. Routing Policy API

`embed`가 실행 표면이라면, `routing`은 제어 표면이다.
OpenRouter식으로 고객이 실제로 필요한 것은 모델 카탈로그만이 아니라 "어떤 조건에서 어디로 보낼지"다.

```python
policy = client.routing.create_policy(
    name="prod-default",
    default_model="openai/text-embedding-3-large",
    strategy="latency",
    fallbacks=[
        "google/gemini-embedding-004",
        "voyage/voyage-3-large",
    ],
)

route = client.routing.resolve(
    policy="prod-default",
    input_type="query",
)

preview = client.routing.preview(
    policy="prod-default",
    text="quarterly revenue report",
)
```

필수 함수:

- `client.routing.create_policy(name, default_model, strategy, fallbacks=None, constraints=None)`
- `client.routing.list_policies()`
- `client.routing.get_policy(policy_id_or_name)`
- `client.routing.update_policy(policy_id_or_name, ...)`
- `client.routing.resolve(policy, input_type=None, metadata=None)`
- `client.routing.preview(policy, text=None, texts=None, metadata=None)`

후속 함수:

- `client.routing.delete_policy(policy_id_or_name)`
- `client.routing.events(window="24h", policy=None)`
- `client.routing.health()`

최소 정책 필드:

- `default_model`
- `strategy`
- `fallbacks`
- `allowed_providers`
- `blocked_providers`
- `max_unit_cost`
- `latency_budget_ms`

`preview()`가 중요한 이유:

- 실제 전송 전에 어떤 provider/model이 선택될지 확인 가능
- 왜 그 route가 선택됐는지 설명 가능
- failover 체인을 미리 검증 가능

### 3-5. Search / Proxy API

이 라인은 BYODB와 Schift DB 둘 다 커버해야 한다.

```python
results = client.search.query(
    query="2024 annual report",
    index="schift://docs",
    model="openai/text-embedding-3-large",
    top_k=10,
)
```

필수 함수:

- `client.search.query(query, index, model=None, top_k=10, rerank=False, filters=None)`
- `client.search.rerank(query, candidates, top_k=None)`
- `client.search.analytics(index, window="7d")`

후속 함수:

- `client.search.hybrid(...)`
- `client.search.cache.clear(index=None)`

### 3-6. Managed DB API

이 라인은 managed vector DB 도입 이후 필요하다.

```python
client.db.create_collection(name="docs", dimension=3072)
client.db.upsert(collection="docs", vectors=[...])
hits = client.db.query(collection="docs", vector=query_vec, top_k=10)
```

필수 함수:

- `client.db.create_collection(name, dimension, metric="cosine")`
- `client.db.list_collections()`
- `client.db.delete_collection(name)`
- `client.db.upsert(collection, vectors)`
- `client.db.delete(collection, ids)`
- `client.db.query(collection, vector=None, text=None, top_k=10, filters=None)`

## 4. Supporting Types

함수보다 먼저 계약을 고정해야 하는 타입들:

- `Projection`
- `BenchReport`
- `BenchmarkSuite`
- `BenchmarkRun`
- `RoutingPolicy`
- `RoutingDecision`
- `MigrationResult`
- `EmbeddingResult`
- `SearchResult`
- `CollectionInfo`
- `UsageReport`
- `UsageLimits`

최소 필드 초안:

| Type | Required fields |
|---|---|
| `Projection` | `project_id`, `source_model`, `target_model`, `source_dim`, `target_dim`, `method`, `quality` |
| `BenchReport` | `verdict`, `original`, `projected`, `source_model`, `target_model` |
| `BenchmarkSuite` | `suite_id`, `name`, `source_model`, `target_model`, `sample_ratios` |
| `BenchmarkRun` | `run_id`, `suite_id`, `status`, `report`, `created_at` |
| `RoutingPolicy` | `policy_id`, `name`, `default_model`, `strategy`, `fallbacks` |
| `RoutingDecision` | `policy`, `selected_model`, `selected_provider`, `reason`, `fallback_used` |
| `MigrationResult` | `total`, `migrated`, `dry_run`, `source_dim`, `target_dim` |
| `EmbeddingResult` | `model`, `dimensions`, `vectors`, `usage` |
| `SearchResult` | `id`, `score`, `metadata` |
| `UsageReport` | `window`, `group_by`, `totals`, `breakdown` |
| `UsageLimits` | `plan`, `quota`, `consumed`, `remaining`, `reset_at` |

## 5. Server Boundary

여기서 먼저 못 박아야 할 규칙:

- Projection matrix를 SDK에 기본적으로 내리지 않는다.
- migration 실행 시 SDK는 "읽기/쓰기 orchestration" 역할만 맡는다.
- 학습, query transform, rerank, usage metering은 서버 책임이다.
- 예외적으로 `Projection`을 내려주는 로컬 모드는 별도 상품/플래그로 분리 검토한다.

이 규칙 때문에 함수 설계도 두 층으로 나뉜다.

- high-level API: `client.migrate.fit()`, `client.search.query()`
- low-level local API: `Projection.transform()`, `schift.migrate(...)`

## 6. Recommended Implementation Order

### Phase 1

- `Client` auth/bootstrap 정리
- `client.migrate.create_benchmark_suite()`
- `client.migrate.list_benchmark_suites()`
- `client.migrate.run_benchmark_suite()`
- `client.migrate.fit()`
- `client.migrate.bench()`
- `client.migrate.run()`
- 기존 `Client.fit()` / `Client.bench()`는 하위 호환 alias 유지

### Phase 2

- `client.embed.create()`
- `client.embed.batch()`
- `client.embed.list_models()`
- `client.routing.create_policy()`
- `client.routing.resolve()`
- `client.routing.preview()`

### Phase 3

- `client.search.query()`
- `client.search.rerank()`
- `client.search.analytics()`

### Phase 4

- `client.db.*`
- `client.usage()`

## 7. Open Questions Before Implementation

- `Projection`을 항상 서버 보관형으로 갈지, 로컬 다운로드를 허용할지
- migration 입력을 ndarray 중심으로 둘지, adapter/url 중심으로 둘지
- `client.search.query()`에서 `text query`와 `vector query`를 한 함수로 받을지 분리할지
- `client.db.query()`가 `text` 입력 시 내부적으로 `embed.create()`를 호출할지 명시적으로 분리할지
- routing policy를 account 전역으로 둘지, 앱/인덱스 단위로 둘지
- `embed.create(..., model="auto")`를 내부적으로 `routing.resolve()` alias로 볼지 분리할지

## 8. Current Decision

지금 바로 구현 대상으로 볼 최소 함수 집합은 아래다.

- `Client(...)`
- `client.migrate.create_benchmark_suite(...)`
- `client.migrate.list_benchmark_suites()`
- `client.migrate.get_benchmark_suite(...)`
- `client.migrate.run_benchmark_suite(...)`
- `client.migrate.list_benchmark_runs(...)`
- `client.migrate.get_benchmark_run(...)`
- `client.migrate.bench(...)`
- `client.migrate.fit(...)`
- `client.migrate.run(...)`
- `client.migrate.list_projections()`
- `client.migrate.get_projection(...)`

그 다음 우선순위는 아래다.

- `client.embed.create(...)`
- `client.embed.batch(...)`
- `client.embed.list_models()`
- `client.routing.create_policy(...)`
- `client.routing.resolve(...)`
- `client.routing.preview(...)`

나머지 search/db는 문서 계약만 유지하고 구현은 뒤로 미룬다.
