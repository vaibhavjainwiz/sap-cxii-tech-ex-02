from pydantic import BaseModel, Field
from typing import Any


class Order(BaseModel):
    """Single order record."""

    order_id: str
    customer_id: str
    order_date: str
    amount: float
    currency: str


class OrderStats(BaseModel):
    """Aggregate order statistics."""

    total_revenue: float
    avg_order_value: float
    orders_per_day: dict[str, int]


class SemanticSearchResult(BaseModel):
    """Order result with similarity score."""

    order_id: str
    customer_id: str
    amount_usd: float
    order_date: str
    score: float


class AskRequest(BaseModel):
    """Natural-language question payload."""

    question: str = Field(
        ...,
        min_length=5,
        examples=["What is the total revenue from customer C001 in the last 30 days?"],
    )


class AskResponse(BaseModel):
    """Response containing the LLM-generated answer."""

    answer: str
    sql_used: str
    rows: list[dict[str, Any]] = []
    token_count: int = 0
