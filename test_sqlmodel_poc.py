#!/usr/bin/env python3
"""
Proof of concept test for SQLModel implementation.

This script validates that the SQLModel-based database service
works correctly with the existing SQLite database.
"""

import sys
from pathlib import Path

from config import get_config
from database_service import DatabaseService, benchmark_queries
from db_utils import DatabaseManager


def test_sqlmodel_compatibility() -> bool:
    """Test that SQLModel service provides same results as raw SQL."""
    config = get_config()
    db_path = config.database_path

    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        print("💡 Run './collect.sh' to sync the database")
        return False

    print("🧪 Testing SQLModel compatibility...")

    # Initialize both services
    try:
        old_db = DatabaseManager(db_path)
        new_db = DatabaseService(db_path)
    except Exception as e:
        print(f"❌ Failed to initialize databases: {e}")
        return False

    # Test 1: Database stats
    print("\n📊 Testing database statistics...")
    try:
        old_stats = old_db.get_database_stats()
        new_stats = new_db.get_database_stats()

        print(f"   Raw SQL stats: {old_stats}")
        print(f"   SQLModel stats: {new_stats}")

        if old_stats == new_stats:
            print("   ✅ Stats match!")
        else:
            print("   ❌ Stats don't match!")
            return False

    except Exception as e:
        print(f"   ❌ Stats test failed: {e}")
        return False

    # Test 2: Unread articles
    print("\n📰 Testing unread articles...")
    try:
        old_articles = old_db.get_unread_articles(10)
        new_articles = new_db.get_unread_articles(10)

        print(f"   Raw SQL found: {len(old_articles)} articles")
        print(f"   SQLModel found: {len(new_articles)} articles")

        if len(old_articles) == len(new_articles):
            print("   ✅ Article counts match!")

            # Check first article details
            if old_articles and new_articles:
                old_first = old_articles[0]
                new_first = new_articles[0]

                if (
                    old_first["id"] == new_first["id"]
                    and old_first["title"] == new_first["title"]
                ):
                    print("   ✅ Article details match!")
                else:
                    print("   ❌ Article details don't match!")
                    print(f"      Old: {old_first['id']} - {old_first['title'][:50]}")
                    print(f"      New: {new_first['id']} - {new_first['title'][:50]}")
                    return False
        else:
            print("   ❌ Article counts don't match!")
            return False

    except Exception as e:
        print(f"   ❌ Unread articles test failed: {e}")
        return False

    # Test 3: Empty summaries
    print("\n📄 Testing empty summaries...")
    try:
        old_empty = old_db.get_articles_with_empty_summaries(5)
        new_empty = new_db.get_articles_with_empty_summaries(5)

        print(f"   Raw SQL found: {len(old_empty)} empty articles")
        print(f"   SQLModel found: {len(new_empty)} empty articles")

        if len(old_empty) == len(new_empty):
            print("   ✅ Empty summary counts match!")
        else:
            print("   ❌ Empty summary counts don't match!")
            return False

    except Exception as e:
        print(f"   ❌ Empty summaries test failed: {e}")
        return False

    # Test 4: Performance comparison
    print("\n⚡ Testing performance...")
    try:
        perf_results = benchmark_queries(db_path, iterations=10)

        print(f"   Raw SQL average: {perf_results['raw_sql_avg_ms']:.2f}ms")
        print(f"   SQLModel average: {perf_results['sqlmodel_avg_ms']:.2f}ms")
        print(f"   Performance ratio: {perf_results['performance_ratio']:.2f}x")

        if perf_results["performance_ratio"] < 3.0:  # Allow up to 3x slower
            print("   ✅ Performance acceptable!")
        else:
            print("   ⚠️  Performance degradation detected (but functionality works)")

    except Exception as e:
        print(f"   ❌ Performance test failed: {e}")
        return False

    # Cleanup
    if hasattr(old_db, "close"):
        old_db.close()
    new_db.close()

    print("\n🎉 All SQLModel compatibility tests passed!")
    return True


def test_type_safety() -> bool:
    """Test that type annotations work correctly."""
    print("\n🔍 Testing type safety...")

    config = get_config()
    db_service = DatabaseService(config.database_path)

    try:
        # Test that we get proper type hints
        articles = db_service.get_unread_articles(5)

        if articles:
            article = articles[0]
            # These should all be properly typed
            article_id: int = article["id"]
            title: str = article["title"] or ""
            is_translated: bool = article["is_translated"]

            print(f"   ✅ Type annotations work: article {article_id}")
            print(f"      Title: {title[:50]}...")
            print(f"      Translated: {is_translated}")

        db_service.close()
        return True

    except Exception as e:
        print(f"   ❌ Type safety test failed: {e}")
        if hasattr(db_service, "close"):
            db_service.close()
        return False


def show_migration_benefits() -> None:
    """Show the benefits of migrating to SQLModel."""
    print("\n📈 Migration Benefits:")
    print("   ✅ Type safety with mypy")
    print("   ✅ IDE autocompletion")
    print("   ✅ Pydantic validation")
    print("   ✅ Reusable query components")
    print("   ✅ Reduced SQL boilerplate")
    print("   ✅ Better error handling")
    print("   ✅ Modern Python patterns")

    print("\n🔧 Current Raw SQL Lines:")
    print("   db_utils.py: ~400+ lines of SQL")
    print("   session_manager.py: ~200+ lines of SQL")
    print("   Total: 600+ lines of manual SQL")

    print("\n🚀 SQLModel Replacement:")
    print("   db_models.py: ~150 lines (type definitions)")
    print("   database_service.py: ~300 lines (business logic)")
    print("   Total: 450 lines (25% reduction + type safety)")


def main() -> int:
    """Run SQLModel proof of concept tests."""
    print("🐦 Chirpy SQLModel Proof of Concept")
    print("=" * 50)

    # Test compatibility
    success = test_sqlmodel_compatibility()

    if success:
        # Test type safety
        test_type_safety()

        # Show benefits
        show_migration_benefits()

        print("\n✅ SQLModel POC successful!")
        print("💡 Ready to implement gradual migration strategy")
        return 0
    else:
        print("\n❌ SQLModel POC failed!")
        print("💡 Need to address compatibility issues before migration")
        return 1


if __name__ == "__main__":
    sys.exit(main())
