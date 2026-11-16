# Async API benchmark report

## Setup and method

- Date: 2026-11-16
- FastAPI app served by one local uvicorn worker on `127.0.0.1:8000`.
- `benchmark.py` sent 100 GET requests at concurrency 100 to each report endpoint, measuring client-side latency.
- Report calls simulate 0.3 s of database I/O and 0.2 s of external I/O. v1 performs them sequentially; v2 overlaps them with `asyncio.gather`.
- Three runs were completed. Values below are milliseconds except total duration and throughput.

## Results

| Version | Run | Avg (ms) | P95 (ms) | Total (s) | Req/s |
|---|---:|---:|---:|---:|---:|
| v1 sync | 1 | 1192 | 1850 | 2.00 | 50.1 |
| v1 sync | 2 | 1353 | 1880 | 2.09 | 47.9 |
| v1 sync | 3 | 1239 | 1808 | 2.03 | 49.2 |
| **v1 sync** | **Mean** | **1261** | **1846** | **2.04** | **49.1** |
| v2 async | 1 | 705 | 765 | 0.83 | 120.9 |
| v2 async | 2 | 510 | 528 | 0.56 | 177.5 |
| v2 async | 3 | 664 | 730 | 0.78 | 128.0 |
| **v2 async** | **Mean** | **626** | **674** | **0.72** | **142.1** |

Across the three runs, v2 reduced mean response latency by **50.3%** and P95 latency by **63.5%**. Mean throughput increased by **189.7%**. These measurements vary between runs and apply only to this local simulated workload.

One additional local `curl.exe` measurement returned v1 `POST /orders` in 2.01 s and v2 in 4 ms; another v2 sample was 23 ms. Both valid requests returned 201, and an invalid order returned 422. v1 waits for the simulated 2 s email operation; v2 schedules it as a FastAPI background task and returns without waiting for it.

## Observations and limitations

- `asyncio.gather` overlaps the two independent simulated I/O calls in v2.
- Sync endpoints execute in a finite worker-thread pool, so heavy concurrent load can queue sync work. Results depend on the runtime and its thread-pool configuration.
- v2's email task runs in-process after the response; `BackgroundTasks` is not a durable job queue.
- I/O is simulated, all requests ran on one machine, and uvicorn used one worker. These results do not predict production performance.

## Conclusion

For this I/O-bound example, the async report endpoint completed the concurrent benchmark faster and with higher throughput. The v2 order endpoint also returned before the simulated email work completed. Real services should be benchmarked with representative dependencies and deployment settings.
