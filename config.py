"""
Configuration management for Chirpy RSS reader.

Handles application settings, environment variables, and logging configuration.
"""

import logging
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def _parse_env_value(value: str | None) -> str | None:
    """Parse environment variable value, removing inline comments."""
    if value is None:
        return None
    # Split on # and take first part, then strip whitespace
    return value.split("#")[0].strip() or None


@dataclass
class ChirpyConfig:
    """Configuration settings for Chirpy application."""

    # Database settings
    database_path: str = "data/articles.db"

    # Article processing settings
    max_articles: int = 3
    max_summary_length: int = 500

    # OpenAI API settings
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 500
    openai_temperature: float = 0.3

    # Text-to-speech settings
    tts_engine: str = "pyttsx3"  # 'pyttsx3' or 'say'
    tts_rate: int = 180  # words per minute
    tts_volume: float = 0.9  # 0.0 to 1.0

    # OpenAI TTS settings
    tts_quality: str = "hd"  # 'basic', 'standard', 'hd'
    openai_tts_voice: str = "nova"  # alloy, echo, fable, onyx, nova, shimmer
    audio_format: str = "mp3"  # mp3, opus, aac, flac
    tts_speed_multiplier: float = 1.0  # 0.25 to 4.0

    # Content fetching settings
    fetch_timeout: int = 30  # seconds
    rate_limit_delay: int = 2  # seconds between API calls

    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: str | None = None  # None for console only
    log_max_bytes: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 3

    # Application behavior
    auto_mark_read: bool = True
    pause_between_articles: bool = True
    speech_enabled: bool = True
    interactive_mode: bool = False
    select_articles: bool = False

    # Translation settings
    auto_translate: bool = True
    target_language: str = "ja"
    preserve_original: bool = True
    translation_provider: str = "openai"

    # Audio cache management settings
    audio_cache_max_size_mb: int = 100  # Maximum cache size in MB
    audio_cache_max_age_days: int = 30  # File expiration time in days
    audio_cache_cleanup_on_startup: bool = True  # Clean expired files on startup
    audio_cache_cleanup_threshold: float = 0.8  # Cleanup at 80% of max size

    def __post_init__(self) -> None:
        """Post-initialization processing."""
        # Convert string paths to Path objects if needed
        if isinstance(self.database_path, str):
            self.database_path = str(Path(self.database_path).expanduser())

        # Validate ranges
        self.max_articles = max(1, min(100, self.max_articles))
        self.tts_rate = max(50, min(500, self.tts_rate))
        self.tts_volume = max(0.0, min(1.0, self.tts_volume))
        self.openai_temperature = max(0.0, min(2.0, self.openai_temperature))

    def update_from_dict(self, updates: dict[str, Any]) -> None:
        """Update configuration from dictionary."""
        for key, value in updates.items():
            if hasattr(self, key):
                setattr(self, key, value)
        # Re-run validation
        self.__post_init__()

    @classmethod
    def from_env(cls) -> "ChirpyConfig":
        """Create configuration from environment variables."""
        load_dotenv()

        return cls(
            database_path=os.getenv("CHIRPY_DATABASE_PATH", "data/articles.db"),
            max_articles=int(_parse_env_value(os.getenv("CHIRPY_MAX_ARTICLES")) or "3"),
            max_summary_length=int(
                _parse_env_value(os.getenv("CHIRPY_MAX_SUMMARY_LENGTH")) or "500"
            ),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            openai_max_tokens=int(
                _parse_env_value(os.getenv("OPENAI_MAX_TOKENS")) or "500"
            ),
            openai_temperature=float(
                _parse_env_value(os.getenv("OPENAI_TEMPERATURE")) or "0.3"
            ),
            tts_engine=os.getenv("TTS_ENGINE", "pyttsx3"),
            tts_rate=int(_parse_env_value(os.getenv("TTS_RATE")) or "180"),
            tts_volume=float(_parse_env_value(os.getenv("TTS_VOLUME")) or "0.9"),
            tts_quality=os.getenv("TTS_QUALITY", "hd"),
            openai_tts_voice=os.getenv("OPENAI_TTS_VOICE", "nova"),
            audio_format=os.getenv("AUDIO_FORMAT", "mp3"),
            tts_speed_multiplier=float(
                _parse_env_value(os.getenv("TTS_SPEED_MULTIPLIER")) or "1.0"
            ),
            fetch_timeout=int(_parse_env_value(os.getenv("FETCH_TIMEOUT")) or "30"),
            rate_limit_delay=int(
                _parse_env_value(os.getenv("RATE_LIMIT_DELAY")) or "2"
            ),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_format=os.getenv(
                "LOG_FORMAT",
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            ),
            log_file=os.getenv("LOG_FILE"),
            log_max_bytes=int(
                _parse_env_value(os.getenv("LOG_MAX_BYTES")) or str(10 * 1024 * 1024)
            ),
            log_backup_count=int(
                _parse_env_value(os.getenv("LOG_BACKUP_COUNT")) or "3"
            ),
            auto_mark_read=(
                _parse_env_value(os.getenv("AUTO_MARK_READ")) or "true"
            ).lower()
            == "true",
            pause_between_articles=(
                _parse_env_value(os.getenv("PAUSE_BETWEEN_ARTICLES")) or "true"
            ).lower()
            == "true",
            interactive_mode=(
                _parse_env_value(os.getenv("INTERACTIVE_MODE")) or "false"
            ).lower()
            == "true",
            speech_enabled=(
                _parse_env_value(os.getenv("SPEECH_ENABLED")) or "true"
            ).lower()
            == "true",
            auto_translate=(
                _parse_env_value(os.getenv("AUTO_TRANSLATE")) or "true"
            ).lower()
            == "true",
            target_language=os.getenv("TARGET_LANGUAGE", "ja"),
            preserve_original=(
                _parse_env_value(os.getenv("PRESERVE_ORIGINAL")) or "true"
            ).lower()
            == "true",
            translation_provider=os.getenv("TRANSLATION_PROVIDER", "openai"),
            audio_cache_max_size_mb=int(
                _parse_env_value(os.getenv("AUDIO_CACHE_MAX_SIZE_MB")) or "100"
            ),
            audio_cache_max_age_days=int(
                _parse_env_value(os.getenv("AUDIO_CACHE_MAX_AGE_DAYS")) or "30"
            ),
            audio_cache_cleanup_on_startup=(
                (
                    _parse_env_value(os.getenv("AUDIO_CACHE_CLEANUP_ON_STARTUP"))
                    or "true"
                ).lower()
                == "true"
            ),
            audio_cache_cleanup_threshold=float(
                _parse_env_value(os.getenv("AUDIO_CACHE_CLEANUP_THRESHOLD")) or "0.8"
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        }

    def validate_security(self) -> list[str]:
        """
        Validate configuration for security issues.

        Returns:
            List of security warnings/issues found
        """
        warnings = []

        # Check API key security
        if self.openai_api_key:
            if len(self.openai_api_key) < 20:
                warnings.append("OpenAI API key appears too short - may be invalid")
            if not self.openai_api_key.startswith(("sk-", "sk_")):
                warnings.append("OpenAI API key format looks suspicious")

        # Check file permissions for sensitive files
        sensitive_files = [
            self.database_path,
            ".env",
            "config.toml",
        ]

        for file_path in sensitive_files:
            path_obj = Path(file_path)
            if path_obj.exists():
                perms = self._check_file_permissions(path_obj)
                if perms:
                    warnings.extend(perms)

        # Check log file security
        if self.log_file:
            log_path = Path(self.log_file)
            if log_path.exists():
                perms = self._check_file_permissions(log_path)
                if perms:
                    warnings.extend(perms)

        return warnings

    def _check_file_permissions(self, file_path: Path) -> list[str]:
        """
        Check file permissions for security issues.

        Args:
            file_path: Path to file to check

        Returns:
            List of permission-related warnings
        """
        warnings = []

        try:
            file_stat = file_path.stat()
            mode = file_stat.st_mode

            # Check if file is world-readable
            if mode & stat.S_IROTH:
                warnings.append(
                    f"{file_path} is world-readable - may expose sensitive data"
                )

            # Check if file is world-writable
            if mode & stat.S_IWOTH:
                warnings.append(f"{file_path} is world-writable - security risk")

            # Check if file is group-writable (less critical)
            if mode & stat.S_IWGRP:
                warnings.append(
                    f"{file_path} is group-writable - potential security risk"
                )

        except (OSError, PermissionError) as e:
            warnings.append(f"Could not check permissions for {file_path}: {e}")

        return warnings

    def secure_file_permissions(self, file_path: str) -> bool:
        """
        Set secure permissions on a file (owner read/write only).

        Args:
            file_path: Path to file to secure

        Returns:
            True if permissions were set successfully
        """
        try:
            path_obj = Path(file_path)
            if path_obj.exists():
                # Set permissions to owner read/write only (600)
                path_obj.chmod(stat.S_IRUSR | stat.S_IWUSR)
                return True
        except (OSError, PermissionError) as e:
            print(f"Warning: Could not secure permissions for {file_path}: {e}")

        return False


class ChirpyLogger:
    """Centralized logging configuration for Chirpy."""

    def __init__(self, config: ChirpyConfig):
        """Initialize logging system."""
        self.config = config
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging based on configuration."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Set log level
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logging.basicConfig(level=log_level)

        # Create formatter
        formatter = logging.Formatter(self.config.log_format)

        # Configure console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)

        # Add console handler to root logger
        root_logger.addHandler(console_handler)

        # Configure file handler if specified
        if self.config.log_file:
            try:
                from logging.handlers import RotatingFileHandler

                log_path = Path(self.config.log_file).expanduser()
                log_path.parent.mkdir(parents=True, exist_ok=True)

                file_handler = RotatingFileHandler(
                    log_path,
                    maxBytes=self.config.log_max_bytes,
                    backupCount=self.config.log_backup_count,
                )
                file_handler.setFormatter(formatter)
                file_handler.setLevel(log_level)
                root_logger.addHandler(file_handler)

                logging.info(f"File logging enabled: {log_path}")

            except Exception as e:
                logging.warning(f"Failed to setup file logging: {e}")

        # Set specific logger levels for third-party libraries
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)

        logging.info("Logging system initialized")

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a logger instance."""
        return logging.getLogger(name)


def get_config() -> ChirpyConfig:
    """Get application configuration from environment."""
    return ChirpyConfig.from_env()


def setup_logging(config: ChirpyConfig | None = None) -> ChirpyLogger:
    """Setup logging system."""
    if config is None:
        config = get_config()
    return ChirpyLogger(config)


# Global configuration instance
_config: ChirpyConfig | None = None
_logger_instance: ChirpyLogger | None = None


def get_global_config() -> ChirpyConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = get_config()
    return _config


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with proper configuration."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = setup_logging()
    return _logger_instance.get_logger(name)


def initialize_app_logging() -> tuple[ChirpyConfig, logging.Logger]:
    """Initialize application logging and return config and logger."""
    config = get_global_config()
    logger_instance = setup_logging(config)
    logger = logger_instance.get_logger("chirpy")
    return config, logger
