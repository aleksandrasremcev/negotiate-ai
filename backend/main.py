import logging
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from backend.agent import generate_offer
from backend.approval import ApprovalDecision, process_approval
from backend.negotiation import (
    NegotiationConfig,
    NegotiationOffer,
    validate_offer,
)
from backend.session import NegotiationSession


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize FastAPI application
app = FastAPI(
    title="NegotiateAI API",
    description="AI-powered negotiation assistant",
    version="0.2.0",
)


# Temporary in-memory storage
sessions: dict[str, NegotiationSession] = {}


# Health check
@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "NegotiateAI",
    }


# Create a new negotiation session
@app.post("/api/v1/negotiations", status_code=201)
def create_negotiation(config: NegotiationConfig):

    session_id = f"neg_{uuid4().hex[:12]}"

    session = NegotiationSession(config=config)

    sessions[session_id] = session

    return {
        "session_id": session_id,
        "status": session.status,
        "config": config.model_dump(),
    }


# Get negotiation session details
@app.get("/api/v1/negotiations/{session_id}")
def get_negotiation(session_id: str):

    session = sessions.get(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Negotiation session not found.",
        )

    return {
        "session_id": session_id,
        "status": session.status,
        "config": session.config.model_dump(),
        "pending_offer": (
            session.pending_offer.model_dump()
            if session.pending_offer is not None
            else None
        ),
        "round_number": session.round_number,
        "messages": session.get_history(),
    }


# Generate an opening offer
@app.post("/api/v1/negotiations/{session_id}/opening-offer")
def create_opening_offer(session_id: str):

    session = sessions.get(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Negotiation session not found.",
        )

    # Opening offer can only be generated for a new session
    if session.status != "CREATED":
        raise HTTPException(
            status_code=409,
            detail="Opening offer is not allowed in the current session state.",
        )

    if session.pending_offer is not None or session.messages:
        raise HTTPException(
            status_code=409,
            detail="An opening offer already exists.",
        )

    # The amount is determined by Python, not the AI
    opening_amount = session.config.opening_offer

    offer = NegotiationOffer(
        amount=opening_amount,
        message=(
            f"I would like to offer ${opening_amount:g} "
            f"for {session.config.item}. "
            "Would you consider this price?"
        ),
    )

    # Enforce budget limit
    if not validate_offer(offer, session.config):
        raise HTTPException(
            status_code=400,
            detail="Opening offer exceeds maximum budget.",
        )

    # Ask AI to generate a negotiation message
    try:
        ai_message = generate_offer(session.config)

    except Exception:
        logger.exception(
            "Failed to generate opening offer for session %s",
            session_id,
        )

        raise HTTPException(
            status_code=502,
            detail="AI service failed to generate an opening offer.",
        ) from None

    # Keep the validated amount and construct the final message in Python.
    # Do not use the AI's unvalidated monetary statements.
    safe_message = (
        f"Hello, I am interested in {session.config.item}. "
        f"I would like to offer ${opening_amount:g}. "
        "Would you be willing to consider this price?"
    )

    # Store proposal for human approval
    pending_offer = NegotiationOffer(
        amount=opening_amount,
        message=safe_message,
    )

    session.set_pending_offer(pending_offer)

    return {
        "session_id": session_id,
        "status": session.status,
        "proposed_amount": pending_offer.amount,
        "message": pending_offer.message,
    }


# Human approval endpoint
@app.post("/api/v1/negotiations/{session_id}/approval")
def approve_negotiation_offer(
    session_id: str,
    decision: ApprovalDecision,
):

    session = sessions.get(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Negotiation session not found.",
        )

    if session.status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=409,
            detail="No offer is currently waiting for approval.",
        )

    pending_offer = session.pending_offer

    if pending_offer is None:
        raise HTTPException(
            status_code=409,
            detail="Pending offer not found.",
        )

    # Process APPROVE / REJECT / MODIFY
    try:
        approved_offer = process_approval(
            offer=pending_offer,
            decision=decision,
            config=session.config,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    # Reject the proposal
    if decision.action == "REJECT":
        session.clear_pending_offer()

        return {
            "session_id": session_id,
            "status": session.status,
            "decision": "REJECTED",
            "approved_offer": None,
        }

    # Approved or modified offer
    if approved_offer is None:
        raise HTTPException(
            status_code=500,
            detail="Approval processing failed.",
        )

    # Record the approved buyer message
    session.add_message(
        role="buyer",
        content=approved_offer.message,
    )

    session.round_number += 1

    session.clear_pending_offer()

    session.status = "ACTIVE"

    return {
        "session_id": session_id,
        "status": session.status,
        "decision": decision.action,
        "approved_offer": approved_offer.model_dump(),
        "message": (
            "Offer approved and recorded locally. "
            "It has not been sent to the seller."
        ),
    }