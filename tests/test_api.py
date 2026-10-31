import pytest
from fastapi.testclient import TestClient

from backend.main import app, sessions
from backend.negotiation import NegotiationOffer


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_sessions():
    sessions.clear()
    yield
    sessions.clear()


def create_session():
    response = client.post(
        "/api/v1/negotiations",
        json={
            "item": "Used MacBook Pro",
            "target_price": 400,
            "max_budget": 500,
            "opening_offer": 300,
        },
    )

    assert response.status_code == 201
    return response.json()["session_id"]


def approve_opening_offer(session_id):
    response = client.post(
        f"/api/v1/negotiations/{session_id}/opening-offer"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING_APPROVAL"

    response = client.post(
        f"/api/v1/negotiations/{session_id}/approval",
        json={"action": "APPROVE"},
    )

    assert response.status_code == 200
    return response.json()


def test_create_negotiation():
    session_id = create_session()

    response = client.get(
        f"/api/v1/negotiations/{session_id}"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CREATED"


def test_opening_offer_requires_approval():
    session_id = create_session()

    response = client.post(
        f"/api/v1/negotiations/{session_id}/opening-offer"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING_APPROVAL"

    session = client.get(
        f"/api/v1/negotiations/{session_id}"
    ).json()

    assert session["last_approved_amount"] is None
    assert session["round_number"] == 0


def test_approve_opening_offer():
    session_id = create_session()

    result = approve_opening_offer(session_id)

    assert result["status"] == "ACTIVE"
    assert result["last_approved_amount"] == 300

    session = client.get(
        f"/api/v1/negotiations/{session_id}"
    ).json()

    assert session["round_number"] == 1
    assert session["last_approved_amount"] == 300


def test_seller_accepts_approved_offer():
    session_id = create_session()
    approve_opening_offer(session_id)

    response = client.post(
        f"/api/v1/negotiations/{session_id}/seller-response",
        json={"message": "I accept your offer of $300"},
    )

    assert response.status_code == 200

    result = response.json()

    assert result["status"] == "PENDING_FINAL_APPROVAL"
    assert result["outcome"] == "ACCEPTED"
    assert result["agreed_amount"] == 300


def test_completed_negotiation_cannot_continue():
    session_id = create_session()
    approve_opening_offer(session_id)

    client.post(
        f"/api/v1/negotiations/{session_id}/seller-response",
        json={"message": "I accept $300"},
    )

    response = client.post(
        f"/api/v1/negotiations/{session_id}/seller-response",
        json={"message": "Actually, I want $400"},
    )

    assert response.status_code == 409


def test_conditional_acceptance_requires_confirmation():
    session_id = create_session()
    approve_opening_offer(session_id)

    response = client.post(
        f"/api/v1/negotiations/{session_id}/seller-response",
        json={
            "message": (
                "I accept $300, but only if you include free shipping."
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "NEEDS_CONFIRMATION"
    assert response.json()["status"] == "ACTIVE"


def test_seller_cannot_respond_before_approval():
    session_id = create_session()

    response = client.post(
        f"/api/v1/negotiations/{session_id}/seller-response",
        json={"message": "I accept $300"},
    )

    assert response.status_code == 409


def test_modified_offer_cannot_exceed_budget():
    session_id = create_session()

    client.post(
        f"/api/v1/negotiations/{session_id}/opening-offer"
    )

    response = client.post(
        f"/api/v1/negotiations/{session_id}/approval",
        json={
            "action": "MODIFY",
            "modified_amount": 600,
        },
    )

    assert response.status_code in (400, 422)

    session = client.get(
        f"/api/v1/negotiations/{session_id}"
    ).json()

    assert session["last_approved_amount"] is None
    assert session["status"] == "PENDING_APPROVAL"


def test_seller_ends_negotiation():
    session_id = create_session()
    approve_opening_offer(session_id)

    response = client.post(
        f"/api/v1/negotiations/{session_id}/seller-response",
        json={"message": "The deal is off"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["outcome"] == "REJECTED"


def test_counteroffer_requires_human_approval(monkeypatch):
    session_id = create_session()
    approve_opening_offer(session_id)

    def fake_counteroffer(session, seller_message):
        return NegotiationOffer(
            amount=330,
            message="I can offer $330.",
        )

    monkeypatch.setattr(
        "backend.main.generate_counteroffer_with_memory",
        fake_counteroffer,
    )

    response = client.post(
        f"/api/v1/negotiations/{session_id}/seller-response",
        json={"message": "I would like $450"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING_APPROVAL"
    assert response.json()["proposed_amount"] == 330

    session = client.get(
        f"/api/v1/negotiations/{session_id}"
    ).json()

    # AI suggestion must not change the approved amount
    assert session["last_approved_amount"] == 300
    assert session["round_number"] == 1

    approval = client.post(
        f"/api/v1/negotiations/{session_id}/approval",
        json={"action": "APPROVE"},
    )

    assert approval.status_code == 200
    assert approval.json()["last_approved_amount"] == 330
    assert approval.json()["status"] == "ACTIVE"