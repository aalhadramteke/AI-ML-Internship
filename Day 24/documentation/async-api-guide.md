# Async API Practice: Sync vs Async Performance

A FastAPI project that compares a **synchronous API (v1)** with an **asynchronous API (v2)** and benchmarks the difference on I/O-bound endpoints.

## Features

| Concept | Where it's used |
|---|---|
| Async/await | v2 endpoints use `async def` and `await` |
| Concurrent I/O | `asyncio.gather` overlaps the DB and external-service calls |
| Background tasks | v2 sends the order email after the response via `BackgroundTasks` |
| Middleware | Adds `X-Process-Time-ms` and `X-Request-ID` to every response |
| Dependency injection | `Depends(get_db)` supplies the database service |
| Validation | Pydantic rejects invalid orders with HTTP 422 |
| API versioning | `/api/v1` (sync baseline) and `/api/v2` (async) |
| Benchmarking | `benchmark.py` compares both versions under concurrent load |

## Project Structure

```
.
├── app
│   ├── __init__.py
│   ├── main.py          # FastAPI app, middleware, versioned routers
│   ├── deps.py          # Database service (sync + async methods), get_db()
│   ├── middleware.py    # TimingMiddleware
│   ├── schemas.py       # OrderIn validation model
│   └── routers
│       ├── __init__.py
│       ├── v1.py        # Synchronous endpoints (baseline)
│       └── v2.py        # Asynchronous endpoints
├── benchmark.py         # Load test: v1 vs v2
├── requirements.txt
└── README.md
```

## Tech Stack

Python 3.10+, FastAPI, Uvicorn, HTTPX, Pydantic

## Getting Started

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

`requirements.txt`:
```
fastapi
uvicorn
httpx
```

### 2. Run the server
```bash
uvicorn app.main:app --port 8000
```

### 3. Open the docs
Swagger UI: http://localhost:8000/docs

## API Endpoints

| Method | Path | Version | Type | Behavior |
|---|---|---|---|---|
| GET | `/api/v1/report/{item_id}` | v1 | Sync | DB call, then external call, one after the other (~0.5 s) |
| GET | `/api/v2/report/{item_id}` | v2 | Async | Both calls run concurrently with `asyncio.gather` (~0.3 s) |
| POST | `/api/v1/orders` | v1 | Sync | Email is sent inline, so the response waits (~2 s) |
| POST | `/api/v2/orders` | v2 | Async | Email runs as a background task, so the response is immediate |

### Example request
```bash
curl -X POST http://localhost:8000/api/v2/orders \
  -H "Content-Type: application/json" \
  -d '{"item": "book", "quantity": 2}'
```

### Validation rules

| Field | Rule |
|---|---|
| `item` | string, 2-50 characters |
| `quantity` | integer, 1-100 |

Invalid input returns `422 Unprocessable Entity`.

### Response headers (all endpoints)

| Header | Meaning |
|---|---|
| `X-Process-Time-ms` | Server processing time in milliseconds |
| `X-Request-ID` | Short unique ID for the request |

## How It Works

**v1 (sync):** each request runs blocking calls (`time.sleep`) one after another, so a slow dependency holds the worker for the whole duration.

**v2 (async):**
- `await` hands control back to the event loop while waiting, so other requests keep being served.
- `asyncio.gather` runs independent calls at the same time, so total latency is the slowest call and not the sum.
- `BackgroundTasks` runs the email step after the response is sent.

## Benchmark

### Run it
Start the server in one terminal, then in another:
```bash
python benchmark.py
```

### Method
- 100 requests per version at concurrency 100
- 3 runs per version
- Endpoints tested: `GET /api/v1/report/1` and `GET /api/v2/report/1`
- Metrics: average latency, P95 latency, total time, throughput (req/s)
- Simulated I/O: 0.3 s DB call + 0.2 s external call

### Results

| Endpoint | Metric | v1 Sync | v2 Async | Improvement |
|---|---|---|---|---|
| GET /report/{id} | Avg latency (ms) | [value] | [value] | 50.3% lower |
| GET /report/{id} | P95 latency (ms) | [value] | [value] | [value] |
| GET /report/{id} | Total time (s) | [value] | [value] | [value] |
| GET /report/{id} | Throughput (req/s) | [value] | [value] | ~2.9x higher |
| POST /orders | Response time (ms) | [value] | [value] | [value] |

### Summary
- v2's average response time was **50.3% lower** and throughput about **2.9x higher** on the report endpoint.
- The gain comes from overlapping I/O waits and freeing the event loop.
- On the order endpoint, moving the email to a background task removes its delay from the response time.

### Note on the sync baseline
FastAPI runs plain `def` endpoints in a thread pool (about 40 threads by default), so v1 is not fully serialized. The gap between v1 and v2 widens as concurrency exceeds the pool size.

## Limitations

- I/O is simulated with sleeps, not a real database or network.
- Client and server ran on the same machine with a single Uvicorn worker.
- Results demonstrate the concept and do not predict production performance.
- Async gives little benefit for CPU-bound work.

## API Documentation

- Interactive docs: `/docs` (Swagger UI) and `/redoc`
- OpenAPI spec: `/openapi.json`

## Author

Aalhad Ramteke
