from backend.agent import generate_safe_counteroffer
from backend.negotiation import NegotiationConfig

config = NegotiationConfig(
    item="Website design",
    opening_offer=300,
    target_price=400,
    max_budget=500,
)

seller_message = (
    "Thank you for your offer. "
    "My price for the website design is $600."
)

print("\nNEGOTIATEAI - COUNTEROFFER")
print("-" * 40)
print(f"Seller: {seller_message}")

try:
    offer = generate_safe_counteroffer(config, seller_message)

    print(f"\nAI proposed amount: ${offer.amount}")
    print(f"AI message: {offer.message}")
    print("\nBudget validation: PASSED")

except Exception as error:
    print(f"\nCounteroffer rejected: {error}")