import os

EXCHANGE_RATE = {
    "USD":1.0,
    "EUR":1.1
}

DB_PATH = os.getenv("DB_PATH", "data/orders.db")
TABLE_NAME = "orders"
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "data/orders.faiss")
FAISS_RECORDS_PATH = os.getenv("FAISS_RECORDS_PATH", "data/orders_records.json")