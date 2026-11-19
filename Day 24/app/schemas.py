from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class OrderIn(BaseModel):
    item: str = Field(min_length=2, max_length=50)
    quantity: int = Field(gt=0, le=100)


class ResearchIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=5, max_length=500, description="Research question")


class ResearchOut(BaseModel):
    query: str
    status: str
    report: str
    run_dir: Optional[str] = None
    log: List[str] = []
    duration_s: float
