"""Exponential backoff strategy for relay operations."""

import random
from typing import Optional


class HardError(Exception):
    """Non-retryable error — stop immediately."""

    def __init__(self, message: str, code: str = "unknown"):
        self.message = message
        self.code = code
        super().__init__(message)


class SoftError(Exception):
    """Retryable error — apply backoff and retry."""

    def __init__(self, message: str, code: str = "unknown"):
        self.message = message
        self.code = code
        super().__init__(message)


class BackoffConfig:
    """Configuration for backoff behavior."""

    def __init__(
        self,
        base_delay: float = 60.0,  # seconds
        max_errors: int = 3,
        max_backoff: float = 900.0,  # 15 minutes
        multiplier: float = 2.0,
        jitter: float = 0.1,
    ):
        self.base_delay = base_delay
        self.max_errors = max_errors
        self.max_backoff = max_backoff
        self.multiplier = multiplier
        self.jitter = jitter


class ExponentialBackoff:
    """Exponential backoff with hard/soft error separation.

    Hard errors (HardError): increment consecutive_errors, reset failures.
    Soft errors (SoftError): increment consecutive_failures, reset errors.
    """

    def __init__(self, config: Optional[BackoffConfig] = None):
        self.config = config or BackoffConfig()
        self.consecutive_errors = 0
        self.consecutive_failures = 0

    def record_error(self) -> None:
        """Hard error: agent crash/JSON parse/infrastructure failure."""
        self.consecutive_errors += 1
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        """Soft error: agent reported success=false."""
        self.consecutive_failures += 1
        self.consecutive_errors = 0

    def record_success(self) -> None:
        self.consecutive_errors = 0
        self.consecutive_failures = 0

    @property
    def should_abort(self) -> bool:
        """3 consecutive failures -> abort."""
        return self.consecutive_failures >= self.config.max_errors

    @property
    def backoff_duration(self) -> float:
        """Seconds to wait before retry (hard errors only)."""
        if self.consecutive_errors == 0:
            return 0.0
        delay = self.config.base_delay * (self.config.multiplier ** (self.consecutive_errors - 1))
        # Add jitter
        jitter_range = delay * self.config.jitter
        delay += random.uniform(-jitter_range, jitter_range)
        return min(delay, self.config.max_backoff)

    @property
    def should_wait_before_retry(self) -> bool:
        return self.consecutive_errors > 0
