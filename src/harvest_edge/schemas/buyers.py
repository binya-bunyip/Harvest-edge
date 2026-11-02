from pydantic import BaseModel, ConfigDict, Field


class BuyerFields(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=30)


class BuyerCreate(BuyerFields):
    pass


class BuyerUpdate(BuyerFields):
    pass


class BuyerRead(BuyerFields):
    model_config = ConfigDict(from_attributes=True)

    id: int
