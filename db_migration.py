#!/usr/bin/env python3
"""
Database migration script for Chirpy RSS reader.

Creates read_articles table to track which articles have been read.
"""

import sqlite3
import sys
from pathlib import Path


def create_read_articles_table(db_path: str) -> None:
    """Create the read_articles table if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
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

        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_read_articles_article_id
            ON read_articles (article_id)
        """)

        conn.commit()
        print("✅ read_articles table created successfully")

        # Show table info
        cursor.execute("PRAGMA table_info(read_articles)")
        columns = cursor.fetchall()
        print("\nTable schema:")
        for col in columns:
            print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else ''}")

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    finally:
        conn.close()


def check_existing_data(db_path: str) -> None:
    """Check existing articles data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Count total articles
        cursor.execute("SELECT COUNT(*) FROM articles")
        total_articles = cursor.fetchone()[0]

        # Count read articles
        cursor.execute("SELECT COUNT(*) FROM read_articles")
        read_articles = cursor.fetchone()[0]

        print("\n📊 Database status:")
        print(f"  Total articles: {total_articles}")
        print(f"  Read articles: {read_articles}")
        print(f"  Unread articles: {total_articles - read_articles}")

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()


def main() -> None:
    """Main migration function."""
    db_path = Path(__file__).parent / "data" / "articles.db"

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)

    print(f"🔄 Running migration on: {db_path}")

    create_read_articles_table(str(db_path))
    check_existing_data(str(db_path))

    print("\n✅ Migration completed successfully!")


if __name__ == "__main__":
    main()
