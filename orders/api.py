from datetime import datetime, timedelta, timezone
import pandas as pd
from orders import db
from orders.models import Order, OrderStats


def save_orders(df: pd.DataFrame):
    """Validate and persist a DataFrame of orders."""
    required = {"order_id", "customer_id", "order_date", "amount", "currency"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    db.save_orders(df)


def get_orders_by_customer(customer_id: str) -> list[Order]:
    """Return all orders for a customer."""
    return db.find_orders_by_customer(customer_id)


def get_order_stats() -> OrderStats:
    """Return aggregate order statistics."""
    return db.get_order_stats()


def get_recent_orders(days: int) -> list[Order]:
    """Return orders placed within the last N days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    return db.find_recent_orders(cutoff)
