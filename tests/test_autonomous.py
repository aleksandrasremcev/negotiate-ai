from fastapi.testclient import TestClient

from backend.main import app, sessions
from backend.negotiation import NegotiationOffer


client = TestClient(app)


def test_autonomous_opening_offer():
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
    assert response.json()["status"] == "ACTIVE"

    session = client.get(
        f"/api/v1/negotiations/{session_id}"
    ).json()

    assert session["last_approved_amount"] == 300
    assert session["round_number"] == 1
    assert session["pending_offer"] is None


def test_autonomous_counteroffer(monkeypatch):
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

    # Automatically approve opening offer
    response = client.post(
        f"/api/v1/negotiations/{session_id}/opening-offer"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"

    # Simulate AI-generated counteroffer without calling real API
    def fake_counteroffer(session, seller_message):
        return NegotiationOffer(
            amount=350,
            message="I can offer $350.",
        )

    monkeypatch.setattr(
        "backend.main.generate_counteroffer_with_memory",
        fake_counteroffer,
    )

    # Seller asks for a higher price
    response = client.post(
        f"/api/v1/negotiations/{session_id}/seller-response",
        json={"message": "I would like $450"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"
    assert response.json()["proposed_amount"] == 350

    # Verify autonomous approval
    session = client.get(
        f"/api/v1/negotiations/{session_id}"
    ).json()

    assert session["last_approved_amount"] == 350
    assert session["round_number"] == 2
    assert session["pending_offer"] is None


def test_autonomous_rejects_over_budget_counteroffer(monkeypatch):
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

    # Automatically approve opening offer
    response = client.post(
        f"/api/v1/negotiations/{session_id}/opening-offer"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"

    # Simulate an AI offer exceeding the maximum budget
    def fake_counteroffer(session, seller_message):
        return NegotiationOffer(
            amount=600,
            message="I can offer $600.",
        )

    monkeypatch.setattr(
        "backend.main.generate_counteroffer_with_memory",
        fake_counteroffer,
    )

    response = client.post(
        f"/api/v1/negotiations/{session_id}/seller-response",
        json={"message": "I want $700."},
    )

    # Backend must reject the over-budget offer
    assert response.status_code == 400

    session = client.get(
        f"/api/v1/negotiations/{session_id}"
    ).json()

    # The original approved offer must remain unchanged
    assert session["last_approved_amount"] == 300
    assert session["round_number"] == 1
    assert session["pending_offer"] is None

def test_autonomous_stops_at_max_rounds(monkeypatch):
    sessions.clear()

    response = client.post(
        "/api/v1/negotiations",
        json={
            "item": "Used MacBook Pro",
            "target_price": 400,
            "max_budget": 500,
            "opening_offer": 300,
            "mode": "AUTONOMOUS",
            "max_rounds": 1,
        },
    )

    assert response.status_code == 201
    session_id = response.json()["session_id"]

    response = client.post(
        f"/api/v1/negotiations/{session_id}/opening-offer"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"

    def fake_counteroffer(session, seller_message):
        raise AssertionError(
            "AI must not be called after maximum rounds."
        )

    monkeypatch.setattr(
        "backend.main.generate_counteroffer_with_memory",
        fake_counteroffer,
    )

    response = client.post(
        f"/api/v1/negotiations/{session_id}/seller-response",
        json={"message": "I want $450."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["outcome"] == "MAX_ROUNDS_REACHED"

    session = client.get(
        f"/api/v1/negotiations/{session_id}"
    ).json()

    assert session["round_number"] == 1
    assert session["last_approved_amount"] == 300
    assert session["pending_offer"] is None   