import argparse
import json
import statistics
import time

import httpx


def percentile(values: list[float], percentile_value: float) -> float:
    ordered = sorted(values)
    index = min(round((len(ordered) - 1) * percentile_value), len(ordered) - 1)
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark a running FabCopilot API")
    parser.add_argument("--url", default="http://127.0.0.1:8000/health")
    parser.add_argument("--requests", type=int, default=200)
    args = parser.parse_args()
    if args.requests < 1:
        raise ValueError("requests must be positive")

    durations_ms: list[float] = []
    started_at = time.perf_counter()
    with httpx.Client(timeout=5.0, trust_env=False) as client:
        for _ in range(args.requests):
            request_started = time.perf_counter()
            response = client.get(args.url)
            response.raise_for_status()
            durations_ms.append((time.perf_counter() - request_started) * 1000)
    elapsed = time.perf_counter() - started_at

    print(
        json.dumps(
            {
                "url": args.url,
                "requests": args.requests,
                "requests_per_second": round(args.requests / elapsed, 2),
                "latency_ms": {
                    "mean": round(statistics.mean(durations_ms), 3),
                    "p50": round(percentile(durations_ms, 0.50), 3),
                    "p95": round(percentile(durations_ms, 0.95), 3),
                    "max": round(max(durations_ms), 3),
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
