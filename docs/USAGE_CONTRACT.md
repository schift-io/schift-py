# Usage Contract

> Status: Draft
> Date: 2026-03-13

## 1. Responsibility

`client.usage()`는 고객이 보는 aggregate usage를 반환한다.

`client.usage_limits()`는 현재 플랜/쿼터 상태를 반환한다.

## 2. Public API

```python
usage = client.usage(window="7d", group_by="provider")
limits = client.usage_limits()
```

## 3. usage request

허용 필드:

- `window`: `24h`, `7d`, `30d`
- `group_by`: `provider`, `model`, `policy`, `feature`

## 4. usage response

```json
{
  "window": "7d",
  "group_by": "provider",
  "totals": {
    "embedding_requests": 12034,
    "search_requests": 8832,
    "migration_runs": 4,
    "estimated_spend_usd": 42.18,
    "avg_latency_ms": 812,
    "failover_count": 27
  },
  "breakdown": [
    {
      "key": "openai",
      "requests": 8450,
      "estimated_spend_usd": 31.00
    },
    {
      "key": "google",
      "requests": 3584,
      "estimated_spend_usd": 11.18
    }
  ]
}
```

## 5. usage_limits response

```json
{
  "plan": "pro",
  "quota": {
    "embedding_requests": 500000,
    "search_requests": 2000000,
    "migration_runs": 100
  },
  "consumed": {
    "embedding_requests": 12034,
    "search_requests": 8832,
    "migration_runs": 4
  },
  "remaining": {
    "embedding_requests": 487966,
    "search_requests": 1991168,
    "migration_runs": 96
  },
  "reset_at": "2026-04-01T00:00:00Z"
}
```

## 6. What usage does not do

- raw request event export
- internal billing ledger export
- cross-account operator view

## 7. Current decision

- `usage`는 aggregate only
- `usage_limits`는 quota/remaining only
