#!/usr/bin/env python3
"""
Chirpy RSS Reader - Main Application

MVP RSS reader with text-to-speech functionality.
Reads articles from SQLite database and provides audio narration.
"""

import sys
from pathlib import Path
from typing import Any

try:
    import pyttsx3  # type: ignore
except ImportError:
    pyttsx3 = None

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
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "data/articles.db"

    reader = ChirpyReader(db_path)
    reader.run()


if __name__ == "__main__":
    main()
