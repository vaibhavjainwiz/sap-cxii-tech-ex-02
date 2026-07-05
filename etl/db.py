import sqlite3
import pandas as pd
from etl.config import DB_PATH, TABLE_NAME
from etl.models import Order, OrderStats


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def save_orders(df: pd.DataFrame):
    conn = _connect()
    df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
    conn.close()


def find_orders_by_customer(customer_id: str) -> list[Order]:
    conn = _connect()
    rows = conn.execute(
        f"SELECT * FROM {TABLE_NAME} WHERE customer_id = ?", (customer_id,)
    ).fetchall()
    conn.close()
    return [Order(**dict(r)) for r in rows]


def get_order_stats() -> OrderStats:
    conn = _connect()
    cur = conn.cursor()

    row = cur.execute(
        f"SELECT SUM(amount) AS total_revenue, AVG(amount) AS avg_order_value FROM {TABLE_NAME}"
    ).fetchone()

    orders_per_day = cur.execute(
        f"SELECT order_date, COUNT(*) AS count FROM {TABLE_NAME} GROUP BY order_date ORDER BY order_date"
    ).fetchall()

    conn.close()
    return OrderStats(
        total_revenue=round(row["total_revenue"], 2) if row["total_revenue"] else 0,
        avg_order_value=round(row["avg_order_value"], 2) if row["avg_order_value"] else 0,
        orders_per_day={r["order_date"]: r["count"] for r in orders_per_day},
    )


def find_recent_orders(cutoff_date: str) -> list[Order]:
    conn = _connect()
    rows = conn.execute(
        f"SELECT * FROM {TABLE_NAME} WHERE order_date >= ? ORDER BY order_date DESC",
        (cutoff_date,)
    ).fetchall()
    conn.close()
    return [Order(**dict(r)) for r in rows]


def execute_raw_sql(sql: str) -> list[dict]:
    conn = _connect()
    rows = conn.execute(sql).fetchall()
    conn.close()
    return [dict(r) for r in rows]
