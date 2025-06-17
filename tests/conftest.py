"""Pytest configuration and shared fixtures."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from config import ChirpyConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_db_path(temp_dir):
    """Create a temporary SQLite database path."""
    return str(temp_dir / "test_articles.db")


@pytest.fixture
def sample_config(test_db_path):
    """Create a sample configuration for testing."""
    return ChirpyConfig(
        database_path=test_db_path,
        max_articles=3,
        max_summary_length=500,
        openai_api_key="test-key",
        openai_model="gpt-4o",
        tts_rate=180,
        tts_volume=0.9,
        log_level="INFO",
        auto_mark_read=True,
        speech_enabled=False,  # Disable for tests
        interactive_mode=False,
    )


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Test summary content"
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_article():
    """Sample article data for testing."""
    return {
        "id": 1,
        "title": "Test Article",
        "link": "https://example.com/article",
        "published": "2023-01-01 12:00:00",
        "summary": "This is a test article summary.",
        "embedded": 0,
    }


@pytest.fixture
def articles_list():
    """List of sample articles for testing."""
    return [
        {
            "id": 1,
            "title": "First Article",
            "link": "https://example.com/1",
            "published": "2023-01-01 12:00:00",
            "summary": "First article summary.",
            "embedded": 0,
        },
        {
            "id": 2,
            "title": "Second Article",
            "link": "https://example.com/2",
            "published": "2023-01-02 12:00:00",
            "summary": "Second article summary.",
            "embedded": 0,
        },
        {
            "id": 3,
            "title": "Third Article",
            "link": "https://example.com/3",
            "published": "2023-01-03 12:00:00",
            "summary": "",  # Empty summary for testing
            "embedded": 0,
        },
    ]


@pytest.fixture(autouse=True)
def clean_env():
    """Clean environment variables before each test."""
    # Store original values
    original_env = {}
    env_vars = [
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "CHIRPY_DATABASE_PATH",
        "CHIRPY_MAX_ARTICLES",
        "CHIRPY_MAX_SUMMARY_LENGTH",
        "OPENAI_MAX_TOKENS",
        "OPENAI_TEMPERATURE",
        "TTS_ENGINE",
        "TTS_RATE",
        "TTS_VOLUME",
        "TTS_QUALITY",
        "OPENAI_TTS_VOICE",
        "AUDIO_FORMAT",
        "TTS_SPEED_MULTIPLIER",
        "FETCH_TIMEOUT",
        "RATE_LIMIT_DELAY",
        "LOG_LEVEL",
        "LOG_FORMAT",
        "LOG_FILE",
        "LOG_MAX_BYTES",
        "LOG_BACKUP_COUNT",
        "AUTO_MARK_READ",
        "PAUSE_BETWEEN_ARTICLES",
        "INTERACTIVE_MODE",
        "SPEECH_ENABLED",
        "AUTO_TRANSLATE",
        "TARGET_LANGUAGE",
        "PRESERVE_ORIGINAL",
        "TRANSLATION_PROVIDER",
    ]

    for var in env_vars:
        if var in os.environ:
            original_env[var] = os.environ[var]
            del os.environ[var]

    yield

    # Restore original values
    for var, value in original_env.items():
        os.environ[var] = value
