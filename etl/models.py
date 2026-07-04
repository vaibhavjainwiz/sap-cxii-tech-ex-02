from pydantic import BaseModel


class Order(BaseModel):
    order_id: str
    customer_id: str
    order_date: str
    amount: float
    currency: str


class OrderStats(BaseModel):
    total_revenue: float
    avg_order_value: float
    orders_per_day: dict[str, int]
