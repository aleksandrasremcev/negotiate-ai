from backend.outcome import detect_outcome


def test_accept_exact_price():
    result = detect_outcome("I accept $360", 360)
    assert result.outcome == "ACCEPTED"


def test_reject_offer():
    result = detect_outcome("I do not accept $360", 360)
    assert result.outcome == "CONTINUE"


def test_different_price():
    result = detect_outcome("I accept $400", 360)
    assert result.outcome == "CONTINUE"


def test_conditional_acceptance():
    result = detect_outcome(
        "I accept $360, but only if you include free shipping.",
        360,
    )
    assert result.outcome == "NEEDS_CONFIRMATION"


def test_acceptance_without_price():
    result = detect_outcome("I accept your offer", 360)
    assert result.outcome == "NEEDS_CONFIRMATION"


def test_seller_ends_negotiation():
    result = detect_outcome("The deal is off", 360)
    assert result.outcome == "REJECTED"


def test_multiple_prices():
    result = detect_outcome(
        "I accept $360, but shipping costs $50",
        360,
    )
    assert result.outcome == "NEEDS_CONFIRMATION"