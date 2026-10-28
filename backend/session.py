from pydantic import BaseModel, Field

from backend.negotiation import NegotiationConfig


class NegotiationMessage(BaseModel):
    role: str
    content: str


class NegotiationSession(BaseModel):
    config: NegotiationConfig
    messages: list[NegotiationMessage] = Field(default_factory=list)
    round_number: int = 0

    def add_message(self, role: str, content: str):
        self.messages.append(
            NegotiationMessage(
                role=role,
                content=content,
            )
        )

    def get_history(self):
        return [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in self.messages
        ]