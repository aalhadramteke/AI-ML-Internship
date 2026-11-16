from pydantic import BaseModel, Field

class OrderIn(BaseModel):
    item: str = Field(min_length=2, max_length=50)
    quantity: int = Field(gt=0, le=100)