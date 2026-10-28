import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from backend.negotiation import (
    NegotiationConfig,
    NegotiationOffer,
    validate_offer,
)
from backend.session import NegotiationSession


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
        max_tokens=3000,
    )

    # Extract model response
    choice = response.choices[0]
    content = choice.message.content

    # Debug empty opening offers
    if not content:
        print(
            "DEBUG - Opening offer finish reason:",
            choice.finish_reason,
        )
        print(
            "DEBUG - Opening offer token usage:",
            response.usage,
        )

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
        raise ValueError("AI returned invalid JSON.") from exc

    # Validate the structure of the AI response
    offer = NegotiationOffer.model_validate(data)

    # Check the proposed amount against the maximum budget
    if not validate_offer(offer, config):
        raise ValueError(
            f"Offer ${offer.amount} exceeds maximum budget ${config.max_budget}."
        )

    # Build the final message using only the validated amount
    safe_message = (
        f"Thank you for your response. "
        f"I would like to offer ${offer.amount:g} "
        f"for {config.item}. "
        f"Would you be willing to consider this price?"
    )

    return NegotiationOffer(
        amount=offer.amount,
        message=safe_message,
    )


# Generate a counteroffer using negotiation history
def generate_counteroffer_with_memory(
    session: NegotiationSession,
    seller_message: str,
) -> NegotiationOffer:

    config = session.config

    # Build negotiation history
    history = "\n".join(
        f"{message.role}: {message.content}"
        for message in session.messages
    )

    response = client.chat.completions.create(
        model=os.getenv("BASETEN_MODEL"),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are NegotiateAI, a buyer-side negotiation agent. "
                    "Use the negotiation history to decide your next offer. "
                    "Your goal is to negotiate the lowest reasonable price. "
                    "Never invent facts or promises. "
                    "Never accept or finalize an agreement. "
                    "Never exceed the maximum budget. "
                    "Return ONLY valid JSON with two fields: "
                    "'amount' (number) and 'message' (string). "
                    "Do not include markdown or code fences."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Item: {config.item}\n"
                    f"Opening offer: ${config.opening_offer}\n"
                    f"Target price: ${config.target_price}\n"
                    f"Maximum budget: ${config.max_budget}\n\n"
                    f"Negotiation history:\n{history}\n\n"
                    f"Latest seller message: {seller_message}\n"
                    "Generate the next counteroffer."
                ),
            },
        ],
        max_tokens=3000,
    )

    # Extract model response
    choice = response.choices[0]
    content = choice.message.content

    # Debug empty responses
    if not content:
        print(
            "DEBUG - Counteroffer finish reason:",
            choice.finish_reason,
        )
        print(
            "DEBUG - Counteroffer token usage:",
            response.usage,
        )

        raise ValueError("AI returned an empty response.")

    # Parse JSON response
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("AI returned invalid JSON.") from exc

    # Validate AI offer
    offer = NegotiationOffer.model_validate(data)

    # Enforce maximum budget
    if not validate_offer(offer, config):
        raise ValueError("Counteroffer exceeds maximum budget.")

    # Python constructs the final message using validated amount
    safe_message = (
        f"Thank you for your response. "
        f"I would like to offer ${offer.amount:g}. "
        f"Would you consider this price?"
    )

    return NegotiationOffer(
        amount=offer.amount,
        message=safe_message,
    )