# --- Builder stage ---
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Runtime stage ---
FROM python:3.11-slim

RUN useradd appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

RUN mkdir -p data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

CMD ["sh", "-c", "python etl.py load data/orders.csv && uvicorn etl.app:app --host 0.0.0.0 --port 8000"]
