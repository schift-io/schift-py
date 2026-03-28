# Routing Decision Schema

> Status: Draft
> Date: 2026-03-13

## 1. resolve response

```json
{
  "policy": "prod-default",
  "selected_model": "openai/text-embedding-3-large",
  "selected_provider": "openai",
  "reason": "best_quality_within_latency_budget",
  "fallback_used": false,
  "candidate_count": 3
}
```

## 2. preview response

```json
{
  "dry_run": true,
  "decision": {
    "selected_model": "google/gemini-embedding-004",
    "selected_provider": "google",
    "reason": "fallback_due_to_provider_health",
    "fallback_used": true
  },
  "notes": [
    "default_model excluded by provider health status",
    "fallback #1 selected"
  ]
}
```

## 3. Notes

- `resolve()`는 실제 decision
- `preview()`는 dry-run decision
- detailed event trail은 routing events contract 참조
