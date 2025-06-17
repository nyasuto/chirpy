"""Tests for DatabaseService/DatabaseManager operations."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from sqlmodel import Session, select

from database_service import DatabaseManager, DatabaseService
from db_models import Article, ReadArticle, ReadingSession


class TestDatabaseService:
    """Test suite for DatabaseService class."""

    @pytest.mark.unit
    def test_database_service_initialization_success(self, test_db_path):
        """Test successful DatabaseService initialization."""
        # Create empty database file
        Path(test_db_path).touch()

        db_service = DatabaseService(test_db_path)

        assert db_service.database_path == test_db_path
        assert db_service.engine is not None
        assert db_service.logger is not None

        db_service.close()

    @pytest.mark.unit
    def test_database_service_initialization_missing_file(self, temp_dir):
        """Test DatabaseService initialization with missing database file."""
        missing_db_path = str(temp_dir / "missing.db")

        with pytest.raises(FileNotFoundError) as excinfo:
            DatabaseService(missing_db_path)

        assert "Database not found" in str(excinfo.value)
        assert missing_db_path in str(excinfo.value)

    @pytest.mark.unit
    def test_database_manager_compatibility_wrapper(self, test_db_path):
        """Test DatabaseManager compatibility wrapper."""
        # Create empty database file
        Path(test_db_path).touch()

        db_manager = DatabaseManager(test_db_path)

        # Should have same interface as DatabaseService
        assert isinstance(db_manager, DatabaseService)
        assert db_manager.database_path == test_db_path

        db_manager.close()

    @pytest.mark.unit
    def test_get_database_stats_empty_database(self, test_db_path):
        """Test getting stats from empty database."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        stats = db_service.get_database_stats()

        assert isinstance(stats, dict)
        assert stats["total_articles"] == 0
        assert stats["read_articles"] == 0
        assert stats["unread_articles"] == 0
        assert stats["empty_summaries"] == 0

        db_service.close()

    @pytest.mark.unit
    def test_get_database_stats_with_articles(self, test_db_path):
        """Test getting stats with sample articles."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        # Add sample articles
        with Session(db_service.engine) as session:
            articles = [
                Article(
                    id=1,
                    title="Article 1",
                    link="https://example.com/1",
                    published="2023-01-01 10:00:00",
                    summary="First article summary",
                ),
                Article(
                    id=2,
                    title="Article 2",
                    link="https://example.com/2",
                    published="2023-01-02 10:00:00",
                    summary="",  # Empty summary
                ),
                Article(
                    id=3,
                    title="Article 3",
                    link="https://example.com/3",
                    published="2023-01-03 10:00:00",
                    summary="Third article summary",
                ),
            ]
            for article in articles:
                session.add(article)

            # Mark article 1 as read
            session.add(ReadArticle(article_id=1, read_at=datetime.now()))
            session.commit()

        stats = db_service.get_database_stats()

        assert stats["total_articles"] == 3
        assert stats["read_articles"] == 1
        assert stats["unread_articles"] == 1  # Article 3 (Article 2 has empty summary)
        assert stats["empty_summaries"] == 1  # Article 2

        db_service.close()

    @pytest.mark.unit
    def test_get_unread_articles_empty_database(self, test_db_path):
        """Test getting unread articles from empty database."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        articles = db_service.get_unread_articles()

        assert isinstance(articles, list)
        assert len(articles) == 0

        db_service.close()

    @pytest.mark.unit
    def test_get_unread_articles_with_data(self, test_db_path):
        """Test getting unread articles with sample data."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        # Add sample articles
        with Session(db_service.engine) as session:
            articles = [
                Article(
                    id=1,
                    title="Read Article",
                    link="https://example.com/1",
                    published="2023-01-01 10:00:00",
                    summary="This article was read",
                ),
                Article(
                    id=2,
                    title="Unread Article",
                    link="https://example.com/2",
                    published="2023-01-02 10:00:00",
                    summary="This article is unread",
                ),
                Article(
                    id=3,
                    title="Empty Summary Article",
                    link="https://example.com/3",
                    published="2023-01-03 10:00:00",
                    summary="",  # Should be excluded
                ),
            ]
            for article in articles:
                session.add(article)

            # Mark article 1 as read
            session.add(ReadArticle(article_id=1, read_at=datetime.now()))
            session.commit()

        unread_articles = db_service.get_unread_articles()

        assert len(unread_articles) == 1
        assert unread_articles[0]["id"] == 2
        assert unread_articles[0]["title"] == "Unread Article"
        assert unread_articles[0]["summary"] == "This article is unread"

        db_service.close()

    @pytest.mark.unit
    def test_get_unread_articles_limit(self, test_db_path):
        """Test get_unread_articles respects limit parameter."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        # Add multiple unread articles
        with Session(db_service.engine) as session:
            for i in range(5):
                article = Article(
                    id=i + 1,
                    title=f"Article {i + 1}",
                    link=f"https://example.com/{i + 1}",
                    published=f"2023-01-0{i + 1} 10:00:00",
                    summary=f"Summary for article {i + 1}",
                )
                session.add(article)
            session.commit()

        # Test limit=2
        articles = db_service.get_unread_articles(limit=2)
        assert len(articles) == 2

        # Test limit=10 (should return all 5)
        articles = db_service.get_unread_articles(limit=10)
        assert len(articles) == 5

        db_service.close()

    @pytest.mark.unit
    def test_get_articles_with_empty_summaries(self, test_db_path):
        """Test getting articles with empty summaries."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        # Add articles with various summary states
        with Session(db_service.engine) as session:
            articles = [
                Article(
                    id=1,
                    title="Good Article",
                    link="https://example.com/1",
                    summary="Good summary",
                ),
                Article(
                    id=2,
                    title="Empty Summary Article",
                    link="https://example.com/2",
                    summary="",
                ),
                Article(
                    id=3,
                    title="None Summary Article",
                    link="https://example.com/3",
                    summary=None,
                ),
                Article(
                    id=4,
                    title="No Summary Available Article",
                    link="https://example.com/4",
                    summary="No summary available",
                ),
            ]
            for article in articles:
                session.add(article)
            session.commit()

        empty_articles = db_service.get_articles_with_empty_summaries()

        assert len(empty_articles) == 3
        empty_ids = [article["id"] for article in empty_articles]
        assert 2 in empty_ids  # Empty string
        assert 3 in empty_ids  # None
        assert 4 in empty_ids  # "No summary available"
        assert 1 not in empty_ids  # Good summary

        db_service.close()

    @pytest.mark.unit
    def test_get_untranslated_articles(self, test_db_path):
        """Test getting articles needing translation."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        # Add articles with various language states
        with Session(db_service.engine) as session:
            articles = [
                Article(
                    id=1,
                    title="English Article",
                    link="https://example.com/1",
                    summary="English summary",
                    detected_language="en",
                ),
                Article(
                    id=2,
                    title="Unknown Language Article",
                    link="https://example.com/2",
                    summary="Unknown language summary",
                    detected_language="unknown",
                ),
                Article(
                    id=3,
                    title="Another Unknown Article",
                    link="https://example.com/3",
                    summary="Another unknown summary",
                    detected_language="unknown",
                ),
                Article(
                    id=4,
                    title="Empty Summary Unknown",
                    link="https://example.com/4",
                    summary="",  # Should be excluded
                    detected_language="unknown",
                ),
            ]
            for article in articles:
                session.add(article)
            session.commit()

        untranslated = db_service.get_untranslated_articles()

        assert len(untranslated) == 2
        untranslated_ids = [article["id"] for article in untranslated]
        assert 2 in untranslated_ids
        assert 3 in untranslated_ids
        assert 1 not in untranslated_ids  # Known language
        assert 4 not in untranslated_ids  # Empty summary

        db_service.close()

    @pytest.mark.unit
    def test_mark_article_as_read_success(self, test_db_path):
        """Test successfully marking article as read."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        # Add test article
        with Session(db_service.engine) as session:
            article = Article(
                id=1,
                title="Test Article",
                link="https://example.com/1",
                summary="Test summary",
            )
            session.add(article)
            session.commit()

        # Mark as read
        result = db_service.mark_article_as_read(1)
        assert result is True

        # Verify it was marked as read
        with Session(db_service.engine) as session:
            read_record = session.exec(
                select(ReadArticle).where(ReadArticle.article_id == 1)
            ).first()
            assert read_record is not None
            assert read_record.article_id == 1
            assert isinstance(read_record.read_at, datetime)

        db_service.close()

    @pytest.mark.unit
    def test_mark_article_as_read_duplicate(self, test_db_path):
        """Test marking already read article doesn't create duplicate."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        # Add test article
        with Session(db_service.engine) as session:
            article = Article(
                id=1,
                title="Test Article",
                link="https://example.com/1",
                summary="Test summary",
            )
            session.add(article)
            session.commit()

        # Mark as read twice
        result1 = db_service.mark_article_as_read(1)
        result2 = db_service.mark_article_as_read(1)

        assert result1 is True
        assert result2 is True

        # Verify only one record exists
        with Session(db_service.engine) as session:
            count = session.exec(
                select(ReadArticle).where(ReadArticle.article_id == 1)
            ).all()
            assert len(count) == 1

        db_service.close()

    @pytest.mark.unit
    def test_mark_article_as_read_error_handling(self, test_db_path):
        """Test error handling in mark_article_as_read."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        # Mock Session to raise exception
        with patch("database_service.Session") as mock_session:
            mock_session.side_effect = Exception("Database error")

            result = db_service.mark_article_as_read(1)
            assert result is False

        db_service.close()

    @pytest.mark.unit
    def test_update_article_summary_success(self, test_db_path):
        """Test successfully updating article summary."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        # Add test article
        with Session(db_service.engine) as session:
            article = Article(
                id=1,
                title="Test Article",
                link="https://example.com/1",
                summary="Original summary",
            )
            session.add(article)
            session.commit()

        # Update summary
        new_summary = "Updated summary with more details"
        result = db_service.update_article_summary(1, new_summary)
        assert result is True

        # Verify update
        with Session(db_service.engine) as session:
            article = session.get(Article, 1)
            assert article.summary == new_summary

        db_service.close()

    @pytest.mark.unit
    def test_update_article_summary_nonexistent(self, test_db_path):
        """Test updating summary for nonexistent article."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        result = db_service.update_article_summary(999, "New summary")
        assert result is False

        db_service.close()

    @pytest.mark.unit
    def test_update_article_language_info_success(self, test_db_path):
        """Test successfully updating article language information."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        # Add test article
        with Session(db_service.engine) as session:
            article = Article(
                id=1,
                title="Test Article",
                link="https://example.com/1",
                summary="Test summary",
                detected_language="unknown",
            )
            session.add(article)
            session.commit()

        # Update language info
        result = db_service.update_article_language_info(
            1,
            detected_language="en",
            original_summary="Original text",
            is_translated=True,
        )
        assert result is True

        # Verify update
        with Session(db_service.engine) as session:
            article = session.get(Article, 1)
            assert article.detected_language == "en"
            assert article.original_summary == "Original text"
            assert article.is_translated is True

        db_service.close()

    @pytest.mark.unit
    def test_update_article_language_info_partial(self, test_db_path):
        """Test updating only some language info fields."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        # Add test article
        with Session(db_service.engine) as session:
            article = Article(
                id=1,
                title="Test Article",
                link="https://example.com/1",
                summary="Test summary",
                detected_language="unknown",
                original_summary=None,
                is_translated=False,
            )
            session.add(article)
            session.commit()

        # Update only detected_language
        result = db_service.update_article_language_info(1, "ja")
        assert result is True

        # Verify selective update
        with Session(db_service.engine) as session:
            article = session.get(Article, 1)
            assert article.detected_language == "ja"
            assert article.original_summary is None  # Unchanged
            assert article.is_translated is False  # Unchanged

        db_service.close()

    @pytest.mark.unit
    def test_save_reading_session_new(self, test_db_path):
        """Test saving new reading session."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        session_data = {
            "session_id": "test_session_123",
            "created_at": 1640995200.0,
            "updated_at": 1640995200.0,
            "article_ids": [1, 2, 3],
            "current_index": 0,
            "completed": False,
            "total_reading_time": 0.0,
            "words_read": 0,
            "articles_completed": 0,
            "session_name": "Test Session",
            "session_metadata": {},
        }

        result = db_service.save_reading_session(session_data)
        assert result is True

        # Verify session was saved
        with Session(db_service.engine) as session:
            reading_session = session.get(ReadingSession, "test_session_123")
            assert reading_session is not None
            assert reading_session.session_name == "Test Session"
            assert reading_session.article_ids == [1, 2, 3]
            assert reading_session.completed is False

        db_service.close()

    @pytest.mark.unit
    def test_save_reading_session_update(self, test_db_path):
        """Test updating existing reading session."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        # Create initial session
        initial_data = {
            "session_id": "test_session_123",
            "created_at": 1640995200.0,
            "updated_at": 1640995200.0,
            "article_ids": [1, 2, 3],
            "current_index": 0,
            "completed": False,
            "total_reading_time": 0.0,
            "words_read": 0,
            "articles_completed": 0,
            "session_name": "Initial Session",
            "session_metadata": {},
        }
        db_service.save_reading_session(initial_data)

        # Update session
        update_data = {
            "session_id": "test_session_123",
            "current_index": 2,
            "articles_completed": 2,
            "total_reading_time": 150.5,
            "session_name": "Updated Session",
        }
        result = db_service.save_reading_session(update_data)
        assert result is True

        # Verify update
        with Session(db_service.engine) as session:
            reading_session = session.get(ReadingSession, "test_session_123")
            assert reading_session.session_name == "Updated Session"
            assert reading_session.current_index == 2
            assert reading_session.articles_completed == 2
            assert reading_session.total_reading_time == 150.5

        db_service.close()

    @pytest.mark.unit
    def test_get_active_sessions_empty(self, test_db_path):
        """Test getting active sessions from empty database."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        sessions = db_service.get_active_sessions()

        assert isinstance(sessions, list)
        assert len(sessions) == 0

        db_service.close()

    @pytest.mark.unit
    def test_get_active_sessions_with_data(self, test_db_path):
        """Test getting active sessions with sample data."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        # Add test sessions
        session_data_1 = {
            "session_id": "active_session",
            "created_at": 1640995200.0,
            "updated_at": 1640995300.0,
            "article_ids": [1, 2, 3],
            "current_index": 1,
            "completed": False,  # Active
            "total_reading_time": 0.0,
            "words_read": 0,
            "articles_completed": 0,
            "session_name": "Active Session",
            "session_metadata": {},
        }

        session_data_2 = {
            "session_id": "completed_session",
            "created_at": 1640995100.0,
            "updated_at": 1640995400.0,
            "article_ids": [4, 5, 6],
            "current_index": 3,
            "completed": True,  # Completed
            "total_reading_time": 300.0,
            "words_read": 1500,
            "articles_completed": 3,
            "session_name": "Completed Session",
            "session_metadata": {},
        }

        db_service.save_reading_session(session_data_1)
        db_service.save_reading_session(session_data_2)

        active_sessions = db_service.get_active_sessions()

        assert len(active_sessions) == 1
        assert active_sessions[0]["session_id"] == "active_session"
        assert active_sessions[0]["session_name"] == "Active Session"
        assert active_sessions[0]["completed"] is False
        assert active_sessions[0]["total_articles"] == 3

        db_service.close()

    @pytest.mark.unit
    def test_close_database_service(self, test_db_path):
        """Test closing database service properly."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        # Verify engine exists
        assert hasattr(db_service, "engine")

        # Close service
        db_service.close()

        # Engine should still exist but be disposed
        assert hasattr(db_service, "engine")

    @pytest.mark.unit
    def test_database_service_error_logging(self, test_db_path):
        """Test that database errors are properly logged."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        # Mock the logger directly on the service instance
        mock_logger = Mock()
        db_service.logger = mock_logger

        # Test error in mark_article_as_read
        with patch("database_service.Session") as mock_session:
            mock_session.side_effect = Exception("Test error")
            result = db_service.mark_article_as_read(1)

            assert result is False
            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args[0][0]
            assert "Error marking article 1 as read" in error_call

        db_service.close()

    @pytest.mark.unit
    def test_article_dictionary_conversion(self, test_db_path):
        """Test that SQLModel objects are properly converted to dictionaries."""
        Path(test_db_path).touch()
        db_service = DatabaseService(test_db_path)

        # Add test article with all fields
        with Session(db_service.engine) as session:
            article = Article(
                id=1,
                title="Complete Article",
                link="https://example.com/1",
                published="2023-01-01 10:00:00",
                summary="Complete summary",
                embedded=1,
                detected_language="en",
                original_summary="Original text",
                is_translated=True,
            )
            session.add(article)
            session.commit()

        articles = db_service.get_unread_articles()

        assert len(articles) == 1
        article_dict = articles[0]

        # Verify all expected fields are present and correct type
        expected_fields = [
            "id",
            "title",
            "link",
            "published",
            "summary",
            "embedded",
            "detected_language",
            "original_summary",
            "is_translated",
        ]

        for field in expected_fields:
            assert field in article_dict

        assert article_dict["id"] == 1
        assert article_dict["title"] == "Complete Article"
        assert article_dict["is_translated"] is True
        assert isinstance(article_dict, dict)

        db_service.close()
