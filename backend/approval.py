from typing import Literal

from pydantic import BaseModel, Field

from backend.negotiation import (
    NegotiationConfig,
    NegotiationOffer,
    validate_offer,
)


class ApprovalDecision(BaseModel):
    action: Literal["APPROVE", "REJECT", "MODIFY"]
    modified_amount: float | None = Field(default=None, gt=0)


def process_approval(
    offer: NegotiationOffer,
    decision: ApprovalDecision,
    config: NegotiationConfig,
) -> NegotiationOffer | None:

    if decision.action == "REJECT":
        return None

    if decision.action == "APPROVE":
        if not validate_offer(offer, config):
            raise ValueError("Offer exceeds maximum budget.")
        return offer

    if decision.action == "MODIFY":
        if decision.modified_amount is None:
            raise ValueError("Modified amount is required.")

        modified_offer = NegotiationOffer(
            amount=decision.modified_amount,
            message=(
                f"Thank you for your response. "
                f"I would like to offer ${decision.modified_amount:g}. "
                f"Would you consider this price?"
            ),
        )

        if not validate_offer(modified_offer, config):
            raise ValueError("Modified offer exceeds maximum budget.")

        return modified_offer

    raise ValueError("Invalid approval action.")