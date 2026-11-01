
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app, sessions, seller_final_price


client = TestClient(app)


def test_final_price_detection():
    assert seller_final_price("My final price is $600.") == 600
    assert seller_final_price("My price is $600.") is None
    assert seller_final_price("My final price is $400.") == 400


def test_seller_final_price_above_budget():
    sessions.clear()

    response = client.post(
        "/api/v1/negotiations",
        json={
            "item": "Used MacBook Pro",
            "target_price": 400,
            "max_budget": 500,
            "opening_offer": 300,
            "mode": "AUTONOMOUS",
            "max_rounds": 5,
        },
    )

    assert response.status_code == 201
    session_id = response.json()["session_id"]

    response = client.post(
        f"/api/v1/negotiations/{session_id}/opening-offer"
    )
    assert response.status_code == 200

    with patch(
        "backend.main.generate_counteroffer_with_memory"
    ) as mock_ai:
        response = client.post(
            f"/api/v1/negotiations/{session_id}/seller-response",
            json={"message": "My final price is $600."},
        )

        mock_ai.assert_not_called()

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["outcome"] == "BUDGET_LIMIT_REACHED"
