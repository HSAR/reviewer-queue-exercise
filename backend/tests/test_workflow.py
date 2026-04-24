from fastapi.testclient import TestClient
import pytest

from app.main import app, items_by_id, load_items


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_items():
    items_by_id.clear()
    items_by_id.update(load_items())


def test_active_queue_excludes_terminal_items_and_orders_by_urgency():
    response = client.get("/api/items")

    assert response.status_code == 200
    payload = response.json()
    ids = [item["id"] for item in payload["items"]]

    assert "RV-1029" not in ids
    assert "RV-1033" not in ids
    assert "RV-1034" not in ids
    assert ids[:4] == ["RV-1024", "RV-1030", "RV-1025", "RV-1032"]


def test_claim_records_reviewer_and_moves_item_into_review():
    response = client.post(
        "/api/items/RV-1031/actions",
        json={"action": "claim", "reviewer": "alex"},
    )

    assert response.status_code == 200
    item = response.json()["item"]
    assert item["status"] == "in_review"
    assert item["assigned_reviewer"] == "alex"


def test_invalid_action_is_rejected_cleanly():
    response = client.post(
        "/api/items/RV-1034/actions",
        json={"action": "claim", "reviewer": "alex"},
    )

    assert response.status_code == 400
    assert "cannot be changed" in response.json()["detail"]
