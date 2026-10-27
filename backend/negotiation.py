from pydantic import BaseModel, Field, model_validator


class NegotiationConfig(BaseModel):
    item: str = Field(min_length=1)
    target_price: float = Field(gt=0)
    max_budget: float = Field(gt=0)
    opening_offer: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_budget(self):
        if self.opening_offer > self.target_price:
            raise ValueError("Opening offer cannot exceed target price.")

        if self.target_price > self.max_budget:
            raise ValueError("Target price cannot exceed maximum budget.")

        return self


class NegotiationOffer(BaseModel):
    amount: float = Field(gt=0)
    message: str = Field(min_length=1)


def validate_offer(
    offer: NegotiationOffer,
    config: NegotiationConfig,
) -> bool:

    if offer.amount > config.max_budget:
        return False

    return True