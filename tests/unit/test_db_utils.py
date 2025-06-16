"""
Unit tests for DatabaseManager operations.
"""

import sqlite3
from unittest.mock import patch

import pytest

from db_utils import DatabaseManager


class TestDatabaseManager:
    """Test DatabaseManager CRUD operations and statistics."""

    def test_database_initialization(self, test_db_path):
        """Test database manager initialization."""
        db = DatabaseManager(str(test_db_path))
        assert db.db_path == str(test_db_path)

    def test_get_connection(self, db_manager):
        """Test database connection creation."""
        with db_manager.get_connection() as conn:
            assert isinstance(conn, sqlite3.Connection)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result == (1,)

    def test_get_total_count(self, db_manager):
        """Test getting total article count."""
        total = db_manager.get_total_count()
        assert total == 5  # Based on sample data

    def test_get_read_count(self, db_manager):
        """Test getting read article count."""
        read_count = db_manager.get_read_count()
        assert read_count == 1  # Article 5 is marked as read

    def test_get_unread_count(self, db_manager):
        """Test getting unread article count."""
        unread_count = db_manager.get_unread_count()
        assert unread_count == 4  # Articles 1-4 are unread

    def test_get_empty_summaries_count(self, db_manager):
        """Test getting empty summaries count."""
        empty_count = db_manager.get_empty_summaries_count()
        assert empty_count == 1  # Article 4 has empty summary

    def test_get_database_stats(self, db_manager):
        """Test getting comprehensive database statistics."""
        stats = db_manager.get_database_stats()
        
        assert stats["total_articles"] == 5
        assert stats["read_articles"] == 1
        assert stats["unread_articles"] == 4
        assert stats["empty_summaries"] == 1

    def test_get_unread_articles(self, db_manager):
        """Test getting unread articles."""
        articles = db_manager.get_unread_articles(limit=3)
        
        assert len(articles) == 3
        # Should be ordered by published date (newest first)
        assert articles[0]["id"] == 4  # 2025-06-16T13:00:00
        assert articles[1]["id"] == 3  # 2025-06-16T12:00:00
        assert articles[2]["id"] == 2  # 2025-06-16T11:00:00
        
        # Check that all articles have required fields
        for article in articles:
            assert "id" in article
            assert "title" in article
            assert "link" in article
            assert "summary" in article
            assert "detected_language" in article
            assert "is_translated" in article

    def test_get_unread_articles_with_limit(self, db_manager):
        """Test getting unread articles with specific limit."""
        articles = db_manager.get_unread_articles(limit=1)
        assert len(articles) == 1
        assert articles[0]["id"] == 4

    def test_get_article_by_id(self, db_manager):
        """Test getting specific article by ID."""
        article = db_manager.get_article_by_id(1)
        
        assert article is not None
        assert article["id"] == 1
        assert article["title"] == "Test Japanese Article"
        assert article["summary"] == "これは日本語のテスト記事です。"

    def test_get_article_by_id_not_found(self, db_manager):
        """Test getting non-existent article by ID."""
        article = db_manager.get_article_by_id(999)
        assert article is None

    def test_mark_article_as_read(self, db_manager):
        """Test marking article as read."""
        # Article 1 should not be read initially
        assert db_manager.get_read_count() == 1
        
        # Mark article 1 as read
        success = db_manager.mark_article_as_read(1)
        assert success is True
        
        # Read count should increase
        assert db_manager.get_read_count() == 2
        
        # Article should not appear in unread list
        unread_articles = db_manager.get_unread_articles()
        unread_ids = [article["id"] for article in unread_articles]
        assert 1 not in unread_ids

    def test_mark_article_as_read_duplicate(self, db_manager):
        """Test marking already read article as read."""
        # Mark article twice
        db_manager.mark_article_as_read(1)
        success = db_manager.mark_article_as_read(1)
        
        # Should handle duplicate gracefully
        assert success is True
        assert db_manager.get_read_count() == 2  # Should not increase

    def test_mark_article_as_read_invalid_id(self, db_manager):
        """Test marking non-existent article as read."""
        success = db_manager.mark_article_as_read(999)
        assert success is True  # Method doesn't validate article existence

    def test_update_article_summary(self, db_manager):
        """Test updating article summary."""
        new_summary = "Updated test summary"
        success = db_manager.update_article_summary(1, new_summary)
        assert success is True
        
        # Verify update
        article = db_manager.get_article_by_id(1)
        assert article["summary"] == new_summary

    def test_update_article_summary_invalid_id(self, db_manager):
        """Test updating summary for non-existent article."""
        success = db_manager.update_article_summary(999, "New summary")
        assert success is True  # SQLite doesn't fail on UPDATE with no matches

    def test_update_article_language_info(self, db_manager):
        """Test updating article language information."""
        success = db_manager.update_article_language_info(
            article_id=3,
            detected_language="en",
            original_summary="Original English text",
            is_translated=True
        )
        assert success is True
        
        # Verify update
        article = db_manager.get_article_by_id(3)
        assert article["detected_language"] == "en"
        assert article["original_summary"] == "Original English text"
        assert article["is_translated"] == 1

    def test_get_articles_with_empty_summaries(self, db_manager):
        """Test getting articles with empty summaries."""
        articles = db_manager.get_articles_with_empty_summaries(limit=10)
        
        assert len(articles) == 1
        assert articles[0]["id"] == 4
        assert articles[0]["summary"] == ""

    def test_get_untranslated_articles(self, db_manager):
        """Test getting articles that need translation."""
        # First mark some articles as English
        db_manager.update_article_language_info(2, "en", None, False)
        db_manager.update_article_language_info(3, "en", None, False)
        
        articles = db_manager.get_untranslated_articles(limit=10)
        
        assert len(articles) == 2
        article_ids = [article["id"] for article in articles]
        assert 2 in article_ids
        assert 3 in article_ids

    def test_get_translation_stats(self, db_manager):
        """Test getting translation statistics."""
        # Set up some translation data
        db_manager.update_article_language_info(1, "ja", None, False)
        db_manager.update_article_language_info(2, "en", None, False)
        db_manager.update_article_language_info(3, "en", "Original", True)
        
        stats = db_manager.get_translation_stats()
        
        assert "language_counts" in stats
        assert "translated_articles" in stats
        assert "untranslated_articles" in stats
        
        # Should have 2 English articles, 1 Japanese
        assert stats["language_counts"].get("en", 0) >= 2
        assert stats["language_counts"].get("ja", 0) >= 1
        assert stats["translated_articles"] >= 1
        assert stats["untranslated_articles"] >= 1

    def test_database_connection_error_handling(self, test_db_path):
        """Test database connection error handling."""
        # Create database manager with invalid path
        db = DatabaseManager("/invalid/path/database.db")
        
        # Should handle connection errors gracefully
        with pytest.raises(Exception):
            with db.get_connection():
                pass

    def test_database_transaction_rollback(self, db_manager):
        """Test database transaction rollback on error."""
        with pytest.raises(Exception):
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                # Valid operation
                cursor.execute("UPDATE articles SET title = ? WHERE id = ?", ("New Title", 1))
                # Invalid operation to trigger rollback
                cursor.execute("INVALID SQL STATEMENT")
        
        # Verify that the valid operation was rolled back
        article = db_manager.get_article_by_id(1)
        assert article["title"] == "Test Japanese Article"  # Should be unchanged

    def test_concurrent_database_access(self, db_manager):
        """Test concurrent database access."""
        # This is a basic test - in a real scenario you'd use threading
        with db_manager.get_connection() as conn1:
            with db_manager.get_connection() as conn2:
                cursor1 = conn1.cursor()
                cursor2 = conn2.cursor()
                
                # Both connections should work
                cursor1.execute("SELECT COUNT(*) FROM articles")
                count1 = cursor1.fetchone()[0]
                
                cursor2.execute("SELECT COUNT(*) FROM articles")
                count2 = cursor2.fetchone()[0]
                
                assert count1 == count2 == 5