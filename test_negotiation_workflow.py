from backend.negotiation import NegotiationConfig
from backend.session import NegotiationSession
from backend.agent import generate_counteroffer_with_memory
from backend.approval import ApprovalDecision, process_approval


config = NegotiationConfig(
    item="Website design",
    opening_offer=300,
    target_price=400,
    max_budget=500,
)

session = NegotiationSession(config=config)

# Previously approved opening offer
session.add_message("buyer", "I would like to offer $300.")

print("\nNEGOTIATEAI - NEGOTIATION WORKFLOW")
print("-" * 45)

# Seller responds
seller_message = "My price is $600."

print("\nSeller:", seller_message)

# AI generates a proposal
ai_offer = generate_counteroffer_with_memory(
    session,
    seller_message,
)

print("\nAI proposed:", ai_offer.message)

# Human reviews the proposal
print("\nChoose an action:")
print("1 - APPROVE")
print("2 - REJECT")
print("3 - MODIFY")

choice = input("\nYour choice (1/2/3): ").strip()

if choice == "1":
    decision = ApprovalDecision(action="APPROVE")

elif choice == "2":
    decision = ApprovalDecision(action="REJECT")

elif choice == "3":
    new_amount = float(input("Enter your new offer amount: "))
    decision = ApprovalDecision(
        action="MODIFY",
        modified_amount=new_amount,
    )

else:
    raise ValueError("Invalid choice.")

# Validate human decision
approved_offer = process_approval(
    ai_offer,
    decision,
    config,
)

# Record seller's message
session.add_message("seller", seller_message)

if approved_offer is None:
    print("\nOffer rejected. Nothing was sent.")

else:
    # Simulate sending the approved offer
    print("\nAPPROVED OFFER:")
    print(approved_offer.message)

    # In this test, record the simulated sent message
    session.add_message("buyer", approved_offer.message)
    session.round_number += 1

print("\nNEGOTIATION HISTORY")
print("-" * 45)

for message in session.get_history():
    print(f"{message['role']}: {message['content']}")

print(f"\nCompleted rounds: {session.round_number}")