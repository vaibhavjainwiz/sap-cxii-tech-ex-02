import logging
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query

from orders import api, embeddings, nlq
from orders.models import Order, OrderStats, SemanticSearchResult
from orders.models_nlq import AskRequest, AskResponse

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Order API")


@app.on_event("startup")
def startup_load_index():
    embeddings.load_index()


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/orders/customer/{customer_id}")
def order_by_customer(customer_id: str) -> list[Order]:
    orders = api.get_orders_by_customer(customer_id)
    if not orders:
        raise HTTPException(status_code=404, detail=f"No orders found for {customer_id}")
    return orders


@app.get("/orders/stats")
def order_stats() -> OrderStats:
    return api.get_order_stats()


@app.get("/orders/recent")
def recent_orders(days: Annotated[int, Query(ge=1)]) -> list[Order]:
    return api.get_recent_orders(days)


@app.post("/orders/ask")
def ask_orders(req: AskRequest) -> AskResponse:
    result = nlq.ask(req.question)
    if "error" in result:
        if result["error"] == "unanswerable":
            raise HTTPException(status_code=400, detail=result["detail"])
        raise HTTPException(status_code=500, detail=result["detail"])
    return AskResponse(**result)


@app.get("/orders/semantic_search")
def semantic_search(
    q: Annotated[str, Query(min_length=1)],
    top_k: Annotated[int, Query(ge=1, le=100)] = 5,
) -> list[SemanticSearchResult]:
    return [SemanticSearchResult(**r) for r in embeddings.search(q, top_k)]
