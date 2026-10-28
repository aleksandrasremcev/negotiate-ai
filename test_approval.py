from backend.negotiation import NegotiationConfig, NegotiationOffer
from backend.approval import ApprovalDecision, process_approval


# Negotiation configuration
config = NegotiationConfig(
    item="Website design",
    opening_offer=300,
    target_price=400,
    max_budget=500,
)

# AI-generated offer
offer = NegotiationOffer(
    amount=350,
    message="I would like to offer $350.",
)


print("\nNEGOTIATEAI - HUMAN APPROVAL TEST")
print("-" * 45)


# TEST 1: APPROVE
print("\nTEST 1 - APPROVE")

decision = ApprovalDecision(action="APPROVE")
result = process_approval(offer, decision, config)

assert result is not None
assert result.amount == 350

print("Approved offer:", result.amount)
print("PASSED")


# TEST 2: REJECT
print("\nTEST 2 - REJECT")

decision = ApprovalDecision(action="REJECT")
result = process_approval(offer, decision, config)

assert result is None

print("Offer rejected")
print("PASSED")


# TEST 3: MODIFY
print("\nTEST 3 - MODIFY")

decision = ApprovalDecision(
    action="MODIFY",
    modified_amount=400,
)

result = process_approval(offer, decision, config)

assert result is not None
assert result.amount == 400

print("Modified offer:", result.amount)
print("PASSED")


# TEST 4: EXCEED MAXIMUM BUDGET
print("\nTEST 4 - BUDGET PROTECTION")

decision = ApprovalDecision(
    action="MODIFY",
    modified_amount=600,
)

try:
    process_approval(offer, decision, config)

except ValueError as error:
    print("Blocked:", error)
    print("PASSED")

else:
    raise AssertionError("Budget protection failed!")


print("\nALL HUMAN APPROVAL TESTS PASSED")