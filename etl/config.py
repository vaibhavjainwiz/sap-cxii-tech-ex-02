import os

EXCHANGE_RATE = {
    "USD":1.0,
    "EUR":1.1
}

DB_PATH = os.getenv("DB_PATH", "data/orders.db")
TABLE_NAME = "orders"