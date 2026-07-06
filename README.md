# Technical Exercise — sap-cxii-tech-ex-02

This repository contains an ETL pipeline, a FastAPI service, and a Kubernetes deployment architecture for a data microservice that ingests customer order data, exposes it via a query API, and augments it with AI capabilities (NL→SQL and Semantic Search).

## Setup Instructions

### Prerequisites
- Python 3.10+
- Docker & Docker Compose (optional, for containerized run)
- Kubernetes cluster (optional, for `k8s/` deployment)

### 1. Local Development Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Running the ETL Pipeline
The ETL pipeline processes raw CSV data, normalizes currencies to USD, builds a SQLite database, and generates the FAISS vector index for semantic search.
```bash
python etl.py load data/orders.csv
```

### 3. Running the FastAPI Service
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```
The API documentation will be available at `http://localhost:8000/docs`.

### 4. Running via Docker
```bash
docker build -t orders-api .
docker run -p 8000:8000 -v $(pwd)/data:/app/data orders-api
```

---

## Design Notes

- **ETL (`etl.py`)**: Uses `pandas` to clean and normalize the CSV data. Stores the relational data in a SQLite database and builds a FAISS `IndexFlatIP` vector store using `sentence-transformers` (`all-MiniLM-L6-v2`) for semantic search capabilities.
- **API (`app.py`)**: Implements endpoints for customer lookups, stats aggregation, recent orders, natural language querying (NL→SQL), and semantic search.
- **AI Integration**:
  - **NL→SQL**: Uses `gpt-4o-mini` (via OpenAI SDK). Includes a robust single-retry loop that catches SQL execution errors and prompts the LLM to correct its mistake.
    - **Model Choice**: `gpt-4o-mini` was chosen for its excellent balance of low latency, cost-efficiency, and strong zero-shot SQL generation capabilities on simple schemas.
    - **System Prompt**:
      ```text
      You are a SQL assistant. You translate natural language questions into SQLite SQL queries.

      You have access to the following database schema:
      Table: orders
      Columns:
        - order_id (TEXT) — unique order identifier
        - customer_id (TEXT) — alphanumeric customer ID
        - order_date (TEXT) — ISO 8601 date (YYYY-MM-DD)
        - amount (REAL) — order amount in USD (all amounts are already converted to USD)
        - currency (TEXT) — original currency code (USD or EUR)

      Rules:
      1. Return ONLY a valid SQLite SELECT query — no markdown, no explanation, no backticks.
      2. Use only the columns listed above. If the question asks about data not in the schema, respond with exactly: UNANSWERABLE
      3. Use standard SQLite functions (e.g., date(), strftime()) for date arithmetic.
      4. Never use INSERT, UPDATE, DELETE, DROP, ALTER, or any DDL/DML statements.
      5. "Last N days" means order_date >= date('now', '-N days').

      Respond ONLY with JSON matching this schema:
      {
        "out_of_scope": boolean,
        "reason": string | null,
        "sql": string | null
      }
      ```
    - **Retry Loop Example**:
      - *Question*: "Show me orders from the last month"
      - *Bad SQL Generated*: `SELECT * FROM orders WHERE order_date >= current_date - interval '1 month'`
      - *Error*: `near "interval": syntax error` (SQLite does not support interval syntax)
      - *Corrected SQL*: `SELECT * FROM orders WHERE order_date >= date('now', '-1 month')`
  - **Semantic Search**: Uses local `sentence-transformers` (`all-MiniLM-L6-v2`) to generate embeddings.
    - **Model Choice**: `all-MiniLM-L6-v2` was chosen because it produces small (384-dim) vectors and executes extremely fast on CPU, making it perfect for embedding short, structured text (like an order summary) without needing a GPU.
    - **Index Rebuild Strategy**: Currently, the FAISS index is written to disk by `etl.py` and then loaded into memory by `app.py`. There is a known gap: if `etl.py` runs while `app.py` is running, the API must be restarted to pick up the new FAISS index, meaning rebuilds currently require a deployment cycle/pod restart.

---

## Part 4d — Architectural Extension

### Clarification Required

1. **Data Volume & Query Frequency**: What is the expected dataset size (number of orders) per tenant, and what is the expected queries per second (QPS)? (Determines if in-memory FAISS is scalable or if a distributed Vector DB is required to handle throughput).
2. **Update Frequency**: How often does ETL run? (Impacts the zero-downtime index rebuild strategy and cache invalidation).
3. **Local Cloud Constraints**: Is the environment air-gapped? Are managed services (DBs, object storage) available, or is it strictly bare-metal Kubernetes?
4. **PII Strategy**: Should PII be permanently redacted, or reversibly tokenized so the final answer can include the real customer IDs?
5. **GPU Footprint**: For on-premise LLMs, what is the available compute/GPU capacity? (This affects whether we deploy a small proxy model or a massive 70B parameter model).

### Assumptions

1. **Connected Kubernetes Environment**: We assume all environments (EU, US, Local Cloud) run a connected (non-air-gapped) Kubernetes cluster.
2. **Massive Data Volume, High QPS**: We assume data volume per tenant is massive (up to 1 Billion orders), and query volume is high (e.g., >500 QPS per tenant).
3. **Reversible Tokenization for PII**: We assume the business requires full fidelity in the final answer (e.g., showing the actual customer ID). Therefore, PII must be reversibly tokenized before the LLM step, rather than permanently redacted.
4. **ETL is a batch process**: We assume data ingestion happens in scheduled batches (e.g., nightly or hourly) rather than continuous streaming.
5. **LLM Abstraction via Gateway**: We assume all LLMs (cloud APIs or local deployments) are exposed via an OpenAI-compatible REST API. This allows the application to remain agnostic to the actual model backend.

### Compute: Network & Storage

**1. Network**
To ensure sufficient bandwidth between the API tier, LLM Gateway, and Database tier, we calculate the network load based on our high QPS assumption (>500 QPS per tenant):
- **API to Database (SQL/Vector) Egress**: 500 QPS × 2 KB = 1 MB/s per tenant. Total ~50 MB/s.
- **API to LLM Gateway Egress**: 500 QPS × 2 KB (550 tokens) = 1 MB/s per tenant. Total ~50 MB/s.
**Conclusion**: The system is NOT network I/O bound. The primary bottleneck will be **Compute (CPU/GPU)** inside the LLM Gateway.

**2. Storage**
Calculated for **up to 1 Billion orders per tenant**:
- **Relational Database (PostgreSQL)**: 1 Billion rows × 150 bytes ≈ **150 GB per tenant**. Total ~**7.5 TB**.
- **Vector Database (Milvus/Qdrant)**: 1 Billion vectors × ~2,000 bytes (data + index) ≈ **2 TB per tenant**. Total ~**100 TB**.
**Conclusion**: At this scale (2 TB of vector data per tenant), we cannot rely purely on RAM for vector search. We must configure our Vector DB to use **DiskANN** or memory-mapped files (mmap) with NVMe SSDs to serve queries directly from disk.

### Database Design

To support 50 enterprise customers with strict data residency and isolation requirements, we will migrate from SQLite to **PostgreSQL** for structured data, and migrate from in-memory FAISS to **Milvus** (or Qdrant) for the distributed vector store. We intentionally decouple the relational store from the vector store to allow independent horizontal scaling of the read-heavy semantic search tier.

### Architectural Decisions (Q&A)

**1. Tenant isolation for the vector index**
**Decision**: One index (Collection) per tenant within a distributed Vector DB (e.g., Milvus), segregated by geographic region.
- **Data-Leakage**: Structurally guarantees zero leakage. A shared index relies on application-layer filtering (`WHERE tenant_id = X`), where a single bug can expose cross-tenant PII. Collection-per-tenant enforces isolation at the connection/routing level.
- **Latency**: Faster exact-search latency. Queries execute against a smaller, targeted index rather than scanning and post-filtering a massive global index.
- **Memory**: The trade-off is higher memory overhead. Given our high volume assumption (1B orders/tenant), this overhead is an acceptable security premium.

**2. LLM backend per tenant & Routing**
**Decision**: Decentralized routing via a Service Mesh (Istio) sidecar proxy.
- **Where routing lives**: The FastAPI application blindly makes standard OpenAI SDK calls to `localhost`. An Envoy sidecar intercepts this egress traffic. Istio `VirtualService` rules dynamically route the traffic based on the `tenant_id` header—sending EU tenants to Azure OpenAI and KSA tenants to an internal Kubernetes service hosting a private model (e.g., vLLM).
- **Model-agnostic prompt layer**: The application code remains 100% agnostic. Because all backends (Azure, OpenAI, vLLM, Ollama) expose an OpenAI-compatible REST API, the application's prompt templates and parsing logic require zero modification regardless of where the sidecar routes the request.

**3. PII in the NL→SQL pipeline**
**Decision**: Reversible tokenization via WebAssembly (Wasm) Envoy Filters.
- **Guardrails**: A lightweight Wasm plugin runs inside the Envoy sidecar. It intercepts outbound JSON payloads, detects PII (Customer IDs), and replaces them with secure UUID tokens (e.g., `<TOK_123>`) before forwarding to the LLM. It then intercepts the LLM's SQL response and detokenizes it before returning it to the application.
- **Cloud vs. On-Premise impact**: The answer absolutely changes based on the backend. For third-party Cloud APIs, this tokenization is **mandatory** to prevent PII egress over the internet. For an on-premise local Llama model running inside the same secure Kubernetes boundary, the tokenization filter can be bypassed via Istio routing rules, allowing the local LLM to see the raw IDs and potentially generate higher-quality context without violating data residency.

**4. Highest-leverage decision & trade-off**
**Decision**: Decoupling the Relational Store (PostgreSQL) from the Vector Store (Milvus), rather than using unified storage like `pgvector`.
- **Leverage**: At our assumed scale of 1 Billion orders per tenant, this separation is the highest-leverage choice. It allows the read-heavy semantic search tier to scale horizontally (and utilize memory-mapped NVMe disks for 2TB vector graphs) entirely independently from the transactional database handling heavy ETL writes and SQL aggregations. 
- **Trade-off accepted**: We accepted significantly higher operational complexity. We must now maintain, monitor, and upgrade two massive distributed database clusters (PostgreSQL + Milvus) and engineer complex ETL pipelines to keep their states eventually consistent, abandoning the simplicity of single-transaction unified ACID commits that `pgvector` would have provided.
