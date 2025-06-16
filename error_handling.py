"""
Error handling utilities for Chirpy RSS reader.

Provides circuit breaker pattern, retry logic, and comprehensive error handling.
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Generator, TypeVar, Optional

import openai
import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    RetryError,
)

T = TypeVar("T")

class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"  
    HALF_OPEN = "half_open"


@dataclass
class ErrorContext:
    """Context information for error events."""
    operation: str
    component: str
    error_type: str
    error_message: str
    timestamp: float
    retry_count: int = 0
    recoverable: bool = True


class CircuitBreaker:
    """Simple circuit breaker implementation for external services."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        name: str = "default"
    ) -> None:
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Time in seconds before attempting to close circuit
            name: Name for logging and identification
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.name = name
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = CircuitBreakerState.CLOSED
        self.logger = logging.getLogger(f"circuit_breaker.{name}")
    
    def call(self, func: Callable[[], T]) -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: When circuit is open
            Original exception: When function fails and circuit remains closed
        """
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.logger.info(f"Circuit breaker '{self.name}' entering half-open state")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is open"
                )
        
        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        """Handle successful operation."""
        if self.failure_count > 0:
            self.logger.info(f"Circuit breaker '{self.name}' reset after success")
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self) -> None:
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.logger.warning(
                f"Circuit breaker '{self.name}' opened after {self.failure_count} failures"
            )


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class ErrorHandler:
    """Centralized error handling and logging."""
    
    def __init__(self, component_name: str) -> None:
        """
        Initialize error handler.
        
        Args:
            component_name: Name of the component for logging context
        """
        self.component_name = component_name
        self.logger = logging.getLogger(f"error_handler.{component_name}")
    
    def handle_error(
        self,
        operation: str,
        error: Exception,
        retry_count: int = 0,
        recoverable: bool = True,
        context: Optional[dict[str, Any]] = None
    ) -> ErrorContext:
        """
        Handle and log error with context.
        
        Args:
            operation: Name of the operation that failed
            error: The exception that occurred
            retry_count: Current retry attempt number
            recoverable: Whether the error is potentially recoverable
            context: Additional context information
            
        Returns:
            ErrorContext object with error details
        """
        error_context = ErrorContext(
            operation=operation,
            component=self.component_name,
            error_type=type(error).__name__,
            error_message=str(error),
            timestamp=time.time(),
            retry_count=retry_count,
            recoverable=recoverable
        )
        
        log_message = (
            f"Error in {operation}: {error_context.error_type} - {error_context.error_message}"
        )
        
        if context:
            log_message += f" | Context: {context}"
        
        if retry_count > 0:
            log_message += f" | Retry: {retry_count}"
        
        if not recoverable:
            self.logger.error(log_message)
        elif retry_count > 0:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        return error_context


def create_retry_decorator(
    max_retries: int = 3,
    backoff_multiplier: float = 1.0,
    min_wait: float = 4.0,
    max_wait: float = 10.0,
    retry_on: tuple[type[Exception], ...] = (requests.RequestException, openai.APIError)
):
    """
    Create a retry decorator with specified parameters.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_multiplier: Multiplier for exponential backoff
        min_wait: Minimum wait time between retries
        max_wait: Maximum wait time between retries
        retry_on: Exception types to retry on
        
    Returns:
        Retry decorator
    """
    return retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(
            multiplier=backoff_multiplier,
            min=min_wait,
            max=max_wait
        ),
        retry=retry_if_exception_type(retry_on),
        reraise=True
    )


@contextmanager
def timeout_context(seconds: int, operation_name: str = "operation") -> Generator[None, None, None]:
    """
    Context manager for operation timeout (Unix only).
    
    Args:
        seconds: Timeout in seconds
        operation_name: Name of operation for error message
        
    Yields:
        None
        
    Raises:
        TimeoutError: When operation times out
    """
    import signal
    
    def signal_handler(signum: int, frame: Any) -> None:
        raise TimeoutError(f"{operation_name} timed out after {seconds} seconds")
    
    # Set up signal handler
    old_handler = signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Clean up
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def is_recoverable_error(error: Exception) -> bool:
    """
    Determine if an error is potentially recoverable.
    
    Args:
        error: The exception to check
        
    Returns:
        True if error might be recoverable with retry
    """
    # Network and temporary API errors
    if isinstance(error, (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        openai.RateLimitError,
        openai.APITimeoutError,
        openai.InternalServerError,
    )):
        return True
    
    # HTTP 5xx errors (server errors)
    if isinstance(error, requests.exceptions.HTTPError):
        if hasattr(error, 'response') and error.response is not None:
            return 500 <= error.response.status_code < 600
    
    # OpenAI API errors that might be temporary
    if isinstance(error, openai.APIError):
        # Rate limits and server errors are recoverable
        if isinstance(error, (openai.RateLimitError, openai.InternalServerError)):
            return True
        # Check error code if available
        if hasattr(error, 'code') and error.code in ['rate_limit_exceeded', 'server_error']:
            return True
    
    # Database lock errors (SQLite)
    if 'database is locked' in str(error).lower():
        return True
    
    return False


def get_user_friendly_message(error: Exception, operation: str) -> str:
    """
    Get user-friendly error message for display.
    
    Args:
        error: The exception that occurred
        operation: The operation that failed
        
    Returns:
        User-friendly error message
    """
    if isinstance(error, requests.exceptions.Timeout):
        return f"Network request timed out while {operation}. Please check your internet connection and try again."
    
    if isinstance(error, requests.exceptions.ConnectionError):
        return f"Unable to connect to the internet while {operation}. Please check your network connection."
    
    if isinstance(error, openai.RateLimitError):
        return f"API rate limit exceeded while {operation}. The system will automatically retry in a moment."
    
    if isinstance(error, openai.AuthenticationError):
        return f"API authentication failed while {operation}. Please check your API key configuration."
    
    if isinstance(error, openai.APIError):
        return f"External service temporarily unavailable while {operation}. The system will retry automatically."
    
    if isinstance(error, FileNotFoundError):
        return f"Required file not found while {operation}. Please check your configuration."
    
    if isinstance(error, PermissionError):
        return f"Permission denied while {operation}. Please check file permissions."
    
    if 'database' in str(error).lower():
        return f"Database error occurred while {operation}. The system will attempt to recover."
    
    # Generic fallback
    return f"An error occurred while {operation}. The system will attempt to continue."


class HealthChecker:
    """Health checking utility for system components."""
    
    def __init__(self) -> None:
        """Initialize health checker."""
        self.logger = logging.getLogger("health_checker")
    
    def check_internet_connectivity(self, timeout: int = 10) -> bool:
        """
        Check if internet connectivity is available.
        
        Args:
            timeout: Timeout for connectivity check
            
        Returns:
            True if internet is accessible
        """
        try:
            response = requests.get(
                "https://httpbin.org/get",
                timeout=timeout,
                headers={"User-Agent": "Chirpy-HealthCheck/1.0"}
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def check_openai_api(self, api_key: str, timeout: int = 30) -> bool:
        """
        Check if OpenAI API is accessible.
        
        Args:
            api_key: OpenAI API key
            timeout: Timeout for API check
            
        Returns:
            True if OpenAI API is accessible
        """
        if not api_key:
            return False
        
        try:
            client = openai.OpenAI(api_key=api_key, timeout=timeout)
            # Simple API call to check connectivity
            client.models.list()
            return True
        except Exception:
            return False
    
    def check_disk_space(self, path: str, min_free_mb: int = 100) -> bool:
        """
        Check if sufficient disk space is available.
        
        Args:
            path: Path to check disk space for
            min_free_mb: Minimum free space required in MB
            
        Returns:
            True if sufficient disk space is available
        """
        try:
            import shutil
            free_bytes = shutil.disk_usage(path).free
            free_mb = free_bytes / (1024 * 1024)
            return free_mb >= min_free_mb
        except Exception:
            return False