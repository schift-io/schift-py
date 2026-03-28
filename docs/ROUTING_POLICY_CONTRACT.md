# Routing Policy Contract

> Status: Draft
> Date: 2026-03-13
> Scope: Python SDK, Web control plane, Server routing engine

## 1. Purpose

이 문서는 OpenRouter식 embedding routing을 Schift에서 어떻게 계약화할지 정의한다.

목표:

- SDK, 웹, 서버가 같은 routing object를 본다
- 단순 `model="auto"`가 아니라 정책 객체 중심으로 라우팅한다
- 우리 모델 리스트 안에서 어떤 모델을 기본/대체 모델로 쓸지 고정한다
- failover, 비용, latency, provider 제약을 설명 가능한 방식으로 관리한다

## 2. Core concepts

### Model registry

Schift는 provider-native 모델명을 그대로 쓰되, registry에서 capability와 가격 정보를 정규화한다.

예:

- `openai/text-embedding-3-small`
- `openai/text-embedding-3-large`
- `google/gemini-embedding-004`
- `voyage/voyage-3-large`
- `cohere/embed-v4`

### Routing policy

정책은 "우리 모델 리스트 안에서 어떤 모델을 기본으로 쓰고, 언제 어떤 모델로 갈아끼울지"를 정의한다.

### Routing decision

결정은 특정 요청 시점에 실제로 어떤 model/provider가 선택됐는지와 그 이유를 담는다.

### Fallback chain

primary route가 실패하면 projection compatibility를 고려해 대체 route로 넘긴다.

## 2-1. Model catalog first

Schift routing의 전제는 외부 provider 전체를 직접 다루는 것이 아니라, 먼저 Schift가 승인/노출한 모델 리스트가 있다는 점이다.

```text
All provider models
  └─ Schift curated model catalog
       └─ routing policy picks from here
```

즉 routing은 "아무 모델이나 자유 입력"보다 "우리 catalog 안에서 모델을 갈아끼우는 것"이 본질이다.

## 3. Policy object

최소 스키마:

```json
{
  "policy_id": "rtp_123",
  "name": "prod-default",
  "status": "active",
  "default_model": "openai/text-embedding-3-large",
  "strategy": "balanced",
  "fallbacks": [
    "google/gemini-embedding-004",
    "voyage/voyage-3-large"
  ],
  "constraints": {
    "allowed_providers": ["openai", "google", "voyage"],
    "blocked_providers": [],
    "max_unit_cost_usd": 0.00015,
    "latency_budget_ms": 1200,
    "min_dimensions": 1536,
    "region": "global"
  },
  "applies_to": {
    "account_scope": "default",
    "app_id": null,
    "index_id": null,
    "environment": "prod"
  },
  "created_at": "2026-03-13T10:00:00Z",
  "updated_at": "2026-03-13T10:00:00Z"
}
```

## 4. Required fields

| Field | Required | Meaning |
|---|---|---|
| `policy_id` | yes | immutable id |
| `name` | yes | user-facing policy name |
| `status` | yes | `active`, `disabled`, `draft` |
| `default_model` | yes | first-choice model |
| `strategy` | yes | selection objective |
| `fallbacks` | yes | ordered fallback models |
| `constraints` | yes | hard limits |
| `applies_to` | yes | scope binding |

## 5. Strategy enum

허용값:

- `quality`
- `cost`
- `latency`
- `balanced`
- `pinned`

의미:

- `quality`: 최고 품질 우선
- `cost`: 단가 최소화 우선
- `latency`: 응답 시간 최소화 우선
- `balanced`: 기본 전략. 품질/비용/latency를 종합
- `pinned`: `default_model` 고정. 장애 시에만 fallback

## 6. Constraints object

```json
{
  "allowed_providers": ["openai", "google"],
  "blocked_providers": [],
  "max_unit_cost_usd": 0.00015,
  "latency_budget_ms": 1200,
  "min_dimensions": 1536,
  "max_dimensions": 3072,
  "region": "global",
  "require_projection_compatible": true
}
```

필드 설명:

- `allowed_providers`: 이 목록 안에서만 선택
- `blocked_providers`: 이 목록은 항상 제외
- `max_unit_cost_usd`: 이 값보다 비싼 route 제외
- `latency_budget_ms`: 예산 초과 route 제외
- `min_dimensions` / `max_dimensions`: 결과 차원 제한
- `region`: 향후 리전/데이터 거버넌스 제약용
- `require_projection_compatible`: failover 시 projection 가능한 route만 허용

## 7. Scope binding

정책 스코프는 아래 우선순위로 적용한다.

1. `index_id`
2. `app_id`
3. `account_scope=default`

이렇게 두는 이유:

- 고객은 전역 정책 하나로 시작할 수 있다
- 나중에 앱별/인덱스별 정책으로 세밀하게 갈 수 있다

## 8. SDK surface

정책 API:

```python
policy = client.routing.create_policy(
    name="prod-default",
    default_model="openai/text-embedding-3-large",
    strategy="balanced",
    fallbacks=["google/gemini-embedding-004"],
    constraints={
        "max_unit_cost_usd": 0.00015,
        "latency_budget_ms": 1200,
    },
)

client.routing.list_policies()
client.routing.get_policy("prod-default")
client.routing.update_policy("prod-default", strategy="latency")
client.routing.resolve(policy="prod-default", input_type="query")
client.routing.preview(policy="prod-default", text="quarterly revenue report")
```

## 9. Resolve response

```json
{
  "policy": "prod-default",
  "selected_model": "openai/text-embedding-3-large",
  "selected_provider": "openai",
  "strategy": "balanced",
  "reason": "best_quality_within_latency_budget",
  "fallback_used": false,
  "candidate_count": 3,
  "evaluated_candidates": [
    {
      "model": "openai/text-embedding-3-large",
      "provider": "openai",
      "eligible": true,
      "estimated_unit_cost_usd": 0.00013,
      "estimated_latency_ms": 820
    }
  ]
}
```

## 10. Preview response

`preview()`는 실제 과금/전송 없이 decision을 보여준다.

용도:

- deploy 전 정책 확인
- failover 체인 검증
- 왜 특정 route가 선택되는지 설명

```json
{
  "dry_run": true,
  "decision": {
    "selected_model": "google/gemini-embedding-004",
    "selected_provider": "google",
    "reason": "fallback_due_to_provider_health"
  },
  "notes": [
    "default_model excluded by provider health status",
    "fallback #1 selected"
  ]
}
```

## 11. Web requirements

웹에서 최소한 보여야 하는 항목:

- policy 목록
- default model
- fallback chain
- strategy
- provider constraints
- estimated cost/latency
- 최근 failover 발생 여부

## 12. Open questions

- `policy` 식별을 name 우선으로 허용할지 id만 허용할지
- `strategy=balanced`의 가중치를 계정 공통으로 둘지 정책별로 둘지
- projection compatibility를 decision 응답에 얼마나 자세히 노출할지
