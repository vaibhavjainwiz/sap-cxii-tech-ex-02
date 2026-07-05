from pydantic import BaseModel, Field
from typing import Any


class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=5,
        examples=["What is the total revenue from customer C001 in the last 30 days?"],
    )


class AskResponse(BaseModel):
    answer: str
    sql_used: str
    rows: list[dict[str, Any]] = []
    token_count: int = 0
