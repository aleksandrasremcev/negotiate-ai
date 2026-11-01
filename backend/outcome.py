
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


def _contains_phrase(message: str, phrase: str) -> bool:
    pattern = rf"(?<!\w){re.escape(phrase)}(?!\w)"
    return bool(re.search(pattern, message))

def _extract_prices(message: str) -> list[float]:
    pattern = r"\$\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)"

    matches = re.findall(pattern, message)

    return [
        float(value.replace(",", ""))
        for value in matches
    ]

def detect_outcome(
    seller_message: str,
    last_approved_amount: float,
) -> OutcomeResult:

    message = " ".join(seller_message.lower().split())
    message = message.replace("’", "'")

    prices = _extract_prices(message)

    # 1. Explicit termination
    termination_phrases = [
        "i am no longer interested",
        "i don't want to negotiate",
        "i do not want to negotiate",
        "the deal is off",
        "no deal",
        "i'm ending the negotiation",
        "i am ending the negotiation",
        "i won't negotiate",
        "i will not negotiate",
    ]

    if any(
        _contains_phrase(message, phrase)
        for phrase in termination_phrases
    ):
        return OutcomeResult(
            outcome="REJECTED",
            reason="Seller explicitly ended negotiations.",
        )

    # 2. Explicit refusal of the current offer
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

    has_refusal = any(
        _contains_phrase(message, phrase)
        for phrase in refusal_phrases
    )

    # 3. Detect firm final price above current offer
    final_price_phrases = [
        "my final price",
        "my absolute minimum",
        "my lowest price",
        "my firm price",
        "non-negotiable",
        "not negotiable",
        "will not go any lower",
        "won't go any lower",
    ]

    has_firm_price = any(
        _contains_phrase(message, phrase)
        for phrase in final_price_phrases
    )

    if has_firm_price and prices:
        if min(prices) > last_approved_amount:
            return OutcomeResult(
                outcome="NEEDS_CONFIRMATION",
                reason=(
                    "Seller stated a firm price above the current "
                    "offer. Buyer should review before continuing."
                ),
            )

    # 4. Detect seller asking to wait
    waiting_phrases = [
        "let me check",
        "let me think",
        "i need to check",
        "i need to think",
        "i'll get back to you",
        "i will get back to you",
        "give me some time",
        "not ready to decide",
        "i need more time",
        "i'll confirm later",
        "i will confirm later",
    ]

    if any(
        _contains_phrase(message, phrase)
        for phrase in waiting_phrases
    ):
        return OutcomeResult(
            outcome="NEEDS_CONFIRMATION",
            reason="Seller has not made a final decision.",
        )

    # 5. Explicit refusal without termination
    if has_refusal:
        return OutcomeResult(
            outcome="CONTINUE",
            reason="Seller refused the current offer.",
        )

    # 6. Detect acceptance
    acceptance_phrases = [
        "i accept",
        "i agree",
        "we have a deal",
        "it's a deal",
        "deal accepted",
    ]

    has_acceptance = any(
        _contains_phrase(message, phrase)
        for phrase in acceptance_phrases
    )

    if not has_acceptance:
        return OutcomeResult(
            outcome="CONTINUE",
            reason="No explicit acceptance detected.",
        )

    # 7. Conditions requiring human confirmation
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

    if any(
        _contains_phrase(message, phrase)
        for phrase in conditional_phrases
    ):
        return OutcomeResult(
            outcome="NEEDS_CONFIRMATION",
            reason="Seller acceptance contains additional conditions.",
        )

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
        _contains_phrase(message, phrase)
        for phrase in ambiguous_phrases
    ):
        return OutcomeResult(
            outcome="NEEDS_CONFIRMATION",
            reason="Seller acceptance is ambiguous.",
        )

    # 8. Require one explicit price
    if len(prices) != 1:
        return OutcomeResult(
            outcome="NEEDS_CONFIRMATION",
            reason="Seller must confirm one exact price.",
        )

    accepted_price = prices[0]

    # 9. Compare with approved buyer offer
    if abs(accepted_price - last_approved_amount) < 0.001:
        return OutcomeResult(
            outcome="ACCEPTED",
            reason="Seller explicitly accepted the approved offer.",
        )

    return OutcomeResult(
        outcome="CONTINUE",
        reason="Seller proposed a different price.",
    )
