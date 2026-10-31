from fastapi.testclient import TestClient

from backend.main import app, sessions


client = TestClient(app)


def test_final_buyer_confirmation():
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

    response = client.post(
        f"/api/v1/negotiations/{session_id}/seller-response",
        json={"message": "I accept your offer of $300."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING_FINAL_APPROVAL"

    response = client.post(
        f"/api/v1/negotiations/{session_id}/final-approval",
        json={"action": "CONFIRM"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"

    session = client.get(
        f"/api/v1/negotiations/{session_id}"
    ).json()

    assert session["status"] == "COMPLETED"
    assert session["last_approved_amount"] == 300

def test_final_buyer_rejection():
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

    response = client.post(
        f"/api/v1/negotiations/{session_id}/seller-response",
        json={"message": "I accept your offer of $300."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "PENDING_FINAL_APPROVAL"

    response = client.post(
        f"/api/v1/negotiations/{session_id}/final-approval",
        json={"action": "REJECT"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"

    session = client.get(
        f"/api/v1/negotiations/{session_id}"
    ).json()

    assert session["status"] == "CANCELLED"

def test_cannot_confirm_agreement_twice():
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

    response = client.post(
        f"/api/v1/negotiations/{session_id}/seller-response",
        json={"message": "I accept your offer of $300."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "PENDING_FINAL_APPROVAL"

    response = client.post(
        f"/api/v1/negotiations/{session_id}/final-approval",
        json={"action": "CONFIRM"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"

    # Attempt to confirm the same agreement again
    response = client.post(
        f"/api/v1/negotiations/{session_id}/final-approval",
        json={"action": "CONFIRM"},
    )

    assert response.status_code == 409        