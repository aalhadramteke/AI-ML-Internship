# Async API Practice

FastAPI example comparing a synchronous baseline (v1) with async endpoints and a background email task (v2).

## Run locally

From PowerShell:

```powershell
Set-Location 'C:\Linkific\Day 21'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Interactive API documentation: <http://127.0.0.1:8000/docs>  
OpenAPI specification: <http://127.0.0.1:8000/openapi.json> (an exported copy is in `openapi.json`).

Run the 100-request, concurrency-100 report benchmark in another PowerShell window:

```powershell
Set-Location 'C:\Linkific\Day 21'
python benchmark.py
```

## Endpoints

| Method | Path | Behavior |
|---|---|---|
| GET | `/api/v1/report/{item_id}` | Sync baseline; simulates database and external I/O sequentially. |
| GET | `/api/v2/report/{item_id}` | Async; overlaps the simulated I/O calls with `asyncio.gather`. |
| POST | `/api/v1/orders` | Sync; waits for the simulated email operation before returning 201. |
| POST | `/api/v2/orders` | Async; schedules the simulated email operation with `BackgroundTasks` and returns 201. |

Both order endpoints accept a JSON body with `item` (string, 2–50 characters) and `quantity` (integer, 1–100). Invalid input returns 422.

Responses include `X-Process-Time-ms` and `X-Request-ID` headers. The benchmark results and limitations are documented in [report.md](report.md).
