import re
from typing import Literal

from pydantic import BaseModel


NegotiationOutcome = Literal[
    "ACCEPTED",
    "REJECTED",
    "CONTINUE",
    "NEEDS_CONFIRMATION",
]


class OutcomeResult(BaseModel):
    outcome: NegotiationOutcome
    reason: str


def detect_outcome(
    seller_message: str,
    last_approved_amount: float,
) -> OutcomeResult:

    message = " ".join(seller_message.lower().split())
    message = message.replace("’", "'")

    # 1. Detect explicit termination of negotiations
    rejection_phrases = [
        "i am no longer interested",
        "i don't want to negotiate",
        "the deal is off",
        "no deal",
        "i'm ending the negotiation",
    ]

    if any(phrase in message for phrase in rejection_phrases):
        return OutcomeResult(
            outcome="REJECTED",
            reason="Seller ended the negotiation.",
        )

    # 2. Detect explicit refusal of an offer
    refusal_phrases = [
        "i do not accept",
        "i don't accept",
        "i cannot accept",
        "i can't accept",
        "i won't accept",
        "i will not accept",
        "i disagree",
        "i do not agree",
        "i don't agree",
        "i reject",
        "not accepted",
    ]

    if any(phrase in message for phrase in refusal_phrases):
        return OutcomeResult(
            outcome="CONTINUE",
            reason="Seller did not accept the current offer.",
        )

    # 3. Detect possible acceptance
    acceptance_phrases = [
        "i accept",
        "i agree",
        "we have a deal",
        "it's a deal",
        "deal accepted",
    ]

    has_acceptance = any(
        phrase in message
        for phrase in acceptance_phrases
    )

    if not has_acceptance:
        return OutcomeResult(
            outcome="CONTINUE",
            reason="No explicit acceptance detected.",
        )

    # 4. Extract prices written with a dollar sign
    price_matches = re.findall(
        r"\$\s*(\d+(?:\.\d{1,2})?)\b",
        message,
    )

    prices = [float(price) for price in price_matches]

    if not prices:
        return OutcomeResult(
            outcome="NEEDS_CONFIRMATION",
            reason="Seller accepted without confirming the exact price.",
        )

    if len(prices) != 1:
        return OutcomeResult(
            outcome="NEEDS_CONFIRMATION",
            reason="Multiple prices mentioned in seller response.",
        )

    accepted_price = prices[0]

    # 5. Detect conditional acceptance
    conditional_phrases = [
        "but only if",
        "only if",
        "provided that",
        "on condition that",
        "as long as",
        "if you",
        "subject to",
        "but you must",
        "but you'll need to",
        "but you need to",
        "with the condition",
        "under the condition",
        "assuming that",
        "excluding shipping",
        "plus shipping",
        "plus delivery",
        "additional fee",
        "extra charge",
    ]

    if any(phrase in message for phrase in conditional_phrases):
        return OutcomeResult(
            outcome="NEEDS_CONFIRMATION",
            reason="Seller acceptance includes additional conditions.",
        )

    # 6. Detect conflicting or ambiguous acceptance
    ambiguous_phrases = [
        "but",
        "however",
        "although",
        "unless",
        "maybe",
        "possibly",
        "might",
        "could",
        "pending",
        "not final",
    ]

    if any(
        re.search(rf"\b{re.escape(phrase)}\b", message)
        for phrase in ambiguous_phrases
    ):
        return OutcomeResult(
            outcome="NEEDS_CONFIRMATION",
            reason="Seller acceptance contains ambiguous terms.",
        )

    # 7. Check whether seller accepted the approved amount
    if abs(accepted_price - last_approved_amount) < 0.001:
        return OutcomeResult(
            outcome="ACCEPTED",
            reason="Seller explicitly accepted the last approved offer.",
        )

    # 8. Different price: negotiations must continue
    return OutcomeResult(
        outcome="CONTINUE",
        reason="Seller proposed a different price.",
    )