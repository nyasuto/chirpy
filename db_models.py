"""
Database models using SQLModel for type-safe ORM operations.

This module defines the database schema using SQLModel, providing:
- Type-safe database operations
- Pydantic validation
- SQLAlchemy Core compatibility
- Modern Python type hints
"""

from datetime import datetime
from typing import Any

from sqlmodel import JSON, Column, Field, SQLModel, create_engine, select


class Article(SQLModel, table=True):
    """Article model representing RSS feed articles."""

    __tablename__ = "articles"

    id: int | None = Field(default=None, primary_key=True)
    title: str | None = Field(default=None)
    link: str | None = Field(default=None, unique=True)
    published: str | None = Field(default=None)
    summary: str | None = Field(default=None)
    embedded: int = Field(default=0)
    detected_language: str | None = Field(default="unknown")
    original_summary: str | None = Field(default=None)
    is_translated: bool = Field(default=False)


class ReadArticle(SQLModel, table=True):
    """Read tracking model for articles."""

    __tablename__ = "read_articles"

    id: int | None = Field(default=None, primary_key=True)
    article_id: int = Field(foreign_key="articles.id", unique=True)
    read_at: datetime | None = Field(default_factory=datetime.now)


class ReadingSession(SQLModel, table=True):
    """Reading session model for session management."""

    __tablename__ = "reading_sessions"

    session_id: str = Field(primary_key=True)
    created_at: float = Field(...)
    updated_at: float = Field(...)
    article_ids: list[int] = Field(sa_column=Column(JSON))  # JSON array
    current_index: int = Field(default=0)
    completed: bool = Field(default=False)
    total_reading_time: float = Field(default=0.0)
    words_read: int = Field(default=0)
    articles_completed: int = Field(default=0)
    session_name: str = Field(default="")
    session_metadata: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column("metadata", JSON)
    )


class ReadingHistory(SQLModel, table=True):
    """Individual article reading history."""

    __tablename__ = "reading_history"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="reading_sessions.session_id")
    article_id: int = Field(foreign_key="articles.id")
    started_at: float = Field(...)
    completed_at: float | None = Field(default=None)
    reading_time: float = Field(default=0.0)
    words_count: int = Field(default=0)
    was_skipped: bool = Field(default=False)


class ReadingStats(SQLModel, table=True):
    """Daily reading statistics."""

    __tablename__ = "reading_stats"

    date: str = Field(primary_key=True)  # YYYY-MM-DD format
    sessions_count: int = Field(default=0)
    articles_read: int = Field(default=0)
    total_reading_time: float = Field(default=0.0)
    words_read: int = Field(default=0)
    average_session_time: float = Field(default=0.0)
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = Field(default_factory=lambda: datetime.now().timestamp())


# Database engine and connection management
def create_database_engine(database_path: str) -> Any:
    """Create SQLite engine with proper configuration."""
    return create_engine(
        f"sqlite:///{database_path}",
        echo=False,  # Set to True for SQL logging
        connect_args={
            "check_same_thread": False,  # Allow multi-threading
            "timeout": 30,  # 30 second timeout
        },
    )


def ensure_tables_exist(engine: Any) -> None:
    """Create all tables if they don't exist."""
    SQLModel.metadata.create_all(engine)


# Type-safe query builders for common operations
class ArticleQueries:
    """Type-safe query builders for Article operations."""

    @staticmethod
    def get_unread_articles(limit: int = 50) -> Any:
        """Get unread articles with type safety."""
        return (
            select(Article)
            .outerjoin(ReadArticle, Article.id == ReadArticle.article_id)
            .where(ReadArticle.article_id.is_(None))
            .where(Article.summary.is_not(None))
            .where(Article.summary != "")
            .order_by(Article.published.desc())
            .limit(limit)
        )

    @staticmethod
    def get_articles_with_empty_summaries(limit: int = 10) -> Any:
        """Get articles needing summary processing."""
        return (
            select(Article)
            .where(
                (Article.summary.is_(None))
                | (Article.summary == "")
                | (Article.summary == "No summary available")
            )
            .where(Article.link.is_not(None))
            .where(Article.link != "")
            .order_by(Article.published.desc())
            .limit(limit)
        )

    @staticmethod
    def get_untranslated_articles(limit: int = 10) -> Any:
        """Get articles needing translation."""
        return (
            select(Article)
            .where(Article.detected_language == "unknown")
            .where(Article.summary.is_not(None))
            .where(Article.summary != "")
            .where(Article.summary != "No summary available")
            .limit(limit)
        )


class SessionQueries:
    """Type-safe query builders for Session operations."""

    @staticmethod
    def get_active_sessions(limit: int = 10) -> Any:
        """Get incomplete reading sessions."""
        return (
            select(ReadingSession)
            .where(ReadingSession.completed.is_(False))
            .order_by(ReadingSession.updated_at.desc())
            .limit(limit)
        )

    @staticmethod
    def get_daily_stats(date_str: str) -> Any:
        """Get reading statistics for a specific date."""
        return select(ReadingStats).where(ReadingStats.date == date_str)


# Example usage functions showing migration patterns
def example_migrations() -> None:
    """
    Examples showing how raw SQL would be migrated to SQLModel.

    Before (Raw SQL):
        cursor.execute('''
            SELECT a.id, a.title, a.link, a.published, a.summary, a.embedded,
                   a.detected_language, a.original_summary, a.is_translated
            FROM articles a
            LEFT JOIN read_articles r ON a.id = r.article_id
            WHERE r.article_id IS NULL
            AND a.summary IS NOT NULL
            AND a.summary != ''
            ORDER BY a.published DESC
            LIMIT ?
        ''', (limit,))

    After (SQLModel):
        stmt = ArticleQueries.get_unread_articles(limit)
        result = session.exec(stmt).all()

    Benefits:
    - Type safety with mypy
    - IDE autocompletion
    - Compile-time error checking
    - Reusable query components
    - Automatic SQL generation
    """
    pass
