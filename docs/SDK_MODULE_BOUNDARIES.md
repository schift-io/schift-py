# SDK Module Boundaries

> Status: Draft
> Date: 2026-03-13
> Purpose: `migrate`, `embed`, `routing`, `db`, `search`의 역할을 헷갈리지 않게 분리

## 1. One-line definitions

```text
migrate = 이미 있는 벡터를 새 모델 공간으로 옮기는 것
embed   = 텍스트를 벡터로 만드는 것
routing = 우리 모델 리스트 안에서 어떤 모델로 갈아끼울지 결정하는 것
db      = 벡터를 저장/관리하는 것
search  = query를 받아서 관련 벡터/문서를 찾는 것
```

## 2. Big picture

```text
Text
  │
  ├─ embed
  │    └─ text -> vector
  │
  ├─ routing
  │    └─ embed를 어디로 보낼지 결정
  │
  ├─ db
  │    └─ vector 저장
  │
  └─ search
       └─ query -> retrieval result

Existing vectors
  │
  └─ migrate
       └─ old vector space -> new vector space
```

## 3. Module by module

### `migrate`

무엇을 해주나:

- 이미 저장된 벡터를 새 모델 기준으로 전환
- 재임베딩 없이 migration 가능하게 함
- migration 전에 bench로 품질 검증

입력:

- 기존 벡터
- source model / target model
- 또는 projection / benchmark suite

출력:

- bench report
- projection
- migration result

하지 않는 것:

- 원문 텍스트를 새로 임베딩하는 것
- query serving 자체

대표 질문:

- "OpenAI 벡터를 Gemini 기준으로 바꿀 수 있나?"
- "원문이 없어도 migration 되나?"

### `embed`

무엇을 해주나:

- 텍스트를 임베딩 벡터로 변환
- 여러 provider를 같은 API로 호출
- 단일/배치 임베딩 제공

입력:

- text 또는 texts
- model

출력:

- embedding vector(s)

하지 않는 것:

- 어떤 모델을 쓸지 정책적으로 결정하는 것
- 기존 벡터를 다른 공간으로 바꾸는 것

대표 질문:

- "이 텍스트를 벡터로 만들어줘"
- "OpenAI든 Gemini든 같은 코드로 호출하고 싶다"

### `routing`

무엇을 해주나:

- 우리 모델 카탈로그 안에서 어떤 모델을 쓸지 결정
- 모델 스위칭 정책 관리
- fallback/failover 정책 관리
- 비용/품질/latency 기준으로 route 선택

입력:

- routing policy
- model catalog
- input type
- metadata

출력:

- routing decision
- preview
- failover / usage events

하지 않는 것:

- 직접 벡터 저장
- 직접 search 수행
- migration 수행
- catalog 밖의 임의 모델을 무제한 허용하는 것

대표 질문:

- "OpenAI에서 Gemini로 갈아끼우려면 기본 모델을 뭘로 잡지?"
- "장애 나면 우리 모델 리스트 중 어디로 fallback하지?"
- "가장 싼 모델로 갈아끼우되 latency는 1초 이하여야 해"

### `db`

무엇을 해주나:

- 벡터 저장소 관리
- collection 생성/삭제
- vector upsert/delete/query

입력:

- collection definition
- vector records
- metadata

출력:

- collection info
- query hits
- storage stats

하지 않는 것:

- route 정책 결정
- migration 품질 평가

대표 질문:

- "벡터를 어디에 저장하지?"
- "Schift managed DB로 바로 넣고 싶다"

### `search`

무엇을 해주나:

- query를 받아 retrieval 실행
- 필요시 query transform, rerank, cache 적용
- BYODB 또는 Schift DB 위에서 검색

입력:

- query text 또는 query vector
- index / collection
- top_k / filters

출력:

- ranked results
- analytics

하지 않는 것:

- 기존 전체 벡터 migration
- raw embedding provider policy 관리

대표 질문:

- "이 질문과 관련된 문서 10개 찾아줘"
- "검색 품질을 rerank로 올리고 싶다"

## 4. The clean boundary

```text
migrate = offline or batch transition path
embed   = online vector creation path
routing = online model switching layer for embed path
db      = storage layer
search  = retrieval layer
```

## 5. Relationship table

| Module | Primary object | Main verb | Time horizon |
|---|---|---|---|
| `migrate` | existing vectors | convert | batch/offline |
| `embed` | text | encode | online |
| `routing` | model catalog choice | switch/decide | online |
| `db` | vector store | store | persistent |
| `search` | query | retrieve | online |

## 6. What users should feel

```text
Need a vector now?           -> embed
Need to switch models?       -> routing
Need to move old vectors?    -> migrate
Need to store vectors?       -> db
Need to retrieve results?    -> search
```

## 7. API sketch

```python
client.embed.create(...)
client.routing.resolve(...)
client.migrate.run(...)
client.db.upsert(...)
client.search.query(...)
```

이 다섯 개가 서로 겹치면 안 된다.
