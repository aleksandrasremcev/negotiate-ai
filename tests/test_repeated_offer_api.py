
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app, sessions


client = TestClient(app)


def test_repeated_offer_returns_controlled_response():
    sessions.clear()

    # Create a negotiation
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

    # Create and approve the opening offer
    response = client.post(
        f"/api/v1/negotiations/{session_id}/opening-offer"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"

    # Simulate AI failing to produce a new price
    with patch(
        "backend.main.generate_counteroffer_with_memory",
        side_effect=ValueError(
            "AI generated a repeated offer after retry."
        ),
    ) as mock_ai:
        response = client.post(
            f"/api/v1/negotiations/{session_id}/seller-response",
            json={
                "message": "Could you offer a little more?"
            },
        )

    # AI was called, but no new offer was recorded
    mock_ai.assert_called_once()

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ACTIVE"
    assert data["outcome"] == "REPEATED_OFFER"

    # Check that the negotiation round was not consumed
    response = client.get(
        f"/api/v1/negotiations/{session_id}"
    )

    assert response.status_code == 200

    session = response.json()

    assert session["round_number"] == 1
    assert session["last_approved_amount"] == 300
    assert session["pending_offer"] is None

    # Seller message is preserved in negotiation history
    assert session["messages"][-1] == {
        "role": "seller",
        "content": "Could you offer a little more?",
    }

    # No second buyer offer was added
    buyer_messages = [
        message
        for message in session["messages"]
        if message["role"] == "buyer"
    ]

    assert len(buyer_messages) == 1
