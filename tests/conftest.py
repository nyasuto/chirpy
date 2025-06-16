"""
Pytest configuration and shared fixtures for Chirpy RSS Reader tests.
"""

import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock

import pytest
import responses

from config import ChirpyConfig
from content_fetcher import ContentFetcher
from db_utils import DatabaseManager


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_path:
        yield Path(temp_path)


@pytest.fixture
def test_db_path(temp_dir: Path) -> Path:
    """Create a test database path."""
    return temp_dir / "test_articles.db"


@pytest.fixture
def test_config(test_db_path: Path) -> ChirpyConfig:
    """Create a test configuration."""
    return ChirpyConfig(
        database_path=str(test_db_path),
        max_articles=3,
        max_summary_length=500,
        openai_api_key="test-api-key",
        openai_model="gpt-4o",
        openai_max_tokens=500,
        openai_temperature=0.3,
        tts_engine="pyttsx3",
        tts_rate=180,
        tts_volume=0.9,
        speech_enabled=False,  # Disable for tests
        auto_translate=True,
        target_language="ja",
        preserve_original=True,
        translation_provider="openai",
        fetch_timeout=30,
        rate_limit_delay=0,  # No delay in tests
        log_level="DEBUG",
        auto_mark_read=True,
        pause_between_articles=False,  # No pause in tests
    )


@pytest.fixture
def db_manager(test_config: ChirpyConfig) -> Generator[DatabaseManager, None, None]:
    """Create a test database manager with sample data."""
    db = DatabaseManager(test_config.database_path)
    
    # Create tables
    _create_test_tables(db)
    
    # Insert sample data
    _insert_sample_data(db)
    
    yield db


@pytest.fixture
def content_fetcher(test_config: ChirpyConfig) -> ContentFetcher:
    """Create a test content fetcher."""
    return ContentFetcher(test_config)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Mocked Japanese translation"
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_tts_engine():
    """Mock TTS engine for testing."""
    mock_engine = MagicMock()
    return mock_engine


@pytest.fixture
def sample_articles() -> list[dict[str, Any]]:
    """Sample articles for testing."""
    return [
        {
            "id": 1,
            "title": "Test Japanese Article",
            "link": "https://example.com/jp1",
            "published": "2025-06-16T10:00:00+09:00",
            "summary": "これは日本語のテスト記事です。",
            "embedded": 0,
            "detected_language": "ja",
            "original_summary": None,
            "is_translated": False,
        },
        {
            "id": 2,
            "title": "Test English Article",
            "link": "https://example.com/en1",
            "published": "2025-06-16T11:00:00+09:00",
            "summary": "This is an English test article about technology.",
            "embedded": 0,
            "detected_language": "en",
            "original_summary": None,
            "is_translated": False,
        },
        {
            "id": 3,
            "title": "Unknown Language Article",
            "link": "https://example.com/unknown",
            "published": "2025-06-16T12:00:00+09:00",
            "summary": "This article has unknown language detection.",
            "embedded": 0,
            "detected_language": "unknown",
            "original_summary": None,
            "is_translated": False,
        },
        {
            "id": 4,
            "title": "Empty Summary Article",
            "link": "https://example.com/empty",
            "published": "2025-06-16T13:00:00+09:00",
            "summary": "",
            "embedded": 0,
            "detected_language": "unknown",
            "original_summary": None,
            "is_translated": False,
        },
    ]


@pytest.fixture
def responses_mock():
    """Mock HTTP responses for web requests."""
    with responses.RequestsMock() as rsps:
        # Mock successful article fetch
        rsps.add(
            responses.GET,
            "https://example.com/test-article",
            body="<html><body><p>Test article content</p></body></html>",
            status=200,
        )
        
        # Mock failed article fetch
        rsps.add(
            responses.GET,
            "https://example.com/404",
            status=404,
        )
        
        yield rsps


def _create_test_tables(db: DatabaseManager) -> None:
    """Create test database tables."""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Create articles table with all columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                link TEXT UNIQUE,
                published TEXT,
                summary TEXT,
                embedded INTEGER DEFAULT 0,
                detected_language TEXT DEFAULT 'unknown',
                original_summary TEXT,
                is_translated INTEGER DEFAULT 0
            )
        """)
        
        # Create read_articles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS read_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles (id),
                UNIQUE(article_id)
            )
        """)
        
        conn.commit()


def _insert_sample_data(db: DatabaseManager) -> None:
    """Insert sample data into test database."""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Insert sample articles
        sample_data = [
            (1, "Test Japanese Article", "https://example.com/jp1", 
             "2025-06-16T10:00:00+09:00", "これは日本語のテスト記事です。", 0, "ja", None, 0),
            (2, "Test English Article", "https://example.com/en1", 
             "2025-06-16T11:00:00+09:00", "This is an English test article.", 0, "en", None, 0),
            (3, "Unknown Language Article", "https://example.com/unknown", 
             "2025-06-16T12:00:00+09:00", "Article with unknown language.", 0, "unknown", None, 0),
            (4, "Empty Summary Article", "https://example.com/empty", 
             "2025-06-16T13:00:00+09:00", "", 0, "unknown", None, 0),
            (5, "Read Article", "https://example.com/read", 
             "2025-06-16T14:00:00+09:00", "This article was already read.", 0, "en", None, 0),
        ]
        
        cursor.executemany("""
            INSERT INTO articles 
            (id, title, link, published, summary, embedded, detected_language, original_summary, is_translated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_data)
        
        # Mark article 5 as read
        cursor.execute("INSERT INTO read_articles (article_id) VALUES (5)")
        
        conn.commit()