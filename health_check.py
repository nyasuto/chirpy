"""
Health checking system for Chirpy application.

Provides comprehensive health checks for all system components.
"""

import logging
import time
from dataclasses import dataclass

from config import ChirpyConfig
from error_handling import ErrorHandler, HealthChecker


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""

    component: str
    healthy: bool
    response_time_ms: float | None
    error_message: str | None = None
    details: dict[str, str] | None = None


class SystemHealthChecker:
    """Comprehensive health checker for Chirpy system."""

    def __init__(self, config: ChirpyConfig) -> None:
        """
        Initialize system health checker.

        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger("system_health")
        self.health_checker = HealthChecker()
        self.error_handler = ErrorHandler("health_checker")

    def check_all_components(self) -> dict[str, HealthCheckResult]:
        """
        Run health checks on all system components.

        Returns:
            Dictionary mapping component names to health check results
        """
        results = {}

        # Check each component
        components = [
            ("database", self._check_database_health),
            ("internet", self._check_internet_connectivity),
            ("openai_api", self._check_openai_api),
            ("disk_space", self._check_disk_space),
            ("tts_system", self._check_tts_system),
        ]

        for component_name, check_func in components:
            try:
                start_time = time.time()
                result = check_func()
                end_time = time.time()

                result.response_time_ms = (end_time - start_time) * 1000
                results[component_name] = result

            except Exception as e:
                self.error_handler.handle_error(
                    f"health_check_{component_name}",
                    e,
                    recoverable=True,
                    context={"component": component_name},
                )
                results[component_name] = HealthCheckResult(
                    component=component_name,
                    healthy=False,
                    response_time_ms=None,
                    error_message=str(e),
                )

        return results

    def _check_database_health(self) -> HealthCheckResult:
        """Check database connectivity and integrity."""
        try:
            from db_utils import DatabaseManager

            db = DatabaseManager(self.config.database_path)

            # Test basic database operations
            total_articles = db.get_total_count()

            # Check database integrity (basic)
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()

            healthy = integrity_result and integrity_result[0] == "ok"

            return HealthCheckResult(
                component="database",
                healthy=healthy,
                response_time_ms=None,  # Will be set by caller
                details={
                    "total_articles": str(total_articles),
                    "integrity_check": str(integrity_result[0])
                    if integrity_result
                    else "failed",
                    "database_path": self.config.database_path,
                },
            )

        except Exception as e:
            return HealthCheckResult(
                component="database",
                healthy=False,
                response_time_ms=None,
                error_message=str(e),
            )

    def _check_internet_connectivity(self) -> HealthCheckResult:
        """Check internet connectivity."""
        try:
            healthy = self.health_checker.check_internet_connectivity(timeout=10)

            return HealthCheckResult(
                component="internet",
                healthy=healthy,
                response_time_ms=None,
                error_message=None if healthy else "No internet connectivity",
                details={"test_endpoint": "https://httpbin.org/get"},
            )

        except Exception as e:
            return HealthCheckResult(
                component="internet",
                healthy=False,
                response_time_ms=None,
                error_message=str(e),
            )

    def _check_openai_api(self) -> HealthCheckResult:
        """Check OpenAI API accessibility."""
        try:
            if not self.config.openai_api_key:
                return HealthCheckResult(
                    component="openai_api",
                    healthy=False,
                    response_time_ms=None,
                    error_message="No OpenAI API key configured",
                )

            healthy = self.health_checker.check_openai_api(
                self.config.openai_api_key, timeout=30
            )

            return HealthCheckResult(
                component="openai_api",
                healthy=healthy,
                response_time_ms=None,
                error_message=None if healthy else "OpenAI API not accessible",
                details={
                    "model": self.config.openai_model,
                    "api_key_configured": "yes",
                },
            )

        except Exception as e:
            return HealthCheckResult(
                component="openai_api",
                healthy=False,
                response_time_ms=None,
                error_message=str(e),
            )

    def _check_disk_space(self) -> HealthCheckResult:
        """Check available disk space."""
        try:
            import shutil

            # Check disk space for database directory
            db_dir = str(self.config.database_path).rsplit("/", 1)[0]
            if not db_dir:
                db_dir = "."

            disk_usage = shutil.disk_usage(db_dir)
            free_mb = disk_usage.free / (1024 * 1024)
            total_mb = disk_usage.total / (1024 * 1024)
            used_mb = disk_usage.used / (1024 * 1024)

            # Consider healthy if more than 100MB free
            healthy = free_mb > 100

            return HealthCheckResult(
                component="disk_space",
                healthy=healthy,
                response_time_ms=None,
                error_message=None
                if healthy
                else f"Low disk space: {free_mb:.1f}MB free",
                details={
                    "free_mb": f"{free_mb:.1f}",
                    "total_mb": f"{total_mb:.1f}",
                    "used_mb": f"{used_mb:.1f}",
                    "check_path": db_dir,
                },
            )

        except Exception as e:
            return HealthCheckResult(
                component="disk_space",
                healthy=False,
                response_time_ms=None,
                error_message=str(e),
            )

    def _check_tts_system(self) -> HealthCheckResult:
        """Check text-to-speech system availability."""
        try:
            tts_methods = []

            # Check pyttsx3 availability
            try:
                import pyttsx3

                engine = pyttsx3.init()
                engine.stop()  # Clean up
                tts_methods.append("pyttsx3")
            except Exception:
                pass

            # Check system 'say' command (macOS)
            try:
                import subprocess

                result = subprocess.run(
                    ["say", "--version"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    tts_methods.append("say")
            except Exception:
                pass

            healthy = len(tts_methods) > 0

            return HealthCheckResult(
                component="tts_system",
                healthy=healthy,
                response_time_ms=None,
                error_message=None if healthy else "No TTS methods available",
                details={
                    "available_methods": ", ".join(tts_methods)
                    if tts_methods
                    else "none",
                    "speech_enabled": str(self.config.speech_enabled),
                    "configured_engine": self.config.tts_engine,
                },
            )

        except Exception as e:
            return HealthCheckResult(
                component="tts_system",
                healthy=False,
                response_time_ms=None,
                error_message=str(e),
            )

    def get_overall_health_status(self, results: dict[str, HealthCheckResult]) -> bool:
        """
        Determine overall system health status.

        Args:
            results: Dictionary of health check results

        Returns:
            True if system is considered healthy overall
        """
        # Critical components that must be healthy
        critical_components = ["database"]

        # Check critical components
        for component in critical_components:
            if component in results and not results[component].healthy:
                return False

        # Optional components (system can function without them)
        optional_components = ["internet", "openai_api", "tts_system"]

        # At least some optional components should be healthy
        healthy_optional = sum(
            1
            for comp in optional_components
            if comp in results and results[comp].healthy
        )

        # Consider healthy if at least 1 optional component is working
        return healthy_optional >= 1

    def log_health_summary(self, results: dict[str, HealthCheckResult]) -> None:
        """
        Log a summary of health check results.

        Args:
            results: Dictionary of health check results
        """
        overall_healthy = self.get_overall_health_status(results)

        status = "HEALTHY" if overall_healthy else "UNHEALTHY"
        self.logger.info(f"System Health Check Results (Overall: {status})")

        for component, result in results.items():
            status = "✓" if result.healthy else "✗"
            response_time = (
                f" ({result.response_time_ms:.1f}ms)" if result.response_time_ms else ""
            )

            if result.healthy:
                self.logger.info(f"  {status} {component}: OK{response_time}")
            else:
                self.logger.warning(
                    f"  {status} {component}: {result.error_message}{response_time}"
                )

            # Log details for debugging
            if result.details:
                for key, value in result.details.items():
                    self.logger.debug(f"    {key}: {value}")
