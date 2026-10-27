import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from backend.negotiation import (
    NegotiationConfig,
    NegotiationOffer,
    validate_offer,
)


# Load environment variables
load_dotenv()


# Initialize Meta model client through Baseten
client = OpenAI(
    base_url=os.getenv("BASETEN_BASE_URL"),
    api_key=os.getenv("BASETEN_API_KEY"),
)


# Generate the opening negotiation message
def generate_offer(config: NegotiationConfig) -> str:

    response = client.chat.completions.create(
        model=os.getenv("BASETEN_MODEL"),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are NegotiateAI, a professional negotiation assistant. "
                    "Your task is to negotiate the best possible price for the buyer. "
                    "Be polite, persuasive, and concise. "
                    "Never invent facts, market prices, competing offers, "
                    "previous conversations, or promises of future business. "
                    "Only use information explicitly provided by the user. "
                    "Never propose a price above the maximum budget. "
                    "Do not accept or finalize any agreement."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Item: {config.item}\n"
                    f"Opening offer: ${config.opening_offer}\n"
                    f"Target price: ${config.target_price}\n"
                    f"Maximum budget: ${config.max_budget}\n"
                    "Generate an opening negotiation message."
                ),
            },
        ],
        max_tokens=1000,
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError("AI returned an empty opening offer.")

    return content


# Generate a counteroffer with budget validation
def generate_safe_counteroffer(
    config: NegotiationConfig,
    seller_message: str,
) -> NegotiationOffer:

    response = client.chat.completions.create(
        model=os.getenv("BASETEN_MODEL"),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are NegotiateAI, a buyer-side negotiation agent. "
                    "Your task is to negotiate the best possible price. "
                    "Be polite, professional, and concise. "
                    "Never invent facts, market prices, competing offers, "
                    "previous conversations, or promises of future business. "
                    "Never accept or finalize an agreement. "
                    "Never propose an amount above the maximum budget. "
                    "Return ONLY valid JSON with exactly two fields: "
                    "'amount' (number) and 'message' (string). "
                    "The message must contain the exact amount from the amount field. "
                    "Do not include any other monetary amounts. "
                    "Do not include markdown formatting or code fences."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Item: {config.item}\n"
                    f"Opening offer: ${config.opening_offer}\n"
                    f"Target price: ${config.target_price}\n"
                    f"Maximum budget: ${config.max_budget}\n"
                    f"Seller message: {seller_message}\n"
                    "Generate the next counteroffer."
                ),
            },
        ],
        max_tokens=1000,
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError("AI returned an empty counteroffer.")

    # Convert AI response from JSON into Python dictionary
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "AI returned invalid JSON."
        ) from exc

    # Validate the structure of the AI response
    offer = NegotiationOffer.model_validate(data)

    # Check the proposed amount against the maximum budget
    if not validate_offer(offer, config):
        raise ValueError(
            f"Offer ${offer.amount} exceeds maximum budget ${config.max_budget}."
        )

    # Check that the message contains the validated amount
    expected_amount = f"${offer.amount:g}"

    if expected_amount not in offer.message:
        raise ValueError(
            "Counteroffer message does not contain the validated amount."
        )

    return offer