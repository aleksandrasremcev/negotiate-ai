
from unittest.mock import patch

import pytest

from backend.agent import generate_counteroffer_with_memory
from backend.negotiation import NegotiationConfig, NegotiationOffer
from backend.session import NegotiationSession


def create_session():
    config = NegotiationConfig(
        item="Used MacBook Pro",
        target_price=400,
        max_budget=500,
        opening_offer=300,
        mode="AUTONOMOUS",
        max_rounds=5,
    )

    session = NegotiationSession(config=config)

    opening_offer = NegotiationOffer(
        amount=300,
        message="I can offer $300.",
    )

    session.set_pending_offer(opening_offer)
    session.record_approved_offer(opening_offer)

    return session


def test_repeated_offer_is_retried():
    session = create_session()

    responses = [
        '{"amount": 300, "message": "I can offer $300."}',
        '{"amount": 350, "message": "I can offer $350."}',
    ]

    with patch(
        "backend.agent._request_ai",
        side_effect=responses,
    ) as mock_ai:
        offer = generate_counteroffer_with_memory(
            session=session,
            seller_message="Can you increase your offer?",
        )

    assert offer.amount == 350
    assert mock_ai.call_count == 2


def test_repeated_offer_twice_is_rejected():
    session = create_session()

    repeated = (
        '{"amount": 300, "message": "I can offer $300."}'
    )

    with patch(
        "backend.agent._request_ai",
        return_value=repeated,
    ) as mock_ai:
        with pytest.raises(
            ValueError,
            match="repeated",
        ):
            generate_counteroffer_with_memory(
                session=session,
                seller_message="Can you increase your offer?",
            )

    assert mock_ai.call_count == 2
