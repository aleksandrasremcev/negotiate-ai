from backend.negotiation import NegotiationConfig
from backend.agent import generate_offer


config = NegotiationConfig(
    item="Website design",
    opening_offer=300,
    target_price=400,
    max_budget=500,
)

offer = generate_offer(config)

print("\nNEGOTIATEAI - OPENING OFFER")
print("-" * 40)
print(offer)