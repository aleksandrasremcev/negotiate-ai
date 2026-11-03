
# NegotiateAI

**An AI-powered negotiation agent built with Meta Muse Spark Open for the Meta Global AI Developer Hackathon 2026.**

NegotiateAI helps buyers negotiate prices through structured, multi-round conversations while keeping users in control of important decisions.

Unlike a general-purpose chatbot, NegotiateAI follows a defined negotiation workflow, maintains conversation history, validates proposed offers against buyer-defined limits, and requires explicit human confirmation before finalizing an agreement.

## The Problem

Negotiating prices can be time-consuming, stressful, and difficult for people who lack negotiation experience.

AI can help buyers formulate offers and respond to sellers, but autonomous negotiation also introduces risks: exceeding budgets, making unauthorized commitments, or misunderstanding a seller's response.

## The Solution

NegotiateAI combines AI-generated negotiation strategies with deterministic validation and human oversight.

Users configure their negotiation parameters, including the item, opening offer, target price, maximum budget, negotiation mode, and maximum number of rounds.

The application then guides the negotiation through a controlled workflow.

## Key Features

- **AI-powered counteroffers:** Uses Meta Muse Spark Open to generate context-aware negotiation messages.
- **Multi-round negotiation:** Maintains conversation history and adapts counteroffers based on seller responses.
- **Manual mode:** Requires user approval before recording each proposed offer.
- **Autonomous mode:** Automatically approves generated offers within predefined constraints.
- **Budget protection:** Validates proposed amounts against the buyer's maximum budget.
- **Human-in-the-loop final approval:** Requires explicit confirmation before marking an agreement as completed.
- **Outcome detection:** Handles seller acceptance, rejection, ambiguous responses, and budget-limit conditions.
- **Negotiation limits:** Enforces a maximum number of negotiation rounds.
- **Safety guardrails:** Validates AI-generated messages and prevents certain unauthorized agreement statements.

## How It Works

1. The buyer creates a negotiation and defines their budget and preferences.
2. NegotiateAI prepares an opening offer.
3. The seller's response is entered into the application.
4. The backend evaluates the response.
5. When a counteroffer is needed, Meta Muse Spark Open generates a proposed amount and message using the negotiation history.
6. The backend validates the proposed offer.
7. The offer is approved manually or automatically, depending on the selected mode.
8. If the seller accepts, the buyer must explicitly confirm the final agreement.

**Important:** NegotiateAI does not contact external sellers, execute payments, or complete real-world purchases. Agreements are recorded locally within the application.

## Meta AI Integration

NegotiateAI uses **Meta Muse Spark Open**, an open-weight model accessed through Baseten's OpenAI-compatible inference API.

Model identifier:

`meta-models/muse-spark-open-1026`

The model generates negotiation messages and counteroffers. The Python backend independently validates outputs and controls negotiation state transitions.

This separation between AI-generated proposals and deterministic enforcement is central to NegotiateAI's architecture.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | Python, FastAPI |
| AI Model | Meta Muse Spark Open |
| Inference Provider | Baseten |
| API Integration | OpenAI-compatible Python SDK |
| Data Validation | Pydantic |
| Testing | Pytest |

## Architecture

```text
React Frontend
      |
      v
FastAPI Backend
      |
      +-- Negotiation Session Management
      |
      +-- Seller Response / Outcome Detection
      |
      +-- Meta Muse Spark Open (via Baseten)
      |
      +-- Offer Validation and Safety Guardrails
      |
      +-- Human Approval Workflow
```

## Running Locally

### Backend

Clone the repository:

```bash
git clone https://github.com/aleksandrasremcev/negotiate-ai.git
cd negotiate-ai
```

Create and activate a Python virtual environment, then install dependencies:

```bash
pip install -r requirements.txt
```

Configure the following environment variables in a `.env` file:

```env
BASETEN_BASE_URL=https://inference.baseten.co/v1
BASETEN_API_KEY=your_api_key
BASETEN_MODEL=meta-models/muse-spark-open-1026
```

Never commit API keys or `.env` files to version control.

Start the backend:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

### Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL displayed by Vite.

## Testing

Run the automated backend tests without the optional live-model scripts:

```bash
python -m pytest -q --ignore=test_agent.py --ignore=test_multi_round.py
```

The latest local verification completed **29 passing tests**.

Build the frontend:

```bash
cd frontend
npm run build
```

## Current Limitations

- Negotiation sessions are stored in memory and are lost when the backend restarts.
- Seller responses are entered manually; no external marketplace or messaging integration is implemented.
- AI inference requires access to the configured Baseten model.
- The application is a hackathon prototype, not a production transaction platform.

## Hackathon

**Event:** Meta Global AI Developer Hackathon 2026

**Track:** Indie Developer

**Project:** NegotiateAI

**Built during:** October 26 – November 4, 2026

**Developer:** Aleksandra Sremcev

## Demo

A demonstration video will be added as part of the hackathon submission.

