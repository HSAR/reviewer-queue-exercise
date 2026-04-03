# Seed Preview

The seed data in [`../data/review_items.json`](../data/review_items.json) contains a small queue of review items.

## Field notes

- `risk_level`: one of `low`, `medium`, `high`
- `customer_tier`: one of `standard`, `priority`
- `status`: one of `unassigned`, `in_review`, `approved`, `rejected`, `escalated`
- `assigned_reviewer`: `null` for unassigned work, otherwise the reviewer currently handling it
- `notes_count`: a small hint about how much history/context already exists on the item

## Example records

```json
{
  "id": "RV-1024",
  "title": "Wire transfer limit increase",
  "submitted_at": "2026-04-02T08:15:00Z",
  "risk_level": "high",
  "customer_tier": "priority",
  "status": "unassigned",
  "assigned_reviewer": null,
  "notes_count": 2,
  "summary": "Customer requested a same-day increase to a large outgoing transfer limit."
}
```

```json
{
  "id": "RV-1027",
  "title": "Business account name correction",
  "submitted_at": "2026-04-02T10:45:00Z",
  "risk_level": "low",
  "customer_tier": "standard",
  "status": "in_review",
  "assigned_reviewer": "sam",
  "notes_count": 1,
  "summary": "Submitted legal documents to correct the registered business name."
}
```

```json
{
  "id": "RV-1032",
  "title": "Repeated payout destination change",
  "submitted_at": "2026-04-01T17:20:00Z",
  "risk_level": "high",
  "customer_tier": "standard",
  "status": "unassigned",
  "assigned_reviewer": null,
  "notes_count": 4,
  "summary": "Third payout destination change requested in two days for the same merchant account."
}
```

## Reviewer intent

The data is meant to feel concrete enough that good product choices matter:

- some items are clearly urgent
- some are already in progress
- some should be excluded from the active queue because they are terminal
- assignment and status should influence what actions are available
