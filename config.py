"""
Configuration management for Chirpy RSS reader.

Handles application settings, environment variables, and logging configuration.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


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
    openai_tts_voice: str = "alloy"  # alloy, echo, fable, onyx, nova, shimmer
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
            max_articles=int(os.getenv("CHIRPY_MAX_ARTICLES", "3")),
            max_summary_length=int(os.getenv("CHIRPY_MAX_SUMMARY_LENGTH", "500")),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            openai_max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "500")),
            openai_temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.3")),
            tts_engine=os.getenv("TTS_ENGINE", "pyttsx3"),
            tts_rate=int(os.getenv("TTS_RATE", "180")),
            tts_volume=float(os.getenv("TTS_VOLUME", "0.9")),
            tts_quality=os.getenv("TTS_QUALITY", "hd"),
            openai_tts_voice=os.getenv("OPENAI_TTS_VOICE", "alloy"),
            audio_format=os.getenv("AUDIO_FORMAT", "mp3"),
            tts_speed_multiplier=float(os.getenv("TTS_SPEED_MULTIPLIER", "1.0")),
            fetch_timeout=int(os.getenv("FETCH_TIMEOUT", "30")),
            rate_limit_delay=int(os.getenv("RATE_LIMIT_DELAY", "2")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_format=os.getenv(
                "LOG_FORMAT",
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            ),
            log_file=os.getenv("LOG_FILE"),
            log_max_bytes=int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024))),
            log_backup_count=int(os.getenv("LOG_BACKUP_COUNT", "3")),
            auto_mark_read=os.getenv("AUTO_MARK_READ", "true").lower() == "true",
            pause_between_articles=os.getenv("PAUSE_BETWEEN_ARTICLES", "true").lower()
            == "true",
            interactive_mode=os.getenv("INTERACTIVE_MODE", "false").lower() == "true",
            speech_enabled=os.getenv("SPEECH_ENABLED", "true").lower() == "true",
            auto_translate=os.getenv("AUTO_TRANSLATE", "true").lower() == "true",
            target_language=os.getenv("TARGET_LANGUAGE", "ja"),
            preserve_original=os.getenv("PRESERVE_ORIGINAL", "true").lower() == "true",
            translation_provider=os.getenv("TRANSLATION_PROVIDER", "openai"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        }


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
