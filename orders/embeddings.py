import logging

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

from orders import db, vector_store

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Lazy-load and cache the sentence-transformer model."""
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s", MODEL_NAME)
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _order_to_text(row: dict) -> str:
    """Format an order row as a text string for embedding."""
    return f"customer {row['customer_id']}, ${row['amount']:.2f} USD, {row['order_date']}"


def build_index(df: pd.DataFrame) -> None:
    """Encode order records and persist to the vector store."""
    logger.info("Building semantic search index...")

    if df.empty:
        logger.warning("Empty DataFrame — skipping index build")
        return

    order_ids = df["order_id"].tolist()
    texts = [
        _order_to_text(row) for row in df[["customer_id", "amount", "order_date"]].to_dict("records")
    ]

    model = _get_model()
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    vecs = np.array(vecs, dtype=np.float32)

    vector_store.save(order_ids, vecs)


def load_index() -> None:
    """Load a previously built index from the vector store."""
    vector_store.load()


def search(query: str, top_k: int = 5) -> list[dict]:
    """Return top-k orders most similar to the free-text query."""
    model = _get_model()
    q_vec = model.encode([query], normalize_embeddings=True)
    q_vec = np.array(q_vec, dtype=np.float32)

    matched = vector_store.query(q_vec, top_k)

    if not matched:
        return []

    orders_by_id = db.find_orders_by_ids([oid for oid, _ in matched])

    results = []
    for order_id, score in matched:
        order = orders_by_id.get(order_id)
        if order is None:
            continue
        results.append({
            "order_id": order.order_id,
            "customer_id": order.customer_id,
            "amount_usd": order.amount,
            "order_date": order.order_date,
            "score": score,
        })
    return results
