"""Minimal observability: request logging, metrics, and a simple dashboard."""

import logging
import time
import uuid

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

logger = logging.getLogger("app.requests")

REQUESTS_TOTAL = Counter("http_requests_total", "Total HTTP requests")
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0),
)
BOOKING_CONFLICTS = Counter(
    "booking_conflicts_total", "Bookings rejected with a 409 conflict"
)

router = APIRouter(tags=["observability"])


def configure_logging() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )


def _sample_value(collector, suffix: str) -> float:
    for metric in collector.collect():
        for sample in metric.samples:
            if sample.name.endswith(suffix):
                return sample.value
    return 0.0


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def install(app: FastAPI) -> None:
    """Attach observability routes and request logging middleware to the app."""
    app.include_router(router)

    @app.middleware("http")
    async def log_and_measure(request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        request_id = uuid.uuid4().hex[:8]
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            REQUESTS_TOTAL.inc()
            REQUEST_DURATION.observe(time.perf_counter() - start)
            logger.exception(
                "request failed request_id=%s method=%s path=%s",
                request_id,
                request.method,
                request.url.path,
            )
            raise

        duration = time.perf_counter() - start
        REQUESTS_TOTAL.inc()
        REQUEST_DURATION.observe(duration)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%d duration_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration * 1000,
        )
        return response
