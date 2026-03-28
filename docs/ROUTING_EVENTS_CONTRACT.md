# Routing Usage And Failover Event Contract

> Status: Draft
> Date: 2026-03-13
> Scope: SDK observability, Web dashboard, billing and analytics

## 1. Purpose

라우팅은 실제 호출만 있으면 끝나는 기능이 아니다.
Schift BM상 routing fee를 정당화하려면 아래가 보여야 한다.

- 어느 provider/model이 실제로 선택됐는지
- 왜 fallback이 발생했는지
- cost와 latency가 어떻게 나왔는지
- usage/billing이 어떤 route 기준으로 집계되는지

이 문서는 그 이벤트 계약을 정의한다.

## 2. Event families

필수 이벤트 종류:

- `routing.decision`
- `routing.failover`
- `routing.completed`
- `routing.error`

집계용 usage 레코드:

- `usage.embedding`
- `usage.routing_fee`

## 3. routing.decision

요청 직후 route가 정해졌을 때 남긴다.

```json
{
  "event_id": "evt_001",
  "type": "routing.decision",
  "timestamp": "2026-03-13T10:00:00Z",
  "account_id": "acct_123",
  "request_id": "req_123",
  "policy_id": "rtp_123",
  "input_type": "query",
  "selected_model": "openai/text-embedding-3-large",
  "selected_provider": "openai",
  "strategy": "balanced",
  "reason": "best_quality_within_latency_budget",
  "fallback_used": false,
  "estimated_unit_cost_usd": 0.00013,
  "estimated_latency_ms": 820
}
```

## 4. routing.failover

primary가 실패해 fallback으로 넘어간 경우 남긴다.

```json
{
  "event_id": "evt_002",
  "type": "routing.failover",
  "timestamp": "2026-03-13T10:00:01Z",
  "account_id": "acct_123",
  "request_id": "req_123",
  "policy_id": "rtp_123",
  "failed_model": "openai/text-embedding-3-large",
  "failed_provider": "openai",
  "failure_reason": "http_503",
  "fallback_model": "google/gemini-embedding-004",
  "fallback_provider": "google",
  "fallback_index": 1,
  "projection_compatible": true
}
```

`failure_reason` enum 초안:

- `http_408`
- `http_429`
- `http_500`
- `http_502`
- `http_503`
- `http_504`
- `timeout`
- `rate_limited`
- `provider_unhealthy`
- `policy_excluded`

## 5. routing.completed

호출이 성공적으로 끝났을 때 남긴다.

```json
{
  "event_id": "evt_003",
  "type": "routing.completed",
  "timestamp": "2026-03-13T10:00:02Z",
  "account_id": "acct_123",
  "request_id": "req_123",
  "policy_id": "rtp_123",
  "selected_model": "google/gemini-embedding-004",
  "selected_provider": "google",
  "fallback_used": true,
  "input_count": 3,
  "output_dimensions": 3072,
  "latency_ms": 914,
  "provider_cost_usd": 0.00011,
  "routing_fee_usd": 0.0000055,
  "total_cost_usd": 0.0001155,
  "cache_hit": false
}
```

## 6. routing.error

최종적으로 실패했을 때 남긴다.

```json
{
  "event_id": "evt_004",
  "type": "routing.error",
  "timestamp": "2026-03-13T10:00:02Z",
  "account_id": "acct_123",
  "request_id": "req_456",
  "policy_id": "rtp_123",
  "attempted_models": [
    "openai/text-embedding-3-large",
    "google/gemini-embedding-004"
  ],
  "error_code": "all_routes_failed",
  "message": "All eligible routes failed within policy constraints"
}
```

## 7. Usage records

이벤트와 별도로 청구/대시보드용 usage row를 남긴다.

### usage.embedding

```json
{
  "usage_id": "use_001",
  "type": "usage.embedding",
  "timestamp": "2026-03-13T10:00:02Z",
  "account_id": "acct_123",
  "request_id": "req_123",
  "provider": "google",
  "model": "google/gemini-embedding-004",
  "input_count": 3,
  "dimensions": 3072,
  "provider_cost_usd": 0.00011
}
```

### usage.routing_fee

```json
{
  "usage_id": "use_002",
  "type": "usage.routing_fee",
  "timestamp": "2026-03-13T10:00:02Z",
  "account_id": "acct_123",
  "request_id": "req_123",
  "provider": "google",
  "model": "google/gemini-embedding-004",
  "routing_fee_rate": 0.05,
  "routing_fee_usd": 0.0000055
}
```

## 8. SDK surface

SDK에서 필요한 조회 함수:

- `client.routing.events(window="24h", policy=None, type=None)`
- `client.routing.health()`
- `client.usage(window="24h", group_by="model")`

예시:

```python
events = client.routing.events(window="24h", policy="prod-default")
health = client.routing.health()
usage = client.usage(window="7d", group_by="provider")
```

## 9. Web requirements

웹에서 최소로 보여야 하는 지표:

- provider별 호출 비중
- model별 비용
- failover 횟수
- fallback 성공률
- 평균 latency
- 최근 오류 이벤트

운영용 테이블 최소 컬럼:

- timestamp
- policy
- selected provider/model
- fallback used
- latency
- provider cost
- routing fee
- final status

## 10. Relationship to pricing

이 계약은 landing의 문구와 직접 연결된다.

- provider cost + 5%
- failover는 추가 과금 없음
- route decision이 설명 가능해야 함

그래서 usage와 failover 이벤트는 단순 로그가 아니라 제품/청구 계약의 일부다.

## 11. Retention guidance

기본 retention 초안:

- raw routing events: 30일
- usage aggregates: 13개월
- enterprise tier: 보존 기간 설정 가능

## 12. Open questions

- `routing.completed`와 `usage.*`를 별도 테이블로 둘지 하나의 fact row로 합칠지
- failover 시 projection compatibility score를 이벤트에 포함할지
- free tier에서 이벤트 조회 기간을 제한할지
