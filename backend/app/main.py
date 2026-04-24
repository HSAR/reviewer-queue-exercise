from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field


CURRENT_REVIEWER = "alex"
TERMINAL_STATUSES = {"approved", "rejected", "escalated"}
RISK_ORDER = {"high": 0, "medium": 1, "low": 2}
TIER_ORDER = {"priority": 0, "standard": 1}
DATA_FILE_CANDIDATES = [
    Path(__file__).resolve().parents[1] / "data" / "review_items.json",
    Path(__file__).resolve().parents[2] / "data" / "review_items.json",
]


class ReviewAction(StrEnum):
    claim = "claim"
    approve = "approve"
    reject = "reject"
    escalate = "escalate"


ACTION_PAST_TENSE = {
    ReviewAction.approve: "approved",
    ReviewAction.reject: "rejected",
    ReviewAction.escalate: "escalated",
}


class ReviewItem(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: str
    title: str
    submitted_at: datetime
    risk_level: str
    customer_tier: str
    status: str
    assigned_reviewer: str | None
    notes_count: int
    summary: str


class ItemWithActions(ReviewItem):
    allowed_actions: list[ReviewAction]
    urgency_rank: int


class QueueResponse(BaseModel):
    current_reviewer: str
    items: list[ItemWithActions]
    active_count: int
    terminal_count: int


class ActionRequest(BaseModel):
    action: ReviewAction
    reviewer: str = Field(default=CURRENT_REVIEWER, min_length=1)


class ActionResponse(BaseModel):
    item: ItemWithActions
    message: str


def load_items() -> dict[str, ReviewItem]:
    data_file = next((path for path in DATA_FILE_CANDIDATES if path.exists()), None)
    if data_file is None:
        raise RuntimeError("Could not find data/review_items.json")

    with data_file.open() as seed_file:
        raw_items = json.load(seed_file)
    return {item["id"]: ReviewItem(**item) for item in raw_items}


items_by_id = load_items()

app = FastAPI(title="Reviewer Queue API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def allowed_actions(item: ReviewItem) -> list[ReviewAction]:
    if item.status == "unassigned":
        return [ReviewAction.claim]
    if item.status == "in_review":
        return [ReviewAction.approve, ReviewAction.reject, ReviewAction.escalate]
    return []


def urgency_key(item: ReviewItem) -> tuple[int, int, datetime]:
    return (
        RISK_ORDER.get(item.risk_level, len(RISK_ORDER)),
        TIER_ORDER.get(item.customer_tier, len(TIER_ORDER)),
        item.submitted_at,
    )


def decorate_item(item: ReviewItem, rank: int = 0) -> ItemWithActions:
    return ItemWithActions(
        **item.model_dump(),
        allowed_actions=allowed_actions(item),
        urgency_rank=rank,
    )


def active_items() -> list[ReviewItem]:
    return sorted(
        (item for item in items_by_id.values() if item.status not in TERMINAL_STATUSES),
        key=urgency_key,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/items", response_model=QueueResponse)
def get_queue() -> QueueResponse:
    active = active_items()
    decorated = [decorate_item(item, index + 1) for index, item in enumerate(active)]
    return QueueResponse(
        current_reviewer=CURRENT_REVIEWER,
        items=decorated,
        active_count=len(active),
        terminal_count=len(items_by_id) - len(active),
    )


@app.get("/api/items/{item_id}", response_model=ItemWithActions)
def get_item(
    item_id: Annotated[str, PathParam(description="Review item id, for example RV-1024")],
) -> ItemWithActions:
    item = items_by_id.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Item {item_id} was not found")

    ranks = {item.id: index + 1 for index, item in enumerate(active_items())}
    return decorate_item(item, ranks.get(item.id, 0))


@app.post("/api/items/{item_id}/actions", response_model=ActionResponse)
def apply_action(
    item_id: Annotated[str, PathParam(description="Review item id, for example RV-1024")],
    request: ActionRequest,
) -> ActionResponse:
    item = items_by_id.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Item {item_id} was not found")

    if item.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"{item.id} is already {item.status} and cannot be changed",
        )

    if request.action == ReviewAction.claim:
        if item.status != "unassigned":
            raise HTTPException(
                status_code=400,
                detail=f"Only unassigned items can be claimed; {item.id} is {item.status}",
            )
        item.status = "in_review"
        item.assigned_reviewer = request.reviewer
        message = f"{item.id} claimed by {request.reviewer}"
    else:
        if item.status != "in_review":
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Only in-review items can be {ACTION_PAST_TENSE[request.action]}; "
                    f"{item.id} is {item.status}"
                ),
            )
        item.status = ACTION_PAST_TENSE[request.action]
        message = f"{item.id} marked {item.status}"

    ranks = {item.id: index + 1 for index, item in enumerate(active_items())}
    return ActionResponse(item=decorate_item(item, ranks.get(item.id, 0)), message=message)
