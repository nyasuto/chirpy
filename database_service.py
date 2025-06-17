"""
Type-safe database service layer using SQLModel.

This module provides a modern replacement for db_utils.py with:
- Type-safe operations
- Better error handling
- Consistent API patterns
- Performance optimizations
"""

import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlmodel import Session, func, or_, select

from config import get_logger
from db_models import (
    Article,
    ArticleQueries,
    ReadArticle,
    ReadingSession,
    SessionQueries,
    create_database_engine,
    ensure_tables_exist,
)


class DatabaseService:
    """
    Type-safe database service replacing DatabaseManager.

    Provides the same interface as the original DatabaseManager
    but with improved type safety and modern ORM features.
    """

    def __init__(self, database_path: str):
        """Initialize database service with SQLModel engine."""
        self.database_path = database_path
        self.logger = get_logger(__name__)

        # Ensure database file exists
        db_path = Path(database_path)
        if not db_path.exists():
            self.logger.error(f"Database not found: {database_path}")
            raise FileNotFoundError(f"Database not found: {database_path}")

        # Create engine and ensure tables exist
        self.engine = create_database_engine(database_path)
        ensure_tables_exist(self.engine)

        self.logger.info(f"Database service initialized: {database_path}")

    def get_database_stats(self) -> dict[str, int]:
        """Get database statistics with type safety."""
        with Session(self.engine) as session:
            # Total articles
            total_articles = session.exec(select(func.count(Article.id))).one()

            # Read articles
            read_articles = session.exec(select(func.count(ReadArticle.id))).one()

            # Unread articles using subquery
            unread_articles = session.exec(
                select(func.count(Article.id))
                .outerjoin(ReadArticle, Article.id == ReadArticle.article_id)
                .where(ReadArticle.article_id.is_(None))
                .where(Article.summary.is_not(None))
                .where(Article.summary != "")
            ).one()

            # Empty summaries
            empty_summaries = session.exec(
                select(func.count(Article.id)).where(
                    or_(
                        Article.summary.is_(None),
                        Article.summary == "",
                        Article.summary == "No summary available",
                    )
                )
            ).one()

            return {
                "total_articles": total_articles,
                "read_articles": read_articles,
                "unread_articles": unread_articles,
                "empty_summaries": empty_summaries,
            }

    def get_unread_articles(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get unread articles with improved type safety."""
        with Session(self.engine) as session:
            stmt = ArticleQueries.get_unread_articles(limit)
            articles = session.exec(stmt).all()

            # Convert SQLModel objects to dictionaries for compatibility
            return [
                {
                    "id": article.id,
                    "title": article.title,
                    "link": article.link,
                    "published": article.published,
                    "summary": article.summary,
                    "embedded": article.embedded,
                    "detected_language": article.detected_language,
                    "original_summary": article.original_summary,
                    "is_translated": article.is_translated,
                }
                for article in articles
            ]

    def get_articles_with_empty_summaries(
        self, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get articles needing summary processing."""
        with Session(self.engine) as session:
            stmt = ArticleQueries.get_articles_with_empty_summaries(limit)
            articles = session.exec(stmt).all()

            return [
                {
                    "id": article.id,
                    "title": article.title,
                    "link": article.link,
                    "published": article.published,
                    "summary": article.summary,
                    "embedded": article.embedded,
                }
                for article in articles
            ]

    def get_untranslated_articles(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get articles needing translation."""
        with Session(self.engine) as session:
            stmt = ArticleQueries.get_untranslated_articles(limit)
            articles = session.exec(stmt).all()

            return [
                {
                    "id": article.id,
                    "title": article.title,
                    "link": article.link,
                    "published": article.published,
                    "summary": article.summary,
                    "detected_language": article.detected_language,
                    "original_summary": article.original_summary,
                    "is_translated": article.is_translated,
                }
                for article in articles
            ]

    def mark_article_as_read(self, article_id: int) -> bool:
        """Mark article as read with proper error handling."""
        try:
            with Session(self.engine) as session:
                # Use INSERT OR IGNORE pattern
                existing = session.exec(
                    select(ReadArticle).where(ReadArticle.article_id == article_id)
                ).first()

                if not existing:
                    read_record = ReadArticle(
                        article_id=article_id, read_at=datetime.now()
                    )
                    session.add(read_record)
                    session.commit()

                return True

        except Exception as e:
            self.logger.error(f"Error marking article {article_id} as read: {e}")
            return False

    def update_article_summary(self, article_id: int, summary: str) -> bool:
        """Update article summary with type safety."""
        try:
            with Session(self.engine) as session:
                article = session.get(Article, article_id)
                if article:
                    article.summary = summary
                    session.add(article)
                    session.commit()
                    return True
                return False

        except Exception as e:
            self.logger.error(f"Error updating summary for article {article_id}: {e}")
            return False

    def update_article_language_info(
        self,
        article_id: int,
        detected_language: str,
        original_summary: str | None = None,
        is_translated: bool = False,
    ) -> bool:
        """Update article language information."""
        try:
            with Session(self.engine) as session:
                article = session.get(Article, article_id)
                if article:
                    article.detected_language = detected_language
                    if original_summary is not None:
                        article.original_summary = original_summary
                    article.is_translated = is_translated
                    session.add(article)
                    session.commit()
                    return True
                return False

        except Exception as e:
            self.logger.error(
                f"Error updating language info for article {article_id}: {e}"
            )
            return False

    # Session management methods
    def save_reading_session(self, session_data: dict[str, Any]) -> bool:
        """Save or update reading session."""
        try:
            with Session(self.engine) as session:
                reading_session = session.get(
                    ReadingSession, session_data["session_id"]
                )

                if reading_session:
                    # Update existing session
                    for key, value in session_data.items():
                        if hasattr(reading_session, key):
                            setattr(reading_session, key, value)
                else:
                    # Create new session
                    reading_session = ReadingSession(**session_data)

                session.add(reading_session)
                session.commit()
                return True

        except Exception as e:
            self.logger.error(f"Error saving reading session: {e}")
            return False

    def get_active_sessions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get active reading sessions."""
        with Session(self.engine) as session:
            stmt = SessionQueries.get_active_sessions(limit)
            sessions = session.exec(stmt).all()

            return [
                {
                    "session_id": s.session_id,
                    "created_at": s.created_at,
                    "updated_at": s.updated_at,
                    "session_name": s.session_name,
                    "completed": s.completed,
                    "articles_completed": s.articles_completed,
                    "total_reading_time": s.total_reading_time,
                    "total_articles": len(s.article_ids),
                    "article_ids": s.article_ids,
                    "current_index": s.current_index,
                    "metadata": s.session_metadata,
                }
                for s in sessions
            ]

    def close(self) -> None:
        """Close database connections."""
        if hasattr(self, "engine"):
            self.engine.dispose()
        self.logger.info("Database service closed")


# Migration compatibility layer
class DatabaseManager(DatabaseService):
    """
    Compatibility wrapper for existing DatabaseManager usage.

    This allows gradual migration by providing the same interface
    as the original DatabaseManager while using SQLModel underneath.
    """

    def __init__(self, database_path: str):
        """Initialize with compatibility for existing code."""
        super().__init__(database_path)
        self.logger.info("Using SQLModel-based DatabaseManager")


# Performance comparison utilities
def benchmark_queries(database_path: str, iterations: int = 100) -> dict[str, float]:
    """
    Benchmark raw SQL vs SQLModel performance.

    This helps validate that the ORM migration doesn't significantly
    impact performance for the existing use cases.
    """

    # Raw SQL timing
    raw_sql_time = 0.0
    for _ in range(iterations):
        start = time.time()
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.id, a.title, a.link, a.published, a.summary, a.embedded,
                   a.detected_language, a.original_summary, a.is_translated
            FROM articles a
            LEFT JOIN read_articles r ON a.id = r.article_id
            WHERE r.article_id IS NULL
            AND a.summary IS NOT NULL
            AND a.summary != ''
            ORDER BY a.published DESC
            LIMIT 50
        """)
        cursor.fetchall()
        conn.close()
        raw_sql_time += time.time() - start

    # SQLModel timing
    sqlmodel_time = 0.0
    db_service = DatabaseService(database_path)
    for _ in range(iterations):
        start = time.time()
        db_service.get_unread_articles(50)
        sqlmodel_time += time.time() - start
    db_service.close()

    return {
        "raw_sql_avg_ms": (raw_sql_time / iterations) * 1000,
        "sqlmodel_avg_ms": (sqlmodel_time / iterations) * 1000,
        "performance_ratio": sqlmodel_time / raw_sql_time,
    }
