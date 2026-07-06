import json
import logging
import os
import threading

import faiss
import numpy as np

from orders.config import FAISS_INDEX_PATH, FAISS_RECORDS_PATH

logger = logging.getLogger(__name__)

_index: faiss.IndexFlatIP | None = None
_order_ids: list[str] = []
_lock = threading.Lock()


def save(order_ids: list[str], vectors: np.ndarray) -> None:
    """Persist order IDs and their embedding vectors to disk."""
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)

    os.makedirs(os.path.dirname(FAISS_INDEX_PATH) or ".", exist_ok=True)
    faiss.write_index(index, FAISS_INDEX_PATH)
    with open(FAISS_RECORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(order_ids, f)

    logger.info("Vector store saved: %d records, dim=%d", len(order_ids), dim)


def load() -> None:
    """Load a previously saved index and order ID mapping from disk."""
    global _index, _order_ids

    if not os.path.exists(FAISS_INDEX_PATH) or not os.path.exists(FAISS_RECORDS_PATH):
        logger.warning("No pre-built index found at %s — vector search unavailable", FAISS_INDEX_PATH)
        return

    logger.info("Loading vector store from disk...")
    index = faiss.read_index(FAISS_INDEX_PATH)
    with open(FAISS_RECORDS_PATH, encoding="utf-8") as f:
        order_ids = json.load(f)

    with _lock:
        _index = index
        _order_ids = order_ids

    logger.info("Vector store loaded: %d records", len(order_ids))


def query(vector: np.ndarray, top_k: int = 5) -> list[tuple[str, float]]:
    """Return top-k (order_id, score) pairs nearest to the query vector."""
    with _lock:
        index = _index
        order_ids = _order_ids

    if index is None or not order_ids:
        return []

    k = min(top_k, len(order_ids))
    scores, indices = index.search(vector, k)

    return [
        (order_ids[idx], round(float(score), 4))
        for score, idx in zip(scores[0], indices[0])
    ]
