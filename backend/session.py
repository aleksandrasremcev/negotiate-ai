from typing import Literal

from pydantic import BaseModel, Field

from backend.negotiation import (
    NegotiationConfig,
    NegotiationOffer,
)


class NegotiationMessage(BaseModel):
    role: Literal["buyer", "seller"]
    content: str = Field(min_length=1)


class NegotiationSession(BaseModel):
    config: NegotiationConfig

    # Negotiation conversation history
    messages: list[NegotiationMessage] = Field(default_factory=list)

    # Number of approved buyer offers
    round_number: int = Field(default=0, ge=0)

    # AI proposal waiting for human approval
    pending_offer: NegotiationOffer | None = None

    # Last amount explicitly approved by the buyer
    last_approved_amount: float | None = Field(default=None, gt=0)

    # Current negotiation status
    status: Literal[
        "CREATED",
        "PENDING_APPROVAL",
        "ACTIVE",
        "COMPLETED",
        "CANCELLED",
    ] = "CREATED"

    def add_message(
        self,
        role: Literal["buyer", "seller"],
        content: str,
    ) -> None:

        self.messages.append(
            NegotiationMessage(
                role=role,
                content=content,
            )
        )

    def get_history(self) -> list[dict[str, str]]:

        return [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in self.messages
        ]

    def set_pending_offer(
        self,
        offer: NegotiationOffer,
    ) -> None:

        if self.status in ("COMPLETED", "CANCELLED"):
            raise ValueError(
                "Cannot create an offer for a closed negotiation."
            )

        if self.pending_offer is not None:
            raise ValueError(
                "An offer is already waiting for approval."
            )

        self.pending_offer = offer
        self.status = "PENDING_APPROVAL"

    def clear_pending_offer(self) -> None:

        self.pending_offer = None

        if self.status == "PENDING_APPROVAL":
            self.status = (
                "ACTIVE" if self.messages else "CREATED"
            )

    def record_approved_offer(
        self,
        offer: NegotiationOffer,
    ) -> None:

        if self.status != "PENDING_APPROVAL":
            raise ValueError(
                "No offer is waiting for approval."
            )

        if self.pending_offer is None:
            raise ValueError(
                "Pending offer not found."
            )

        if offer.amount > self.config.max_budget:
            raise ValueError(
                "Approved offer exceeds maximum budget."
            )

        self.add_message(
            role="buyer",
            content=offer.message,
        )

        self.last_approved_amount = offer.amount

        self.round_number += 1

        self.clear_pending_offer()

        self.status = "ACTIVE"