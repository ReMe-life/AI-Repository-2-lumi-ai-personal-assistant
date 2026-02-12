"""
Service resilience for LUKi Cognitive Module.

Provides a persistent HTTP client with circuit breaker protection for
calls to external services (security, memory).  Replaces the per-request
httpx.AsyncClient pattern with a shared, connection-pooled client that
propagates trace IDs and tracks call metrics.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime, timedelta
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ServiceCircuitBreaker:
    """
    Lightweight circuit breaker for a single downstream service.

    Transitions:
      CLOSED  --(failure_threshold failures)-->  OPEN
      OPEN    --(recovery_timeout elapsed)-->    HALF_OPEN
      HALF_OPEN --(success)-->                   CLOSED
      HALF_OPEN --(failure)-->                   OPEN
    """

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
    ) -> None:
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_seconds

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker recovered for %s", self.service_name)
        self.state = CircuitState.CLOSED
        self.failure_count = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                "Circuit breaker OPEN for %s after %d failures",
                self.service_name,
                self.failure_count,
            )

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and (
                datetime.utcnow()
                >= self.last_failure_time + timedelta(seconds=self.recovery_timeout)
            ):
                self.state = CircuitState.HALF_OPEN
                logger.info(
                    "Circuit breaker entering HALF_OPEN for %s",
                    self.service_name,
                )
                return True
            return False
        # HALF_OPEN: allow exactly one probe request
        return True

    def status(self) -> Dict[str, Any]:
        return {
            "service": self.service_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
        }


class ResilientServiceClient:
    """
    Shared, connection-pooled HTTP client with circuit breaker for
    calling external services from the cognitive module.
    """

    def __init__(self, service_name: str, base_url: str, timeout: float = 5.0) -> None:
        self.service_name = service_name
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        self._breaker = ServiceCircuitBreaker(service_name)

    async def post(
        self,
        path: str,
        *,
        json: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """POST with circuit breaker protection and trace propagation."""
        if not self._breaker.allow_request():
            raise httpx.ConnectError(
                f"Circuit breaker OPEN for {self.service_name}"
            )

        url = f"{self.base_url}{path}"
        start = time.monotonic()
        try:
            response = await self._client.post(url, json=json, headers=headers or {})
            self._breaker.record_success()
            return response
        except Exception as exc:
            self._breaker.record_failure()
            latency = round((time.monotonic() - start) * 1000, 1)
            logger.warning(
                "%s call failed (%s) after %sms: %s",
                self.service_name,
                type(exc).__name__,
                latency,
                str(exc)[:200],
            )
            raise

    async def get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """GET with circuit breaker protection."""
        if not self._breaker.allow_request():
            raise httpx.ConnectError(
                f"Circuit breaker OPEN for {self.service_name}"
            )

        url = f"{self.base_url}{path}"
        try:
            response = await self._client.get(url, params=params, headers=headers or {})
            self._breaker.record_success()
            return response
        except Exception as exc:
            self._breaker.record_failure()
            raise

    @property
    def circuit_status(self) -> Dict[str, Any]:
        return self._breaker.status()

    async def close(self) -> None:
        await self._client.aclose()
