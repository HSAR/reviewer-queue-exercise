import pytest
from fastapi.testclient import TestClient

from app.main import app, items_by_id, load_items


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_items():
    items_by_id.clear()
    items_by_id.update(load_items())


def test_unclaimed_queue_excludes_claimed_and_terminal_items_and_orders_by_urgency():
    response = client.get("/api/items")

    assert response.status_code == 200
    payload = response.json()
    ids = [item["id"] for item in payload["items"]]

    assert "RV-1027" not in ids
    assert "RV-1028" not in ids
    assert "RV-1030" not in ids
    assert "RV-1029" not in ids
    assert "RV-1033" not in ids
    assert "RV-1034" not in ids
    assert ids == ["RV-1024", "RV-1025", "RV-1032", "RV-1035", "RV-1026", "RV-1031"]
    assert payload["active_count"] == 9
    assert payload["unclaimed_count"] == 6
    assert payload["claimed_by_me_count"] == 1
    assert payload["terminal_count"] == 3


def test_claimed_by_me_queue_returns_only_current_reviewers_items():
    response = client.get("/api/items/claimed-by-me")

    assert response.status_code == 200
    payload = response.json()
    ids = [item["id"] for item in payload["items"]]

    assert ids == ["RV-1030"]
    assert payload["current_reviewer"] == "alex"
    assert payload["claimed_by_me_count"] == 1
    assert payload["items"][0]["allowed_actions"] == ["approve", "reject", "escalate"]


def test_items_include_only_currently_allowed_actions_for_unclaimed_queue():
    response = client.get("/api/items")

    assert response.status_code == 200
    items = {item["id"]: item for item in response.json()["items"]}

    assert items["RV-1024"]["allowed_actions"] == ["claim"]


def test_claim_records_reviewer_and_moves_item_into_review():
    response = client.post(
        "/api/items/RV-1031/actions",
        json={"action": "claim", "reviewer": "alex"},
    )

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["status"] == "in_review"
    assert item["assigned_reviewer"] == "alex"
    assert item["allowed_actions"] == ["approve", "reject", "escalate"]

    claimed_response = client.get("/api/items/claimed-by-me")
    claimed_ids = [item["id"] for item in claimed_response.json()["items"]]
    assert "RV-1031" in claimed_ids

    unclaimed_response = client.get("/api/items")
    unclaimed_ids = [item["id"] for item in unclaimed_response.json()["items"]]
    assert "RV-1031" not in unclaimed_ids


@pytest.mark.parametrize(
    ("action", "expected_status"),
    [
        ("approve", "approved"),
        ("reject", "rejected"),
        ("escalate", "escalated"),
    ],
)
def test_in_review_items_can_move_to_terminal_states(action, expected_status):
    response = client.post(
        "/api/items/RV-1030/actions",
        json={"action": action, "reviewer": "alex"},
    )

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["status"] == expected_status
    assert item["allowed_actions"] == []

    queue_response = client.get("/api/items/claimed-by-me")
    active_ids = [item["id"] for item in queue_response.json()["items"]]
    assert "RV-1030" not in active_ids


@pytest.mark.parametrize(
    ("item_id", "action", "expected_message"),
    [
        ("RV-1034", "claim", "cannot be changed"),
        ("RV-1024", "approve", "Only in-review items"),
        ("RV-1030", "claim", "Only unassigned items"),
    ],
)
def test_invalid_actions_are_rejected_cleanly(item_id, action, expected_message):
    response = client.post(
        f"/api/items/{item_id}/actions",
        json={"action": action, "reviewer": "alex"},
    )

    assert response.status_code == 400
    assert expected_message in response.json()["detail"]


def test_unknown_item_returns_not_found():
    response = client.post(
        "/api/items/RV-9999/actions",
        json={"action": "claim", "reviewer": "alex"},
    )

    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]
