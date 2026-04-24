# Notes

## Assumptions

- The current reviewer is hardcoded as `alex`.
- Seed data is loaded into memory at startup and reset when the API container restarts.
- The active queue excludes terminal statuses: `approved`, `rejected`, and `escalated`.
- Any `in_review` item can be approved, rejected, or escalated. I did not add an ownership restriction beyond the required workflow rules.

## Tradeoffs

- I used a small FastAPI API rather than putting workflow logic in the browser, so invalid transitions are rejected in one place.
- The UI refreshes the queue after each action instead of doing optimistic updates. This is simpler and keeps the active queue ordering correct after terminal actions.
- Docker uses development servers for both services to keep the take-home easy to run and inspect.
- There is no persistent database, authentication, or multi-user conflict handling.

## Improve Next

- Add a lightweight persistence layer, such as SQLite, and audit records for decisions.
- Add reviewer ownership rules if the product should prevent reviewers from closing another person's work.
- Add filtering for "mine" versus "unassigned" items once the queue grows.
- Expand tests around every invalid transition and the UI action states.
