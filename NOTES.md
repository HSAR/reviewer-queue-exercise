# Notes

## Assumptions

- The current reviewer is hardcoded as `alex`.
- Seed data is loaded from `data/review_items.json` into process memory at API startup.
- There is no persistence layer. Any changes are lost when the API restarts or the container is rebuilt.
- The browser refreshes queue data after each workflow action instead of maintaining a separate client-side source of truth.
- Any item in `in_review` can be approved, rejected, or escalated, regardless of assigned reviewer. I did not add ownership enforcement because it was outside the core rules.

## Workflow Model

The backend owns the workflow rules in `backend/app/main.py`.

- `unassigned` items allow only `claim`.
- `claim` changes status to `in_review` and records `assigned_reviewer`.
- `in_review` items allow `approve`, `reject`, and `escalate`.
- `approved`, `rejected`, and `escalated` are terminal states.
- Terminal items return no allowed actions and are excluded from the active queue.
- Invalid transitions return `400` responses with a clear error message.

The API also decorates each item with:

- `allowed_actions`, so the UI can render only valid controls.
- `urgency_rank`, so the UI can explain queue ordering without duplicating the sort rule.

## Queue Ordering

The queue is sorted server-side using the requested urgency rules:

1. `risk_level`: `high`, then `medium`, then `low`
2. `customer_tier`: `priority`, then `standard`
3. `submitted_at`: older items first

Keeping this in the API avoids having the frontend and backend disagree about what a reviewer should work on next.

## UI Choices

The frontend is intentionally one screen:

- Left side: active queue ordered by urgency.
- Right side: selected item details and workflow actions.
- Top summary: current reviewer, active count, and closed count.
- Feedback banner after successful actions.
- Error banner for rejected actions or API failures.
- Loading state while the queue is fetched.

The UI does not show terminal records in the queue because the primary reviewer task is active work. After an item is approved, rejected, or escalated, it disappears from the active queue and the next item is selected.

## Testing

Backend tests cover the core business behavior:

- Active queue excludes terminal items.
- Active queue uses the expected urgency order.
- Items expose the correct allowed actions.
- Claiming records the reviewer and moves the item to `in_review`.
- Approve, reject, and escalate move `in_review` items to terminal states.
- Terminal items are removed from the active queue.
- Invalid transitions are rejected cleanly.
- Unknown item IDs return `404`.

Run them with:

```sh
docker compose run --rm api pytest
```

## Tradeoffs

- I chose a tiny API rather than placing workflow logic in Vue so rules are enforced in one place.
- I kept the backend as a single file because the domain surface is small and splitting repository/service layers would add ceremony.
- I used Docker development servers for simple local startup instead of production builds.
- I skipped authentication, durable storage, audit logs, pagination, and true multi-user conflict handling.

## Improvements With More Time

- Add SQLite or Postgres plus an action history table.
- Add reviewer ownership checks if reviewers should only close their own work.
- Add filters for unassigned work, my work, and risk level.
- Add frontend component tests around action visibility and error handling.
- Add a small terminal/history view for recently completed decisions.
