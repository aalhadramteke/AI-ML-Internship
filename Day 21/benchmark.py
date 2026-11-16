import asyncio
import statistics
import time
import httpx

BASE = "http://127.0.0.1:8000"
N = 100  # total requests
CONCURRENCY = 100  # simultaneous clients

async def hit(client, path, sem, lat):
    async with sem:
        t = time.perf_counter()
        r = await client.get(path)
        r.raise_for_status()
        lat.append((time.perf_counter() - t) * 1000)

async def run(path):
    lat, sem = [], asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient(base_url=BASE, timeout=120) as c:
        start = time.perf_counter()
        await asyncio.gather(*[hit(c, path, sem, lat) for _ in range(N)])
        total = time.perf_counter() - start
    lat.sort()
    return {
        "avg": statistics.mean(lat),
        "p95": lat[int(0.95 * len(lat)) - 1],
        "total": total,
        "rps": N / total,
    }

async def main():
    rows = {}
    for name, path in [("v1 sync", "/api/v1/report/1"), ("v2 async", "/api/v2/report/1")]:
        rows[name] = await run(path)

    print("| Version | Avg (ms) | P95 (ms) | Total (s) | Req/s |")
    print("|---|---|---|---|---|")
    for k, v in rows.items():
        print(f"| {k} | {v['avg']:.0f} | {v['p95']:.0f} | {v['total']:.2f} | {v['rps']:.1f} |")

    imp = (1 - rows["v2 async"]["avg"] / rows["v1 sync"]["avg"]) * 100
    print(f"\nAvg response time improvement: {imp:.1f}%")

asyncio.run(main())