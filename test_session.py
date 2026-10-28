from backend.negotiation import NegotiationConfig
from backend.session import NegotiationSession

config = NegotiationConfig(
    item="Website design",
    opening_offer=300,
    target_price=400,
    max_budget=500,
)

session = NegotiationSession(config=config)

session.add_message(
    role="buyer",
    content="I would like to offer $300."
)

session.add_message(
    role="seller",
    content="My price is $600."
)

session.add_message(
    role="buyer",
    content="Would you consider $350?"
)

print("\nNEGOTIATEAI - NEGOTIATION HISTORY")
print("-" * 40)

for message in session.get_history():
    print(f"{message['role']}: {message['content']}")

print(f"\nTotal messages: {len(session.messages)}")