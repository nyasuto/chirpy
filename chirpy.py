#!/usr/bin/env python3
"""
Chirpy RSS Reader - Main Application

MVP RSS reader with text-to-speech functionality.
Reads articles from SQLite database and provides audio narration.
"""

import sys
import time
from pathlib import Path
from typing import Any

try:
    import pyttsx3  # type: ignore
except ImportError:
    pyttsx3 = None

from content_fetcher import ContentFetcher
from db_utils import DatabaseManager


class ChirpyReader:
    """Main application class for Chirpy RSS reader."""

    def __init__(self, db_path: str = "data/articles.db"):
        """Initialize Chirpy reader."""
        self.db_path = Path(db_path)

        if not self.db_path.exists():
            print(f"❌ Error: Database not found at {db_path}")
            print("💡 Tip: Run './collect.sh' to sync the database")
            sys.exit(1)

        self.db = DatabaseManager(str(self.db_path))
        self.tts_engine = self._initialize_tts()
        self.content_fetcher = ContentFetcher()

    def _initialize_tts(self) -> pyttsx3.Engine | None:
        """Initialize text-to-speech engine."""
        if pyttsx3 is None:
            print(
                "⚠️  Warning: pyttsx3 not available, using macOS 'say' command fallback"
            )
            return None

        try:
            engine = pyttsx3.init()

            # Configure TTS settings
            voices = engine.getProperty("voices")
            if voices:
                # Use first available voice
                engine.setProperty("voice", voices[0].id)

            # Set speech rate (words per minute)
            engine.setProperty("rate", 180)  # Slightly slower for better comprehension

            return engine

        except Exception as e:
            print(f"⚠️  Warning: Failed to initialize pyttsx3: {e}")
            print("Using macOS 'say' command fallback")
            return None

    def speak_text(self, text: str) -> None:
        """Speak the given text using available TTS method."""
        if not text.strip():
            return

        print(f"🔊 Speaking: {text[:100]}{'...' if len(text) > 100 else ''}")

        if self.tts_engine:
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                return
            except Exception as e:
                print(f"⚠️  TTS engine error: {e}, falling back to 'say' command")

        # Fallback to macOS 'say' command
        import subprocess

        try:
            subprocess.run(["say", text], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"⚠️  Text-to-speech not available: {e}")

    def format_article_content(self, article: dict[str, Any]) -> str:
        """Format article content for speech."""
        title = article.get("title", "No title")
        summary = article.get("summary", "No summary available")

        # Clean up the summary text for better speech
        summary = summary.replace("\n", " ").replace("\r", " ")
        summary = " ".join(summary.split())  # Normalize whitespace

        # Limit summary length for reasonable speech duration
        if len(summary) > 500:
            summary = summary[:500] + "..."

        return f"Article title: {title}. Content: {summary}"

    def process_empty_summaries(self, max_articles: int = 5) -> int:
        """
        Process articles with empty summaries by fetching content and generating AI summaries.

        Args:
            max_articles: Maximum number of articles to process

        Returns:
            Number of articles successfully processed
        """
        if not self.content_fetcher.is_available():
            print("⚠️  Content fetching not available (OpenAI API key required)")
            return 0

        print("\n📄 Processing articles with empty summaries...")

        # Get articles with empty summaries
        empty_articles = self.db.get_articles_with_empty_summaries(limit=max_articles)

        if not empty_articles:
            print("✅ No articles with empty summaries found")
            return 0

        print(f"📋 Found {len(empty_articles)} articles with empty summaries")

        processed_count = 0
        for i, article in enumerate(empty_articles, 1):
            print(f"\n--- Processing article {i}/{len(empty_articles)} ---")

            try:
                # Process the article (fetch + summarize)
                summary = self.content_fetcher.process_empty_summary_article(article)

                if summary:
                    # Update database with new summary
                    if self.db.update_article_summary(article["id"], summary):
                        print(f"✅ Updated article {article['id']} with AI summary")
                        processed_count += 1
                    else:
                        print(
                            f"❌ Failed to update database for article {article['id']}"
                        )
                else:
                    print(f"❌ Failed to generate summary for article {article['id']}")

            except Exception as e:
                print(f"❌ Error processing article {article['id']}: {e}")
                continue

            # Rate limiting: pause between requests
            if i < len(empty_articles):
                print("⏸️  Pausing to respect API rate limits...")
                time.sleep(2)

        print(
            f"\n🎉 Processing complete! {processed_count}/{len(empty_articles)} articles updated"
        )
        return processed_count

    def read_articles(self) -> None:
        """Read the latest 3 unread articles with text-to-speech."""
        print("🐦 Chirpy RSS Reader Starting...")

        try:
            # Get database statistics
            stats = self.db.get_database_stats()
            print("📊 Database Stats:")
            print(f"   Total articles: {stats['total_articles']}")
            print(f"   Read articles: {stats['read_articles']}")
            print(f"   Unread articles: {stats['unread_articles']}")
            print(f"   Empty summaries: {stats['empty_summaries']}")

            if stats["unread_articles"] == 0:
                print("✅ No unread articles found!")
                self.speak_text("No unread articles found. All caught up!")
                return

            # Get the 3 latest unread articles
            print("\n📖 Fetching 3 latest unread articles...")
            articles = self.db.get_unread_articles(limit=3)

            if not articles:
                print("❌ No unread articles with content found")
                return

            print(f"📚 Found {len(articles)} unread articles to read")

            # Introduction
            intro_text = (
                f"Welcome to Chirpy! I found {len(articles)} unread articles "
                "to read for you."
            )
            self.speak_text(intro_text)

            # Read each article
            for i, article in enumerate(articles, 1):
                print(f"\n--- Article {i} of {len(articles)} ---")
                print(f"📰 Title: {article['title']}")
                print(f"🔗 Link: {article['link']}")
                print(f"📅 Published: {article['published']}")

                # Format and speak the article
                content = self.format_article_content(article)
                self.speak_text(content)

                # Mark as read
                if self.db.mark_article_as_read(article["id"]):
                    print(f"✅ Marked article {article['id']} as read")
                else:
                    print(f"⚠️  Failed to mark article {article['id']} as read")

                # Pause between articles (except for the last one)
                if i < len(articles):
                    print("⏸️  Pausing between articles...")
                    import time

                    time.sleep(2)

            # Conclusion
            conclusion_text = (
                f"That's all for now! I've read {len(articles)} articles for you."
            )
            print("\n🎉 Session complete!")
            self.speak_text(conclusion_text)

        except Exception as e:
            error_msg = f"An error occurred: {e}"
            print(f"❌ {error_msg}")
            self.speak_text("Sorry, an error occurred while reading articles.")
            sys.exit(1)

    def run(self) -> None:
        """Run the main application."""
        try:
            self.read_articles()
        except KeyboardInterrupt:
            print("\n👋 Chirpy interrupted by user. Goodbye!")
            self.speak_text("Goodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            sys.exit(1)


def main() -> None:
    """Main entry point."""
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--process-summaries":
            # Special mode: process empty summaries
            db_path = sys.argv[2] if len(sys.argv) > 2 else "data/articles.db"
            reader = ChirpyReader(db_path)
            reader.process_empty_summaries()
            return
        else:
            db_path = sys.argv[1]
    else:
        db_path = "data/articles.db"

    reader = ChirpyReader(db_path)
    reader.run()


if __name__ == "__main__":
    main()
