# Reviewer Queue

A small reviewer workspace for an operations team. It separates unclaimed tickets from tickets claimed by the current reviewer, lets a reviewer inspect item details, and applies simple workflow actions against an in-memory FastAPI service.

## Stack

- FastAPI backend
- Vue 3 + Vite frontend
- Docker Compose for local development
- Pytest for backend workflow tests

## Run Locally

```sh
docker compose up --build
```

Then open:

- App: http://localhost:5173
- API health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs

## Run Tests

```sh
docker compose run --rm api pytest
```

## Project Layout

```text
backend/
  app/main.py          FastAPI app, in-memory data store, workflow rules
  tests/              Backend workflow tests
frontend/
  src/App.vue          Single-page reviewer workspace
  src/styles.css       UI styling
data/
  review_items.json    Seed review items loaded by the API
NOTES.md               Assumptions, tradeoffs, and implementation details
```

## Behavior

The app loads seed data into memory when the API starts. The unclaimed and claimed-by-me queues are both ordered by urgency: high risk first, then priority customers, then older submissions.

The current reviewer is hardcoded as `alex`. Claiming an unassigned item moves it into review, assigns it to that reviewer, and moves it from the unclaimed view into the claimed-by-me view. Items in review can be approved, rejected, or escalated. Terminal items leave the active queues and cannot be changed again.

Data is not persisted. Restarting the API resets the queue back to the seed file.
