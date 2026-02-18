"""
Middleware for LUKi Cognitive Module.

Provides:
- Structured JSON logging configuration per project coding standards.
- Request correlation: generates or propagates X-Trace-ID headers so that
  requests can be traced across the core agent → cognitive → security chain.
- Structured request logging: logs method, path, status, and latency for
  every request (excluding high-frequency probes like /health).
"""

import logging
import logging.config
import json
import time
import uuid
from contextvars import ContextVar
from typing import Optional

from fastapi import Request


# ---------------------------------------------------------------------------
# Structured JSON log formatter – project rules require structured JSON
# logging with no PII and exportable to observability backends.
# ---------------------------------------------------------------------------

class _JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects.

    Includes standard fields (timestamp, level, logger, message) plus any
    ``extra`` dict fields attached by the caller.  PII-sensitive request
    bodies are never included.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge caller-supplied extra fields (trace_id, latency, etc.)
        for key in ("method", "path", "status_code", "latency_ms",
                     "trace_id", "service", "user_id", "operation",
                     "error", "attempt"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info and record.exc_info[1]:
            payload["exception"] = str(record.exc_info[1])
        return json.dumps(payload, default=str)


def configure_structured_logging(level: str = "INFO") -> None:
    """Apply structured JSON logging to the cognitive module root logger.

    Call this once at import-time (below) so every logger in the package
    emits JSON.  Idempotent if called multiple times.
    """
    root = logging.getLogger("luki_modules_cognitive")
    if any(isinstance(h.formatter, _JSONFormatter) for h in root.handlers):
        return  # already configured

    handler = logging.StreamHandler()
    handler.setFormatter(_JSONFormatter())
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.propagate = False


# Auto-configure on import
configure_structured_logging()

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
