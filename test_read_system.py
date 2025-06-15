#!/usr/bin/env python3
"""
Test script for read tracking system.

Tests the database utilities and read tracking functionality.
"""

import sys
from pathlib import Path
from typing import Any, Optional

from db_utils import DatabaseManager


def test_read_system() -> None:
    """Test the read tracking system."""
    db_path = Path(__file__).parent / "data" / "articles.db"

    print("🧪 Testing read tracking system...")
    print(f"Database: {db_path}")

    try:
        # Initialize database manager
        db = DatabaseManager(str(db_path))

        # Test 1: Get database stats
        print("\n📊 Database Statistics:")
        stats = db.get_database_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")

        # Test 2: Get unread articles
        print("\n📰 Getting unread articles (limit 5):")
        unread_articles = db.get_unread_articles(limit=5)

        if not unread_articles:
            print("  No unread articles found")
            return

        for i, article in enumerate(unread_articles, 1):
            print(f"  {i}. ID:{article['id']} - {article['title'][:50]}...")
            print(f"     Published: {article['published']}")
            print(f"     Has summary: {'Yes' if article['summary'] else 'No'}")

        # Test 3: Mark first article as read
        if unread_articles:
            first_article = unread_articles[0]
            article_id = first_article["id"]

            print(f"\n✅ Testing: Mark article {article_id} as read")

            # Check if already read
            is_read_before = db.is_article_read(article_id)
            print(f"  Read status before: {is_read_before}")

            # Mark as read
            success = db.mark_article_as_read(article_id)
            print(f"  Mark as read result: {success}")

            # Check if now read
            is_read_after = db.is_article_read(article_id)
            print(f"  Read status after: {is_read_after}")

            # Try to mark as read again (should be ignored)
            success_again = db.mark_article_as_read(article_id)
            print(f"  Mark as read again result: {success_again}")

        # Test 4: Updated stats
        print("\n📊 Updated Database Statistics:")
        updated_stats = db.get_database_stats()
        for key, value in updated_stats.items():
            print(f"  {key}: {value}")

        # Test 5: Get specific article
        if unread_articles:
            article_id = unread_articles[0]["id"]
            print(f"\n🔍 Testing: Get article by ID {article_id}")
            found_article: Optional[dict[str, Any]] = db.get_article_by_id(article_id)
            if found_article is not None:
                print(f"  Found: {found_article['title'][:50]}...")
            else:
                print("  Article not found")

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_read_system()
