# Reviewer Queue Take-Home

## Implementation Quick Start

This scaffold uses FastAPI for the workflow API and Vue/Vite for the reviewer workspace.

Run the app with Docker:

```sh
docker compose up --build
```

Then open:

- UI: http://localhost:5173
- API health: http://localhost:8000/health

Run backend tests through Docker:

```sh
docker compose run --rm api pytest
```

This repository contains a small fullstack take-home exercise for a **mid-level engineer**.

The goal is to assess how you turn a concrete workflow into a simple, usable product slice:

- shape a small backend or service layer
- build a minimal UI
- implement business rules correctly
- make pragmatic product and engineering tradeoffs under time pressure

## Timebox

A strong candidate should be able to complete a solid version of this exercise in **about 60 minutes**.

Please stop after **90 minutes**.

If you run out of time, prioritize:

1. one clear working flow
2. correct business rules
3. a usable interface

## Technology choice

Use **any language, framework, and project structure** you prefer.

This repo intentionally does **not** include a frontend or backend scaffold. We want to see how you choose to structure a small solution, not how well you can fit into a prebuilt stack.

## Scenario

You are building a small internal tool for an operations team.

The team reviews incoming submissions and decides what to do next. Reviewers need to:

- see which items need attention
- inspect item details
- claim work
- move items through the review workflow

The tool should help a reviewer answer:

- what should I work on next?
- what information do I need to make a decision?
- what actions are allowed on this item right now?

## What to build

Build a small reviewer workspace using the seed data in [`data/review_items.json`](data/review_items.json).

It should include:

- an **active queue** of items that still need work
- a way to **inspect an item's details**
- controls to perform workflow actions
- UI feedback after actions are taken

You may implement this as:

- one page with a list and detail panel, or
- two simple views/screens

Either is fine.

## Seed data

The seed data is a list of review items with fields such as:

- `id`
- `title`
- `submitted_at`
- `risk_level`
- `customer_tier`
- `status`
- `assigned_reviewer`
- `notes_count`
- `summary`

You may load the seed data however you like:

- in memory
- from a file
- via SQLite or Postgres
- through a lightweight backend API

Persistence beyond the running app is **not required**.

## Required workflow rules

Your solution must support these actions:

- `claim`
- `approve`
- `reject`
- `escalate`

Use these workflow rules:

- only items with status `unassigned` can be claimed
- claiming an item moves it to `in_review`
- claiming an item must record the acting reviewer
- only items with status `in_review` can be approved, rejected, or escalated
- `approved`, `rejected`, and `escalated` are terminal states
- terminal items must not allow further actions
- invalid actions should be rejected cleanly

For simplicity, you may hardcode the current reviewer identity, for example:

- `alex`

## Queue behavior

The active queue must exclude terminal items:

- `approved`
- `rejected`
- `escalated`

The queue must be ordered by urgency using this rule:

1. higher `risk_level` outranks lower (`high > medium > low`)
2. within the same risk level, `priority` customers outrank `standard`
3. within the same bucket, older items outrank newer items

You may present urgency however you think is clearest.

## UI expectations

We are not looking for polished visual design. We are looking for clear product choices.

Please include:

- loading state
- basic error handling
- obvious workflow actions
- enough item detail to justify the reviewer decision
- a clear indication of item status and assignment

The UI can be simple.

## Flexibility

Reasonable shortcuts are encouraged.

You do **not** need:

- authentication
- deployment
- containerization
- background jobs
- real multi-user support
- complex styling

You **may**:

- use in-memory state
- refresh data after each action instead of doing optimistic UI
- implement a tiny local API or skip the network layer entirely if your structure makes sense

## What we are looking for

We are evaluating:

- correct business-rule implementation
- sensible queue and workflow behavior
- a usable and understandable UI
- pragmatic scoping
- code clarity
- your explanation of tradeoffs and decisions

We are **not** looking for:

- production infrastructure
- a large codebase
- framework-specific patterns
- pixel-perfect design

## What to submit

Please send us:

1. a link to a GitHub repo with your implementation
2. a short `NOTES.md` covering:
   - assumptions you made
   - tradeoffs you chose
   - what you would improve next with more time
3. a short recorded walkthrough (eg Loom or similar), ideally **~3 minutes**, explaining:
   - how you modeled the workflow
   - how you enforced the business rules
   - how you decided what the reviewer should see and do

## Helpful reference files

- [`data/review_items.json`](data/review_items.json) - seed data
- [`examples/seed_preview.md`](examples/seed_preview.md) - sample records and field notes

## Notes on AI use

It is fine to use AI tools while completing this exercise.

We will review not just the code, but also:

- whether the implemented workflow makes sense
- whether the business rules are correctly enforced
- whether the UI reflects real product judgment
- whether you can clearly explain your decisions in a future interview
