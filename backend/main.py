import logging
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.agent import generate_counteroffer_with_memory
from backend.approval import ApprovalDecision, process_approval
from backend.negotiation import (
    NegotiationConfig,
    NegotiationOffer,
    validate_offer,
)
from backend.outcome import detect_outcome
from backend.session import NegotiationSession

from typing import Literal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="NegotiateAI API",
    description="AI-powered negotiation assistant",
    version="0.5.0",
)


# Temporary in-memory storage
sessions: dict[str, NegotiationSession] = {}


class SellerResponse(BaseModel):
    message: str = Field(min_length=1)
    
class FinalApprovalDecision(BaseModel):
    action: Literal["CONFIRM", "REJECT"]


def record_offer(
    session: NegotiationSession,
    offer: NegotiationOffer,
) -> None:
    """
    Record an offer according to the negotiation mode.

    MANUAL:
        Wait for human approval.

    AUTONOMOUS:
        Automatically approve an offer within configured limits.

    This function does not send messages to sellers.
    """

    if session.round_number >= session.config.max_rounds:
        raise HTTPException(
            status_code=409,
            detail="Maximum negotiation rounds reached.",
        )

    if not validate_offer(offer, session.config):
        raise HTTPException(
            status_code=400,
            detail="Offer exceeds maximum budget.",
        )

    try:
        session.set_pending_offer(offer)

        if session.config.mode == "AUTONOMOUS":
            session.record_approved_offer(offer)

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "NegotiateAI",
    }


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
        "last_approved_amount": session.last_approved_amount,
        "round_number": session.round_number,
        "messages": session.get_history(),
    }


@app.post("/api/v1/negotiations/{session_id}/opening-offer")
def create_opening_offer(session_id: str):

    session = sessions.get(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Negotiation session not found.",
        )

    if session.status != "CREATED":
        raise HTTPException(
            status_code=409,
            detail="Opening offer is not allowed in the current state.",
        )

    if session.pending_offer is not None or session.messages:
        raise HTTPException(
            status_code=409,
            detail="An opening offer already exists.",
        )

    opening_amount = session.config.opening_offer

    opening_offer = NegotiationOffer(
        amount=opening_amount,
        message=(
            f"Hello, I am interested in {session.config.item}. "
            f"I would like to offer ${opening_amount:g}. "
            "Would you be willing to consider this price?"
        ),
    )

    record_offer(
        session=session,
        offer=opening_offer,
    )

    return {
        "session_id": session_id,
        "status": session.status,
        "proposed_amount": opening_offer.amount,
        "message": opening_offer.message,
    }


@app.post("/api/v1/negotiations/{session_id}/seller-response")
def receive_seller_response(
    session_id: str,
    seller_response: SellerResponse,
):

    session = sessions.get(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Negotiation session not found.",
        )

    if session.status != "ACTIVE":
        raise HTTPException(
            status_code=409,
            detail="Negotiation is not active.",
        )

    if session.pending_offer is not None:
        raise HTTPException(
            status_code=409,
            detail="An offer is already waiting for approval.",
        )

    if session.last_approved_amount is None:
        raise HTTPException(
            status_code=409,
            detail="No approved buyer offer exists.",
        )

    # Detect seller acceptance or rejection before calling AI
    outcome = detect_outcome(
        seller_message=seller_response.message,
        last_approved_amount=session.last_approved_amount,
    )

    if outcome.outcome == "ACCEPTED":

        session.add_message(
            role="seller",
            content=seller_response.message,
        )

        session.status = "PENDING_FINAL_APPROVAL"

        return {
            "session_id": session_id,
            "status": session.status,
            "outcome": outcome.outcome,
            "reason": outcome.reason,
            "agreed_amount": session.last_approved_amount,
            "message": (
                "Seller acceptance detected and recorded locally. "
                "No external transaction has been executed."
            ),
        }

    if outcome.outcome == "REJECTED":

        session.add_message(
            role="seller",
            content=seller_response.message,
        )

        session.status = "CANCELLED"

        return {
            "session_id": session_id,
            "status": session.status,
            "outcome": outcome.outcome,
            "reason": outcome.reason,
        }

    if outcome.outcome == "NEEDS_CONFIRMATION":

        session.add_message(
            role="seller",
            content=seller_response.message,
        )

        return {
            "session_id": session_id,
            "status": session.status,
            "outcome": outcome.outcome,
            "reason": outcome.reason,
            "message": (
                "Ask the seller to explicitly confirm the "
                "exact price before proceeding."
            ),
        }

    # Stop before generating another offer if round limit reached
    if session.round_number >= session.config.max_rounds:

        session.add_message(
            role="seller",
            content=seller_response.message,
        )

        session.status = "CANCELLED"

        return {
            "session_id": session_id,
            "status": session.status,
            "outcome": "MAX_ROUNDS_REACHED",
            "reason": "Maximum negotiation rounds reached.",
            "message": (
                "Negotiation stopped because the maximum number "
                "of buyer offers has been reached."
            ),
        }

    # CONTINUE: generate AI counteroffer
    try:
        counteroffer = generate_counteroffer_with_memory(
            session=session,
            seller_message=seller_response.message,
        )

    except Exception:
        logger.exception(
            "Failed to generate counteroffer for session %s",
            session_id,
        )

        raise HTTPException(
            status_code=502,
            detail="AI service failed to generate a counteroffer.",
        ) from None

    if not validate_offer(counteroffer, session.config):
        raise HTTPException(
            status_code=400,
            detail="Counteroffer exceeds maximum budget.",
        )

    session.add_message(
        role="seller",
        content=seller_response.message,
    )

    record_offer(
        session=session,
        offer=counteroffer,
    )

    return {
        "session_id": session_id,
        "status": session.status,
        "outcome": outcome.outcome,
        "proposed_amount": counteroffer.amount,
        "message": counteroffer.message,
    }


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

    if decision.action == "REJECT":

        session.clear_pending_offer()

        return {
            "session_id": session_id,
            "status": session.status,
            "decision": "REJECTED",
            "approved_offer": None,
        }

    if approved_offer is None:
        raise HTTPException(
            status_code=500,
            detail="Approval processing failed.",
        )

    try:
        session.record_approved_offer(approved_offer)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "session_id": session_id,
        "status": session.status,
        "decision": decision.action,
        "approved_offer": approved_offer.model_dump(),
        "last_approved_amount": session.last_approved_amount,
        "message": (
            "Offer approved and recorded locally. "
            "It has not been sent to the seller."
        ),
    }

@app.post("/api/v1/negotiations/{session_id}/final-approval")
def final_approval(
    session_id: str,
    decision: FinalApprovalDecision,
):
    session = sessions.get(session_id)

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Negotiation session not found.",
        )

    if session.status != "PENDING_FINAL_APPROVAL":
        raise HTTPException(
            status_code=409,
            detail="Negotiation is not waiting for final approval.",
        )

    if session.last_approved_amount is None:
        raise HTTPException(
            status_code=409,
            detail="No agreed amount available for confirmation.",
        )

    if decision.action == "CONFIRM":
        session.status = "COMPLETED"
        message = "Agreement confirmed locally. No transaction executed."
    else:
        session.status = "CANCELLED"
        message = "Agreement rejected by buyer. No transaction executed."

    return {
        "session_id": session_id,
        "status": session.status,
        "decision": decision.action,
        "agreed_amount": session.last_approved_amount,
        "message": message,
    }