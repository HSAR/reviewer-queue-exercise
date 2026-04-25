from __future__ import annotations

import os
import time
from contextlib import contextmanager
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import psycopg
from fastapi import FastAPI, HTTPException, Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field


CURRENT_REVIEWER = "alex"
TERMINAL_STATUSES = {"approved", "rejected", "escalated"}
DB_CONNECT_RETRIES = 20
DB_RETRY_DELAY_SECONDS = 1
SEED_SQL_CANDIDATES = [
    Path(__file__).resolve().parents[1] / "db" / "init" / "002_seed.sql",
    Path(__file__).resolve().parents[2] / "db" / "init" / "002_seed.sql",
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


def database_url() -> str:
    return (
        "postgresql://"
        f"{os.getenv('POSTGRES_USER', 'reviewer')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'reviewer')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'reviewer_queue')}"
    )


def load_seed_sql() -> str:
    seed_path = next((path for path in SEED_SQL_CANDIDATES if path.exists()), None)
    if seed_path is None:
        raise RuntimeError("Could not find backend/db/init/002_seed.sql")
    return seed_path.read_text()


@contextmanager
def db_connection():
    connection = psycopg.connect(database_url(), row_factory=dict_row)
    try:
        yield connection
    finally:
        connection.close()


def wait_for_database() -> None:
    last_error: Exception | None = None
    for _ in range(DB_CONNECT_RETRIES):
        try:
            with db_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
            return
        except Exception as error:  # pragma: no cover - startup retry path
            last_error = error
            time.sleep(DB_RETRY_DELAY_SECONDS)
    raise RuntimeError("Database was not ready in time") from last_error


def reset_database() -> None:
    with db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE review_items RESTART IDENTITY")
            cursor.execute(load_seed_sql())
        connection.commit()


def allowed_actions(item: ReviewItem) -> list[ReviewAction]:
    if item.status == "unassigned":
        return [ReviewAction.claim]
    if item.status == "in_review":
        return [ReviewAction.approve, ReviewAction.reject, ReviewAction.escalate]
    return []


def decorate_item(item: ReviewItem, rank: int = 0) -> ItemWithActions:
    return ItemWithActions(
        **item.model_dump(),
        allowed_actions=allowed_actions(item),
        urgency_rank=rank,
    )


def item_from_row(row: dict) -> ReviewItem:
    return ReviewItem(
        id=row["item_id"],
        title=row["title"],
        submitted_at=row["submitted_at"],
        risk_level=row["risk_level"],
        customer_tier=row["customer_tier"],
        status=row["status"],
        assigned_reviewer=row["assigned_reviewer"],
        notes_count=row["notes_count"],
        summary=row["summary"],
    )


def fetch_items(where_clause: str = "", params: tuple = ()) -> list[ReviewItem]:
    query = f"""
        SELECT
            item_id,
            title,
            submitted_at,
            risk_level,
            customer_tier,
            status,
            assigned_reviewer,
            notes_count,
            summary
        FROM review_items
        {where_clause}
        ORDER BY
            CASE risk_level
                WHEN 'high' THEN 0
                WHEN 'medium' THEN 1
                ELSE 2
            END,
            CASE customer_tier
                WHEN 'priority' THEN 0
                ELSE 1
            END,
            submitted_at ASC
    """
    with db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
    return [item_from_row(row) for row in rows]


def fetch_item(item_id: str) -> ReviewItem | None:
    with db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    item_id,
                    title,
                    submitted_at,
                    risk_level,
                    customer_tier,
                    status,
                    assigned_reviewer,
                    notes_count,
                    summary
                FROM review_items
                WHERE item_id = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (item_id,),
            )
            row = cursor.fetchone()
    if row is None:
        return None
    return item_from_row(row)


def active_items() -> list[ReviewItem]:
    return fetch_items("WHERE status NOT IN ('approved', 'rejected', 'escalated')")


def active_count() -> int:
    with db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM review_items
                WHERE status NOT IN ('approved', 'rejected')
                """
            )
            row = cursor.fetchone()
    return row["count"]


def terminal_count() -> int:
    with db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM review_items
                WHERE status IN ('approved', 'rejected', 'escalated')
                """
            )
            row = cursor.fetchone()
    return row["count"]


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


@app.on_event("startup")
def startup() -> None:
    wait_for_database()


@app.get("/health")
def health() -> dict[str, str]:
    with db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/api/items", response_model=QueueResponse)
def get_queue() -> QueueResponse:
    try:
        active = active_items()
        decorated = [decorate_item(item, index + 1) for index, item in enumerate(active)]
        return QueueResponse(
            current_reviewer=CURRENT_REVIEWER,
            items=decorated,
            active_count=active_count(),
            terminal_count=terminal_count(),
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/items/{item_id}", response_model=ItemWithActions)
def get_item(
    item_id: Annotated[str, PathParam(description="Review item id, for example RV-1024")],
) -> ItemWithActions:
    try:
        item = fetch_item(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Item {item_id} was not found")

        ranks = {queued_item.id: index + 1 for index, queued_item in enumerate(active_items())}
        return decorate_item(item, ranks.get(item.id, 0))
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.post("/api/items/{item_id}/actions", response_model=ActionResponse)
def apply_action(
    item_id: Annotated[str, PathParam(description="Review item id, for example RV-1024")],
    request: ActionRequest,
) -> ActionResponse:
    try:
        with db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, item_id, status, assigned_reviewer
                    FROM review_items
                    WHERE item_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (item_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise HTTPException(status_code=404, detail=f"Item {item_id} was not found")

                if row["status"] in TERMINAL_STATUSES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"{item_id} is already {row['status']} and cannot be changed",
                    )

                if request.action == ReviewAction.claim:
                    if row["status"] != "unassigned":
                        raise HTTPException(
                            status_code=400,
                            detail=f"Only unassigned items can be claimed; {item_id} is {row['status']}",
                        )
                    cursor.execute(
                        """
                        UPDATE review_items
                        SET status = 'in_review', assigned_reviewer = %s
                        WHERE id = %s
                        """,
                        (request.reviewer, row["id"]),
                    )
                    message = f"{item_id} claimed by {request.reviewer}"
                else:
                    if row["status"] != "in_review":
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"Only in-review items can be {ACTION_PAST_TENSE[request.action]}; "
                                f"{item_id} is {row['status']}"
                            ),
                        )
                    cursor.execute(
                        """
                        UPDATE review_items
                        SET status = %s
                        WHERE id = %s
                        """,
                        (ACTION_PAST_TENSE[request.action], row["id"]),
                    )
                    message = f"{item_id} marked {ACTION_PAST_TENSE[request.action]}"
            connection.commit()

        item = fetch_item(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail=f"Item {item_id} was not found")

        ranks = {queued_item.id: index + 1 for index, queued_item in enumerate(active_items())}
        return ActionResponse(item=decorate_item(item, ranks.get(item.id, 0)), message=message)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
