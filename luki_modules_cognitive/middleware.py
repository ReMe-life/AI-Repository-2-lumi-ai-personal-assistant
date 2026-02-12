"""
Middleware for LUKi Cognitive Module.

Provides:
- Request correlation: generates or propagates X-Trace-ID headers so that
  requests can be traced across the core agent → cognitive → security chain.
- Structured request logging: logs method, path, status, and latency for
  every request (excluding high-frequency probes like /health).
"""

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Optional

from fastapi import Request

logger = logging.getLogger(__name__)

# Context variable holding the active trace ID for the current request.
_trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


def get_trace_id() -> Optional[str]:
    """Return the trace ID bound to the current async context."""
    return _trace_id_var.get()


async def correlation_middleware(request: Request, call_next):
    """
    Extract or generate a trace ID and store it in a context variable.

    The trace ID is propagated to the response via ``X-Trace-ID`` so
    callers can correlate gateway ↔ cognitive ↔ security requests.
    """
    trace_id = (
        request.headers.get("x-trace-id")
        or request.headers.get("x-request-id")
        or uuid.uuid4().hex[:16]
    )
    _trace_id_var.set(trace_id)

    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    return response


async def request_logging_middleware(request: Request, call_next):
    """
    Log every inbound request with method, path, status code, and latency.

    Health probes are logged at DEBUG level to avoid noise.
    """
    start = time.monotonic()
    response = await call_next(request)
    latency_ms = round((time.monotonic() - start) * 1000, 1)

    path = request.url.path
    level = logging.DEBUG if path == "/health" else logging.INFO

    logger.log(
        level,
        "%s %s → %s (%.1fms)",
        request.method,
        path,
        response.status_code,
        latency_ms,
        extra={
            "method": request.method,
            "path": path,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "trace_id": _trace_id_var.get(),
        },
    )

    return response
