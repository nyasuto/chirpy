"""
Session management for Chirpy RSS Reader.

Handles saving and restoring reading sessions, tracking progress,
and managing user reading history.
"""

import json
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from config import ChirpyConfig, get_logger


@dataclass
class ReadingSession:
    """Represents a reading session."""

    session_id: str
    created_at: float
    updated_at: float
    article_ids: list[int]
    current_index: int
    completed: bool
    total_reading_time: float
    words_read: int
    articles_completed: int
    session_name: str = ""
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}


class SessionManager:
    """Manages reading sessions and user history."""

    def __init__(self, config: ChirpyConfig):
        """Initialize session manager."""
        self.config = config
        self.logger = get_logger(__name__)
        self.db_path = Path(config.database_path)
        self.current_session: ReadingSession | None = None

        # Ensure sessions table exists
        self._initialize_session_tables()

    def _initialize_session_tables(self) -> None:
        """Create session management tables if they don't exist."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Sessions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reading_sessions (
                        session_id TEXT PRIMARY KEY,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        article_ids TEXT NOT NULL,  -- JSON array of article IDs
                        current_index INTEGER NOT NULL DEFAULT 0,
                        completed BOOLEAN NOT NULL DEFAULT 0,
                        total_reading_time REAL NOT NULL DEFAULT 0.0,
                        words_read INTEGER NOT NULL DEFAULT 0,
                        articles_completed INTEGER NOT NULL DEFAULT 0,
                        session_name TEXT DEFAULT '',
                        metadata TEXT DEFAULT '{}'  -- JSON metadata
                    )
                """)

                # Reading history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reading_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        article_id INTEGER NOT NULL,
                        started_at REAL NOT NULL,
                        completed_at REAL,
                        reading_time REAL DEFAULT 0.0,
                        words_count INTEGER DEFAULT 0,
                        skipped BOOLEAN DEFAULT 0,
                        FOREIGN KEY (session_id)
                            REFERENCES reading_sessions(session_id),
                        FOREIGN KEY (article_id) REFERENCES articles(id)
                    )
                """)

                # Reading statistics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reading_stats (
                        date TEXT PRIMARY KEY,  -- YYYY-MM-DD format
                        sessions_count INTEGER DEFAULT 0,
                        articles_read INTEGER DEFAULT 0,
                        total_reading_time REAL DEFAULT 0.0,
                        words_read INTEGER DEFAULT 0,
                        average_wpm REAL DEFAULT 0.0
                    )
                """)

                conn.commit()
                self.logger.debug("Session management tables initialized")

        except sqlite3.Error as e:
            self.logger.error(f"Failed to initialize session tables: {e}")

    def create_session(
        self, article_ids: list[int], session_name: str = ""
    ) -> ReadingSession:
        """Create a new reading session."""
        session_id = f"session_{int(time.time() * 1000)}"
        current_time = time.time()

        session = ReadingSession(
            session_id=session_id,
            created_at=current_time,
            updated_at=current_time,
            article_ids=article_ids,
            current_index=0,
            completed=False,
            total_reading_time=0.0,
            words_read=0,
            articles_completed=0,
            session_name=session_name
            or (
                "Session "
                + datetime.fromtimestamp(current_time).strftime("%Y-%m-%d %H:%M")
            ),
        )

        self.current_session = session
        self._save_session(session)

        self.logger.info(
            f"Created reading session '{session.session_name}' "
            f"with {len(article_ids)} articles"
        )
        return session

    def _save_session(self, session: ReadingSession) -> bool:
        """Save session to database."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO reading_sessions
                    (session_id, created_at, updated_at, article_ids, current_index,
                     completed, total_reading_time, words_read, articles_completed,
                     session_name, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        session.session_id,
                        session.created_at,
                        session.updated_at,
                        json.dumps(session.article_ids),
                        session.current_index,
                        session.completed,
                        session.total_reading_time,
                        session.words_read,
                        session.articles_completed,
                        session.session_name,
                        json.dumps(session.metadata),
                    ),
                )

                conn.commit()
                return True

        except sqlite3.Error as e:
            self.logger.error(f"Failed to save session {session.session_id}: {e}")
            return False

    def load_session(self, session_id: str) -> ReadingSession | None:
        """Load session from database."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT session_id, created_at, updated_at, article_ids,
                           current_index, completed, total_reading_time, words_read,
                           articles_completed, session_name, metadata
                    FROM reading_sessions
                    WHERE session_id = ?
                """,
                    (session_id,),
                )

                row = cursor.fetchone()
                if not row:
                    return None

                session = ReadingSession(
                    session_id=row[0],
                    created_at=row[1],
                    updated_at=row[2],
                    article_ids=json.loads(row[3]),
                    current_index=row[4],
                    completed=bool(row[5]),
                    total_reading_time=row[6],
                    words_read=row[7],
                    articles_completed=row[8],
                    session_name=row[9],
                    metadata=json.loads(row[10]),
                )

                self.current_session = session
                self.logger.info(f"Loaded session '{session.session_name}'")
                return session

        except (sqlite3.Error, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def list_sessions(
        self, limit: int = 10, include_completed: bool = True
    ) -> list[dict[str, Any]]:
        """List recent reading sessions."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                where_clause = "" if include_completed else "WHERE completed = 0"

                cursor.execute(
                    f"""
                    SELECT session_id, created_at, updated_at, session_name,
                           completed, articles_completed, total_reading_time,
                           json_array_length(article_ids) as total_articles
                    FROM reading_sessions
                    {where_clause}
                    ORDER BY updated_at DESC
                    LIMIT ?
                """,
                    (limit,),
                )

                sessions = []
                for row in cursor.fetchall():
                    sessions.append(
                        {
                            "session_id": row[0],
                            "created_at": row[1],
                            "updated_at": row[2],
                            "session_name": row[3],
                            "completed": bool(row[4]),
                            "articles_completed": row[5],
                            "total_reading_time": row[6],
                            "total_articles": row[7],
                        }
                    )

                return sessions

        except sqlite3.Error as e:
            self.logger.error(f"Failed to list sessions: {e}")
            return []

    def update_session_progress(
        self,
        article_index: int,
        reading_time: float,
        words_count: int,
        completed: bool = False,
    ) -> None:
        """Update current session progress."""
        if not self.current_session:
            return

        self.current_session.current_index = article_index
        self.current_session.total_reading_time += reading_time
        self.current_session.words_read += words_count
        self.current_session.updated_at = time.time()

        if completed:
            self.current_session.articles_completed += 1

        # Check if session is complete
        if article_index >= len(self.current_session.article_ids) - 1:
            self.current_session.completed = True

        self._save_session(self.current_session)

        # Record article reading history
        if self.current_session.current_index < len(self.current_session.article_ids):
            article_id = self.current_session.article_ids[article_index]
            self._record_article_reading(
                article_id, reading_time, words_count, completed
            )

    def _record_article_reading(
        self, article_id: int, reading_time: float, words_count: int, completed: bool
    ) -> None:
        """Record individual article reading in history."""
        if not self.current_session:
            return

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                current_time = time.time()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO reading_history
                    (session_id, article_id, started_at, completed_at,
                     reading_time, words_count, skipped)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.current_session.session_id,
                        article_id,
                        current_time - reading_time,
                        current_time if completed else None,
                        reading_time,
                        words_count,
                        not completed,
                    ),
                )

                conn.commit()

        except sqlite3.Error as e:
            self.logger.error(f"Failed to record article reading: {e}")

    def get_daily_stats(self, date: str | None = None) -> dict[str, Any]:
        """Get reading statistics for a specific date."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT sessions_count, articles_read, total_reading_time,
                           words_read, average_wpm
                    FROM reading_stats
                    WHERE date = ?
                """,
                    (date,),
                )

                row = cursor.fetchone()
                if row:
                    return {
                        "date": date,
                        "sessions_count": row[0],
                        "articles_read": row[1],
                        "total_reading_time": row[2],
                        "words_read": row[3],
                        "average_wpm": row[4],
                    }
                else:
                    return {
                        "date": date,
                        "sessions_count": 0,
                        "articles_read": 0,
                        "total_reading_time": 0.0,
                        "words_read": 0,
                        "average_wpm": 0.0,
                    }

        except sqlite3.Error as e:
            self.logger.error(f"Failed to get daily stats: {e}")
            return {
                "date": date,
                "sessions_count": 0,
                "articles_read": 0,
                "total_reading_time": 0.0,
                "words_read": 0,
                "average_wpm": 0.0,
            }

    def update_daily_stats(self) -> None:
        """Update daily statistics from session data."""
        if not self.current_session:
            return

        today = datetime.now().strftime("%Y-%m-%d")

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Calculate stats for today
                cursor.execute(
                    """
                    SELECT
                        COUNT(DISTINCT session_id) as sessions_count,
                        COUNT(*) as articles_read,
                        SUM(reading_time) as total_reading_time,
                        SUM(words_count) as words_read
                    FROM reading_history
                    WHERE date(started_at, 'unixepoch') = ?
                    AND completed_at IS NOT NULL
                """,
                    (today,),
                )

                row = cursor.fetchone()
                if row:
                    sessions_count, articles_read, total_time, words_read = row

                    # Calculate average WPM
                    avg_wpm = (words_read / (total_time / 60)) if total_time > 0 else 0

                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO reading_stats
                        (date, sessions_count, articles_read, total_reading_time,
                         words_read, average_wpm)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            today,
                            sessions_count,
                            articles_read,
                            total_time,
                            words_read,
                            avg_wpm,
                        ),
                    )

                    conn.commit()

        except sqlite3.Error as e:
            self.logger.error(f"Failed to update daily stats: {e}")

    def delete_session(self, session_id: str) -> bool:
        """Delete a reading session and its history."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Delete history first (foreign key constraint)
                cursor.execute(
                    "DELETE FROM reading_history WHERE session_id = ?", (session_id,)
                )

                # Delete session
                cursor.execute(
                    "DELETE FROM reading_sessions WHERE session_id = ?", (session_id,)
                )

                conn.commit()

                if (
                    self.current_session
                    and self.current_session.session_id == session_id
                ):
                    self.current_session = None

                self.logger.info(f"Deleted session {session_id}")
                return True

        except sqlite3.Error as e:
            self.logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def export_session_data(self, session_id: str) -> dict[str, Any] | None:
        """Export session data as JSON."""
        session = self.load_session(session_id)
        if not session:
            return None

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Get reading history for this session
                cursor.execute(
                    """
                    SELECT article_id, started_at, completed_at, reading_time,
                           words_count, skipped
                    FROM reading_history
                    WHERE session_id = ?
                    ORDER BY started_at
                """,
                    (session_id,),
                )

                history = []
                for row in cursor.fetchall():
                    history.append(
                        {
                            "article_id": row[0],
                            "started_at": row[1],
                            "completed_at": row[2],
                            "reading_time": row[3],
                            "words_count": row[4],
                            "skipped": bool(row[5]),
                        }
                    )

                return {
                    "session": {
                        "session_id": session.session_id,
                        "created_at": session.created_at,
                        "updated_at": session.updated_at,
                        "article_ids": session.article_ids,
                        "current_index": session.current_index,
                        "completed": session.completed,
                        "total_reading_time": session.total_reading_time,
                        "words_read": session.words_read,
                        "articles_completed": session.articles_completed,
                        "session_name": session.session_name,
                        "metadata": session.metadata,
                    },
                    "history": history,
                    "exported_at": time.time(),
                }

        except sqlite3.Error as e:
            self.logger.error(f"Failed to export session data: {e}")
            return None
