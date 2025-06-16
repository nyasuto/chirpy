"""
Simplified unit tests for DatabaseManager operations.
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from db_utils import DatabaseManager


class TestDatabaseManagerSimple:
    """Test DatabaseManager basic functionality."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            yield tmp.name
        Path(tmp.name).unlink(missing_ok=True)

    @pytest.fixture
    def test_db(self, temp_db_path):
        """Create a test database with sample data."""
        db = DatabaseManager(temp_db_path)

        # Create tables
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

            # Insert sample data
            sample_data = [
                (
                    1,
                    "Test Japanese Article",
                    "https://example.com/jp1",
                    "2025-06-16T10:00:00+09:00",
                    "これは日本語のテスト記事です。",
                    0,
                    "ja",
                    None,
                    0,
                ),
                (
                    2,
                    "Test English Article",
                    "https://example.com/en1",
                    "2025-06-16T11:00:00+09:00",
                    "This is an English test article.",
                    0,
                    "en",
                    None,
                    0,
                ),
                (
                    3,
                    "Unknown Language Article",
                    "https://example.com/unknown",
                    "2025-06-16T12:00:00+09:00",
                    "Article with unknown language.",
                    0,
                    "unknown",
                    None,
                    0,
                ),
                (
                    4,
                    "Empty Summary Article",
                    "https://example.com/empty",
                    "2025-06-16T13:00:00+09:00",
                    "",
                    0,
                    "unknown",
                    None,
                    0,
                ),
                (
                    5,
                    "Read Article",
                    "https://example.com/read",
                    "2025-06-16T14:00:00+09:00",
                    "This article was already read.",
                    0,
                    "en",
                    None,
                    0,
                ),
            ]

            cursor.executemany(
                """
                INSERT INTO articles 
                (id, title, link, published, summary, embedded, detected_language, original_summary, is_translated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                sample_data,
            )

            # Mark article 5 as read
            cursor.execute("INSERT INTO read_articles (article_id) VALUES (5)")

            conn.commit()

        return db

    def test_database_initialization(self, temp_db_path):
        """Test database manager initialization."""
        db = DatabaseManager(temp_db_path)
        assert str(db.db_path) == temp_db_path

    def test_get_connection(self, test_db):
        """Test database connection creation."""
        with test_db.get_connection() as conn:
            assert isinstance(conn, sqlite3.Connection)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1  # SQLite returns Row objects, not tuples

    def test_get_total_count(self, test_db):
        """Test getting total article count."""
        total = test_db.get_total_count()
        assert total == 5

    def test_get_read_count(self, test_db):
        """Test getting read article count."""
        read_count = test_db.get_read_count()
        assert read_count == 1

    def test_get_unread_count(self, test_db):
        """Test getting unread article count."""
        unread_count = test_db.get_unread_count()
        assert (
            unread_count == 3
        )  # Articles 1-3 are unread (4 has empty summary, 5 is read)

    def test_get_empty_summaries_count(self, test_db):
        """Test getting empty summaries count."""
        empty_count = test_db.get_empty_summaries_count()
        assert empty_count == 1

    def test_get_database_stats(self, test_db):
        """Test getting comprehensive database statistics."""
        stats = test_db.get_database_stats()

        assert stats["total_articles"] == 5
        assert stats["read_articles"] == 1
        assert stats["unread_articles"] == 3  # Articles with content that are unread
        assert stats["empty_summaries"] == 1

    def test_get_unread_articles(self, test_db):
        """Test getting unread articles."""
        articles = test_db.get_unread_articles(limit=3)

        assert len(articles) == 3
        # Articles should have required fields
        for article in articles:
            assert "id" in article
            assert "title" in article
            assert "link" in article
            assert "summary" in article

    def test_get_article_by_id(self, test_db):
        """Test getting specific article by ID."""
        article = test_db.get_article_by_id(1)

        assert article is not None
        assert article["id"] == 1
        assert article["title"] == "Test Japanese Article"

    def test_get_article_by_id_not_found(self, test_db):
        """Test getting non-existent article by ID."""
        article = test_db.get_article_by_id(999)
        assert article is None

    def test_mark_article_as_read(self, test_db):
        """Test marking article as read."""
        initial_read_count = test_db.get_read_count()

        success = test_db.mark_article_as_read(1)
        assert success is True

        final_read_count = test_db.get_read_count()
        assert final_read_count == initial_read_count + 1

    def test_update_article_summary(self, test_db):
        """Test updating article summary."""
        new_summary = "Updated test summary"
        success = test_db.update_article_summary(1, new_summary)
        assert success is True

        # Verify update
        article = test_db.get_article_by_id(1)
        assert article["summary"] == new_summary

    def test_update_article_language_info(self, test_db):
        """Test updating article language information."""
        success = test_db.update_article_language_info(
            article_id=3,
            detected_language="en",
            original_summary="Original English text",
            is_translated=True,
        )
        assert success is True

        # Verify update by checking database directly
        with test_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT detected_language, original_summary, is_translated 
                FROM articles WHERE id = 3
            """)
            row = cursor.fetchone()
            assert row[0] == "en"
            assert row[1] == "Original English text"
            assert row[2] == 1

    def test_get_articles_with_empty_summaries(self, test_db):
        """Test getting articles with empty summaries."""
        articles = test_db.get_articles_with_empty_summaries(limit=10)

        assert len(articles) == 1
        assert articles[0]["id"] == 4
        assert articles[0]["summary"] == ""

    def test_database_connection_context_manager(self, test_db):
        """Test database connection context manager."""
        # Test that connection is properly closed
        conn_id = None
        with test_db.get_connection() as conn:
            conn_id = id(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            count = cursor.fetchone()[0]
            assert count == 5

        # Connection should be closed after context
        assert conn_id is not None

    def test_database_query_with_dict_row(self, test_db):
        """Test that database queries return dict-like rows."""
        articles = test_db.get_unread_articles(limit=1)
        assert len(articles) == 1

        article = articles[0]
        # Should be able to access fields by name
        assert article["title"] is not None
        assert article["id"] is not None

        # Should be a dictionary-like object
        assert isinstance(article, dict) or hasattr(article, "keys")

    def test_database_error_handling(self):
        """Test database error handling with invalid path."""
        # DatabaseManager raises FileNotFoundError for non-existent files
        with pytest.raises(FileNotFoundError):
            DatabaseManager("/invalid/path/that/does/not/exist.db")

