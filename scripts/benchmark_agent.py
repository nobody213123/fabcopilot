import argparse
import json
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def post_diagnosis(url: str, request_id: int, timeout: float) -> float:
    payload = json.dumps(
        {
            "prompt": (
                "Analyze DF-01 temperature uniformity and cite evidence. "
                f"Benchmark request {request_id}."
            )
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP status {response.status}")
        body = json.loads(response.read())
        if not body.get("evidence"):
            raise RuntimeError("diagnosis returned no evidence")
    return (time.perf_counter() - started) * 1000


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/agent/diagnose",
    )
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    if args.requests <= 0 or args.concurrency <= 0:
        raise SystemExit("requests and concurrency must be positive")

    # Exclude one-time model initialization from the steady-state measurement.
    post_diagnosis(args.url, -1, args.timeout)

    latencies: list[float] = []
    failures: list[str] = []
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(post_diagnosis, args.url, index, args.timeout): index
            for index in range(args.requests)
        }
        for future in as_completed(futures):
            try:
                latencies.append(future.result())
            except Exception as exc:  # noqa: BLE001
                failures.append(f"request {futures[future]}: {exc}")
    elapsed = time.perf_counter() - started

    report = {
        "requests": args.requests,
        "concurrency": args.concurrency,
        "successes": len(latencies),
        "failures": len(failures),
        "throughput_requests_per_second": len(latencies) / elapsed,
        "mean_latency_ms": statistics.mean(latencies) if latencies else None,
        "p50_latency_ms": percentile(latencies, 0.50) if latencies else None,
        "p95_latency_ms": percentile(latencies, 0.95) if latencies else None,
        "max_latency_ms": max(latencies) if latencies else None,
        "failure_samples": failures[:5],
    }
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
