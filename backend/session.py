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

    # Number of completed negotiation rounds
    round_number: int = Field(default=0, ge=0)

    # AI proposal waiting for human approval
    pending_offer: NegotiationOffer | None = None

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