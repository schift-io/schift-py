# Model Catalog Contract

> Status: Draft
> Date: 2026-03-13
> Scope: Schift curated model list for `embed` and `routing`

## 1. Purpose

Schift는 아무 provider 모델 문자열을 그대로 통과시키는 제품이 아니다.

전제는 이거다.

- Schift가 노출하는 모델 리스트가 있다
- `embed`는 그 리스트 안의 모델을 실행한다
- `routing`은 그 리스트 안에서 모델을 갈아끼운다

즉 model catalog가 먼저고, `routing`은 그 위에서 동작한다.

## 2. Big picture

```text
All provider models
  └─ Schift reviewed / supported models
       ├─ embed can execute these
       ├─ routing can switch between these
       └─ web shows these as selectable models
```

## 3. Catalog object

```json
{
  "model_id": "openai/text-embedding-3-large",
  "display_name": "OpenAI text-embedding-3-large",
  "provider": "openai",
  "provider_model_id": "text-embedding-3-large",
  "task_type": "embedding",
  "dimensions": [3072],
  "max_input_tokens": 8192,
  "supports_batch": true,
  "supports_query": true,
  "supports_document": true,
  "supports_migration_target": true,
  "supports_fallback": true,
  "supports_projection_compatibility": true,
  "pricing": {
    "provider_unit_cost_usd": 0.00013,
    "routing_fee_rate": 0.05
  },
  "status": "active",
  "aliases": [
    "openai-large",
    "oai-3-large"
  ],
  "tags": [
    "quality",
    "general"
  ]
}
```

## 4. Required fields

| Field | Required | Meaning |
|---|---|---|
| `model_id` | yes | Schift canonical model id |
| `display_name` | yes | user-facing label |
| `provider` | yes | provider key |
| `provider_model_id` | yes | provider native id |
| `task_type` | yes | currently `embedding` |
| `dimensions` | yes | supported output dimensions |
| `supports_batch` | yes | batch encode 가능 여부 |
| `supports_migration_target` | yes | migration target 허용 여부 |
| `supports_fallback` | yes | fallback chain에서 사용 가능 여부 |
| `pricing` | yes | provider 원가 + Schift fee basis |
| `status` | yes | `active`, `deprecated`, `disabled`, `beta` |

## 5. Canonical ID rules

형식:

```text
<provider>/<model>
```

예:

- `openai/text-embedding-3-small`
- `openai/text-embedding-3-large`
- `google/gemini-embedding-004`
- `voyage/voyage-3-large`
- `cohere/embed-v4`

원칙:

- SDK와 웹에는 canonical id를 기본으로 노출
- alias는 편의용 입력만 허용
- 저장/응답은 canonical id로 통일

## 6. Alias rules

alias는 짧은 입력을 허용하지만, 내부 저장은 canonical id로 정규화한다.

예:

```text
openai-large -> openai/text-embedding-3-large
gemini-latest -> google/gemini-embedding-004
voyage-large -> voyage/voyage-3-large
```

원칙:

- alias는 충돌 없어야 함
- alias는 stable하지 않을 수 있음
- 정책 저장 시 alias가 아니라 canonical id 사용

## 7. Catalog capabilities

catalog는 단순 리스트가 아니라, routing에 필요한 capability를 담아야 한다.

최소 capability:

- dimension
- batch 가능 여부
- query/document 적합 여부
- migration target 가능 여부
- fallback 가능 여부
- projection compatibility 여부
- 대략적인 cost bucket
- 대략적인 latency bucket

## 8. Suggested buckets

숫자 원본 외에 정책/웹용 bucket도 같이 둔다.

### Cost bucket

- `low`
- `medium`
- `high`

### Latency bucket

- `fast`
- `balanced`
- `slow`

### Quality bucket

- `economy`
- `balanced`
- `premium`

## 9. SDK surface

SDK에서 최소로 필요한 함수:

```python
client.embed.list_models()
client.embed.get_model("openai/text-embedding-3-large")
client.embed.resolve_alias("openai-large")
```

권장 응답:

- `list_models()` -> catalog items 목록
- `get_model(model_id)` -> 단일 catalog item
- `resolve_alias(alias)` -> canonical id

## 10. Relationship to routing

```text
Catalog defines what exists
Routing decides what to use
Embed executes the chosen model
```

정리:

- catalog 없이는 routing 정책도 없다
- routing은 catalog에 없는 모델을 고를 수 없다
- embed는 routing decision 또는 직접 지정된 catalog model을 실행한다

## 11. Relationship to migrate

`migrate`도 catalog와 연결된다.

- source model: catalog에 있거나 legacy external model reference
- target model: 가급적 catalog model
- projection compatibility 정보는 catalog metadata와 연결 가능

즉 migration도 결국 "어떤 모델 공간으로 옮길 것인가"를 catalog 기준으로 설명해야 한다.

## 12. Web requirements

웹에서 최소로 보여야 하는 것:

- model display name
- provider
- dimensions
- cost/latency/quality bucket
- active/beta/deprecated 상태
- fallback 가능 여부
- migration target 가능 여부

## 13. Initial curated list

초기 문서 기준 예시:

| model_id | provider | role |
|---|---|---|
| `openai/text-embedding-3-small` | openai | low-cost default |
| `openai/text-embedding-3-large` | openai | quality default |
| `google/gemini-embedding-004` | google | fallback / switch target |
| `voyage/voyage-3-large` | voyage | premium alternative |
| `cohere/embed-v4` | cohere | alternative |

이 표는 예시이며, 실제 운영 catalog는 별도 소스에서 관리한다.

## 14. Current decision

- public API는 catalog 기반으로 간다
- `routing`은 catalog 안에서만 switch한다
- canonical id를 기준 식별자로 쓴다
- alias는 입력 편의용일 뿐 저장 포맷이 아니다

## 15. Open questions

- catalog를 코드 상수로 둘지 API 응답으로만 둘지
- 가격 정보를 exact number와 bucket 둘 다 노출할지
- deprecated 모델을 기존 policy에서 자동 치환할지 경고만 줄지
