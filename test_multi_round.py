from backend.negotiation import NegotiationConfig
from backend.session import NegotiationSession
from backend.agent import generate_counteroffer_with_memory


# Negotiation settings
config = NegotiationConfig(
    item="Website design",
    opening_offer=300,
    target_price=400,
    max_budget=500,
)

session = NegotiationSession(config=config)

# Initial buyer offer
session.add_message(
    role="buyer",
    content="I would like to offer $300."
)

# ROUND 1
print("\nROUND 1")
print("-" * 40)

seller_message = "My price is $600."

offer1 = generate_counteroffer_with_memory(
    session,
    seller_message,
)

session.add_message("seller", seller_message)
session.add_message("buyer", offer1.message)
session.round_number += 1

print(f"Seller: {seller_message}")
print(f"NegotiateAI: {offer1.message}")


# ROUND 2
print("\nROUND 2")
print("-" * 40)

seller_message = "I can lower my price to $550."

offer2 = generate_counteroffer_with_memory(
    session,
    seller_message,
)

session.add_message("seller", seller_message)
session.add_message("buyer", offer2.message)
session.round_number += 1

print(f"Seller: {seller_message}")
print(f"NegotiateAI: {offer2.message}")


# FINAL HISTORY
print("\nNEGOTIATION HISTORY")
print("-" * 40)

for message in session.get_history():
    print(f"{message['role']}: {message['content']}")

print(f"\nTotal rounds: {session.round_number}")