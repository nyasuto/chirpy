"""
Database utilities for Chirpy RSS reader.

Provides functions for managing articles and read tracking.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from config import get_logger


class DatabaseManager:
    """Manages database operations for Chirpy."""

    def __init__(self, db_path: str):
        """Initialize database manager."""
        self.db_path = Path(db_path)
        self.logger = get_logger(__name__)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn

    def get_unread_articles(self, limit: int = 3) -> list[dict[str, Any]]:
        """
        Get unread articles ordered by published date (newest first).

        Args:
            limit: Maximum number of articles to return

        Returns:
            List of article dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT a.id, a.title, a.link, a.published, a.summary, a.embedded
                FROM articles a
                LEFT JOIN read_articles r ON a.id = r.article_id
                WHERE r.article_id IS NULL
                AND a.summary IS NOT NULL
                AND a.summary != ''
                ORDER BY a.published DESC
                LIMIT ?
            """

            cursor.execute(query, (limit,))
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def mark_article_as_read(self, article_id: int) -> bool:
        """
        Mark an article as read.

        Args:
            article_id: ID of the article to mark as read

        Returns:
            True if successful, False otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO read_articles (article_id, read_at)
                    VALUES (?, ?)
                """,
                    (article_id, datetime.now().isoformat()),
                )

                conn.commit()
                return cursor.rowcount > 0

            except sqlite3.Error as e:
                self.logger.error(f"Error marking article as read: {e}")
                return False

    def is_article_read(self, article_id: int) -> bool:
        """
        Check if an article has been read.

        Args:
            article_id: ID of the article to check

        Returns:
            True if article has been read, False otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 1 FROM read_articles WHERE article_id = ?
            """,
                (article_id,),
            )

            return cursor.fetchone() is not None

    def get_read_count(self) -> int:
        """Get total number of read articles."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM read_articles")
            result = cursor.fetchone()
            return int(result[0]) if result else 0

    def get_total_count(self) -> int:
        """Get total number of articles."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            result = cursor.fetchone()
            return int(result[0]) if result else 0

    def get_unread_count(self) -> int:
        """Get number of unread articles with content."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*)
                FROM articles a
                LEFT JOIN read_articles r ON a.id = r.article_id
                WHERE r.article_id IS NULL
                AND a.summary IS NOT NULL
                AND a.summary != ''
            """)
            result = cursor.fetchone()
            return int(result[0]) if result else 0

    def get_article_by_id(self, article_id: int) -> dict[str, Any] | None:
        """
        Get article by ID.

        Args:
            article_id: ID of the article

        Returns:
            Article dictionary or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, title, link, published, summary, embedded
                FROM articles WHERE id = ?
            """,
                (article_id,),
            )

            row = cursor.fetchone()
            return dict(row) if row else None

    def update_article_summary(self, article_id: int, summary: str) -> bool:
        """
        Update article summary.

        Args:
            article_id: ID of the article to update
            summary: New summary content

        Returns:
            True if successful, False otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute(
                    """
                    UPDATE articles
                    SET summary = ?
                    WHERE id = ?
                """,
                    (summary, article_id),
                )

                conn.commit()
                return cursor.rowcount > 0

            except sqlite3.Error as e:
                self.logger.error(f"Error updating article summary: {e}")
                return False

    def get_articles_with_empty_summaries(
        self, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get articles with empty summaries that need content fetching.

        Args:
            limit: Maximum number of articles to return

        Returns:
            List of article dictionaries with empty summaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT id, title, link, published, summary, embedded
                FROM articles
                WHERE (summary IS NULL OR summary = '' OR
                       summary = 'No summary available')
                AND link IS NOT NULL
                AND link != ''
                ORDER BY published DESC
                LIMIT ?
            """

            cursor.execute(query, (limit,))
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def get_empty_summaries_count(self) -> int:
        """Get number of articles with empty summaries."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*)
                FROM articles
                WHERE (summary IS NULL OR summary = '' OR
                       summary = 'No summary available')
                AND link IS NOT NULL
                AND link != ''
            """)
            result = cursor.fetchone()
            return int(result[0]) if result else 0

    def update_article_language_info(
        self,
        article_id: int,
        detected_language: str,
        original_summary: str | None = None,
        is_translated: bool = False,
    ) -> bool:
        """
        Update article language detection and translation information.

        Args:
            article_id: ID of the article to update
            detected_language: Detected language code (e.g., 'en', 'ja')
            original_summary: Original summary before translation
            is_translated: Whether the current summary is translated

        Returns:
            True if update was successful, False otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                params = (
                    detected_language,
                    original_summary,
                    int(is_translated),
                    article_id,
                )
                cursor.execute(
                    """
                    UPDATE articles
                    SET detected_language = ?,
                        original_summary = ?,
                        is_translated = ?
                    WHERE id = ?
                    """,
                    params,
                )

                conn.commit()
                return cursor.rowcount > 0

            except sqlite3.Error as e:
                self.logger.error(f"Error updating article language info: {e}")
                return False

    def get_articles_by_language(
        self, language: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get articles filtered by detected language.

        Args:
            language: Language code to filter by
            limit: Maximum number of articles to return

        Returns:
            List of article dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute(
                    """
                    SELECT id, title, link, published, summary, embedded,
                           detected_language, original_summary, is_translated
                    FROM articles
                    WHERE detected_language = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (language, limit),
                )

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

            except sqlite3.Error as e:
                self.logger.error(f"Error getting articles by language: {e}")
                return []

    def get_untranslated_articles(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get articles that need translation (non-Japanese articles).

        Args:
            limit: Maximum number of articles to return

        Returns:
            List of article dictionaries that need translation
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute(
                    """
                    SELECT id, title, link, published, summary, embedded,
                           detected_language, original_summary, is_translated
                    FROM articles
                    WHERE detected_language != 'ja'
                      AND detected_language != 'unknown'
                      AND is_translated = 0
                      AND summary IS NOT NULL
                      AND summary != ''
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                )

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

            except sqlite3.Error as e:
                self.logger.error(f"Error getting untranslated articles: {e}")
                return []

    def get_translation_stats(self) -> dict[str, Any]:
        """Get translation statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Count by language
            cursor.execute(
                """
                SELECT detected_language, COUNT(*) as count
                FROM articles
                WHERE detected_language != 'unknown'
                GROUP BY detected_language
                """
            )
            language_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # Count translated articles
            cursor.execute("SELECT COUNT(*) FROM articles WHERE is_translated = 1")
            translated_count = cursor.fetchone()[0]

            # Count untranslated non-Japanese articles
            cursor.execute(
                """
                SELECT COUNT(*) FROM articles
                WHERE detected_language != 'ja'
                  AND detected_language != 'unknown'
                  AND is_translated = 0
                """
            )
            untranslated_count = cursor.fetchone()[0]

            return {
                "language_counts": language_counts,
                "translated_articles": translated_count,
                "untranslated_articles": untranslated_count,
            }

    def get_database_stats(self) -> dict[str, int]:
        """Get database statistics."""
        return {
            "total_articles": self.get_total_count(),
            "read_articles": self.get_read_count(),
            "unread_articles": self.get_unread_count(),
            "empty_summaries": self.get_empty_summaries_count(),
        }
