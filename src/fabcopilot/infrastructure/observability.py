import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "fabcopilot_http_requests_total",
    "HTTP requests grouped by method, route, and status code.",
    ("method", "route", "status_code"),
)
REQUEST_DURATION = Histogram(
    "fabcopilot_http_request_duration_seconds",
    "HTTP request duration grouped by method and route.",
    ("method", "route"),
)


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level.upper(),
        force=True,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


async def observe_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    started_at = time.perf_counter()
    status_code = 500
    structlog.contextvars.bind_contextvars(request_id=request_id)
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        route_object = request.scope.get("route")
        route = getattr(route_object, "path", request.url.path)
        duration = time.perf_counter() - started_at
        REQUEST_COUNT.labels(request.method, route, str(status_code)).inc()
        REQUEST_DURATION.labels(request.method, route).observe(duration)
        structlog.get_logger().info(
            "http_request_completed",
            method=request.method,
            route=route,
            status_code=status_code,
            duration_ms=round(duration * 1000, 3),
        )
        structlog.contextvars.clear_contextvars()
