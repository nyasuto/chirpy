#!/usr/bin/env python3
"""
Chirpy RSS Reader - Main Application

MVP RSS reader with text-to-speech functionality.
Reads articles from SQLite database and provides audio narration.
"""

import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    import pyttsx3  # type: ignore
except ImportError:
    pyttsx3 = None

from cli import apply_args_to_config, handle_special_modes, parse_args
from config import ChirpyConfig, get_logger, initialize_app_logging
from content_fetcher import ContentFetcher
from db_utils import DatabaseManager
from error_handling import (
    ErrorHandler,
    get_user_friendly_message,
    is_recoverable_error,
    timeout_context,
)


class ChirpyReader:
    """Main application class for Chirpy RSS reader."""

    def __init__(self, config: ChirpyConfig):
        """Initialize Chirpy reader."""
        self.config = config
        self.logger = get_logger(__name__)
        self.db_path = Path(config.database_path)

        # Initialize error handler
        self.error_handler = ErrorHandler("chirpy_reader")

        if not self.db_path.exists():
            self.logger.error(f"Database not found at {config.database_path}")
            self.logger.info("Tip: Run './collect.sh' to sync the database")
            sys.exit(1)

        self.db = DatabaseManager(str(self.db_path))
        self.tts_engine = self._initialize_tts()
        self.content_fetcher = ContentFetcher(config)

    def _initialize_tts(self) -> pyttsx3.Engine | None:
        """Initialize text-to-speech engine."""
        if not self.config.speech_enabled:
            self.logger.info("Text-to-speech disabled by configuration")
            return None

        if pyttsx3 is None:
            self.logger.warning(
                "pyttsx3 not available, using macOS 'say' command fallback"
            )
            return None

        try:
            engine = pyttsx3.init()

            # Configure TTS settings from config
            voices = engine.getProperty("voices")
            if voices:
                # Use first available voice
                engine.setProperty("voice", voices[0].id)

            # Set speech rate from config
            engine.setProperty("rate", self.config.tts_rate)
            engine.setProperty("volume", self.config.tts_volume)

            self.logger.info(
                f"TTS initialized with rate={self.config.tts_rate}, "
                f"volume={self.config.tts_volume}"
            )
            return engine

        except Exception as e:
            self.logger.warning(f"Failed to initialize pyttsx3: {e}")
            self.logger.info("Using macOS 'say' command fallback")
            return None

    def speak_text(self, text: str) -> None:
        """Speak text using available TTS method with comprehensive error handling."""
        if not text.strip():
            return

        if not self.config.speech_enabled:
            self.logger.debug("Speech disabled, skipping TTS")
            return

        # Validate and clean text for TTS
        text = self._prepare_text_for_tts(text)
        if not text:
            return

        self.logger.info(f"Speaking: {text[:100]}{'...' if len(text) > 100 else ''}")

        # Try pyttsx3 engine first
        if self.tts_engine is not None:
            if self._try_pyttsx3_with_timeout(text):
                return

        # Fallback to system TTS command
        self._try_system_tts_with_retry(text)

    def _prepare_text_for_tts(self, text: str) -> str:
        """Prepare and validate text for TTS."""
        # Remove excessive whitespace
        text = " ".join(text.split())

        # Truncate very long text to prevent TTS issues
        if len(text) > 10000:
            text = text[:10000] + " ... テキストが長すぎるため省略されました。"
            self.logger.warning("Text truncated for TTS due to length")

        # Remove problematic characters that might cause TTS issues
        problematic_chars = ["<", ">", "{", "}", "[", "]", "|", "\\"]
        for char in problematic_chars:
            text = text.replace(char, " ")

        return text.strip()

    def _try_pyttsx3_with_timeout(self, text: str, max_retries: int = 2) -> bool:
        """Try pyttsx3 TTS with timeout and retry logic."""
        for attempt in range(max_retries):
            try:
                with timeout_context(self.config.tts_timeout, "pyttsx3 TTS"):
                    if self.tts_engine is not None:
                        self.tts_engine.say(text)
                        self.tts_engine.runAndWait()
                    self.logger.debug("pyttsx3 TTS completed successfully")
                    return True

            except TimeoutError as e:
                self.error_handler.handle_error(
                    "tts_pyttsx3_timeout",
                    e,
                    retry_count=attempt,
                    context={
                        "text_length": len(text),
                        "timeout": self.config.tts_timeout,
                    },
                )
                if attempt < max_retries - 1:
                    time.sleep(1)  # Brief pause before retry

            except Exception as e:
                self.error_handler.handle_error(
                    "tts_pyttsx3_error",
                    e,
                    retry_count=attempt,
                    recoverable=is_recoverable_error(e),
                    context={"text_length": len(text)},
                )
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    self.logger.warning(
                        f"pyttsx3 failed after {max_retries} attempts, using fallback"
                    )

        return False

    def _try_system_tts_with_retry(self, text: str, max_retries: int = 3) -> None:
        """Try system TTS command with retry logic."""
        for attempt in range(max_retries):
            try:
                with timeout_context(self.config.tts_timeout, "system TTS"):
                    subprocess.run(
                        ["say", text],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=self.config.tts_timeout,
                    )
                    self.logger.debug("System TTS completed successfully")
                    return

            except subprocess.TimeoutExpired as e:
                self.error_handler.handle_error(
                    "tts_system_timeout",
                    e,
                    retry_count=attempt,
                    context={
                        "text_length": len(text),
                        "timeout": self.config.tts_timeout,
                    },
                )

            except subprocess.CalledProcessError as e:
                self.error_handler.handle_error(
                    "tts_system_error",
                    e,
                    retry_count=attempt,
                    context={"text_length": len(text), "stderr": e.stderr},
                )

            except FileNotFoundError as e:
                self.error_handler.handle_error(
                    "tts_system_not_found",
                    e,
                    recoverable=False,
                    context={"command": "say"},
                )
                self.logger.error(
                    "System TTS command 'say' not found. Text-to-speech unavailable."
                )
                return

            except Exception as e:
                self.error_handler.handle_error(
                    "tts_system_unexpected",
                    e,
                    retry_count=attempt,
                    recoverable=is_recoverable_error(e),
                    context={"text_length": len(text)},
                )

            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                wait_time = min(2**attempt, 5)  # Cap at 5 seconds
                self.logger.debug(f"Retrying TTS in {wait_time} seconds...")
                time.sleep(wait_time)

        # All TTS methods failed
        friendly_message = get_user_friendly_message(
            Exception("TTS system unavailable"), "text-to-speech"
        )
        self.logger.error(f"All TTS methods failed: {friendly_message}")
        self.logger.info("Continuing without audio output...")

    def process_article_for_reading(self, article: dict[str, Any]) -> dict[str, Any]:
        """
        Process article with on-demand language detection and translation.

        Args:
            article: Article dictionary from database

        Returns:
            Updated article dictionary with translated content if needed
        """
        article_id = article.get("id")
        if not isinstance(article_id, int):
            return article
        detected_language = article.get("detected_language", "unknown")
        summary = article.get("summary", "")

        # If language is unknown and we have content, detect and translate
        if (
            detected_language == "unknown"
            and summary
            and summary.strip()
            and summary != "No summary available"
            and self.content_fetcher.is_available()
            and self.config.auto_translate
        ):
            try:
                title_preview = article.get("title", "")[:50]
                self.logger.info(
                    f"Detecting language for article {article_id}: {title_preview}..."
                )

                # Process with translation workflow
                result = self.content_fetcher.process_article_with_translation(article)
                translated_summary, detected_lang, is_translated = result

                if translated_summary and is_translated:
                    # Update database with translation
                    original_summary = article.get("summary", "")
                    self.db.update_article_summary(article_id, translated_summary)
                    self.db.update_article_language_info(
                        article_id, detected_lang, original_summary, True
                    )
                    # Update article dict for immediate use
                    article["summary"] = translated_summary
                    article["detected_language"] = detected_lang
                    article["is_translated"] = True
                    article["original_summary"] = original_summary

                    self.logger.info(
                        f"✅ Article {article_id} translated from {detected_lang} to ja"
                    )

                elif detected_lang != "unknown":
                    # Update language info even if no translation needed
                    self.db.update_article_language_info(
                        article_id, detected_lang, None, False
                    )
                    article["detected_language"] = detected_lang
                    article["is_translated"] = False

                    self.logger.info(
                        f"ℹ️  Article {article_id} detected as {detected_lang}"
                    )

            except Exception as e:
                self.logger.warning(
                    f"Failed to process article {article_id} for translation: {e}"
                )

        return article

    def format_article_content(self, article: dict[str, Any]) -> str:
        """Format article content for speech."""
        title = article.get("title", "No title")
        summary = article.get("summary", "No summary available")
        detected_language = article.get("detected_language", "unknown")
        is_translated = article.get("is_translated", False)

        # Add language info to title if translated
        if is_translated and detected_language == "en":
            title = f"{title} (英語記事 → 日本語翻訳済み)"

        # Clean up the summary text for better speech
        summary = summary.replace("\n", " ").replace("\r", " ")
        summary = " ".join(summary.split())  # Normalize whitespace

        # Limit summary length based on config
        if len(summary) > self.config.max_summary_length:
            summary = summary[: self.config.max_summary_length] + "..."

        return f"Article title: {title}. Content: {summary}"

    def process_empty_summaries(self, max_articles: int = 5) -> int:
        """
        Process articles with empty summaries by fetching and generating summaries.

        Args:
            max_articles: Maximum number of articles to process

        Returns:
            Number of articles successfully processed
        """
        if not self.content_fetcher.is_available():
            self.logger.warning(
                "Content fetching not available (OpenAI API key required)"
            )
            return 0

        self.logger.info("Processing articles with empty summaries...")

        # Get articles with empty summaries
        empty_articles = self.db.get_articles_with_empty_summaries(limit=max_articles)

        if not empty_articles:
            self.logger.info("No articles with empty summaries found")
            return 0

        self.logger.info(f"Found {len(empty_articles)} articles with empty summaries")

        processed_count = 0
        for i, article in enumerate(empty_articles, 1):
            self.logger.info(
                f"Processing article {i}/{len(empty_articles)}: "
                f"{article.get('title', 'No title')}"
            )

            try:
                # Process the article (fetch + summarize)
                summary = self.content_fetcher.process_empty_summary_article(article)

                if summary:
                    # Update database with new summary
                    if self.db.update_article_summary(article["id"], summary):
                        self.logger.info(
                            f"Updated article {article['id']} with AI summary"
                        )
                        processed_count += 1
                    else:
                        self.logger.error(
                            f"Failed to update database for article {article['id']}"
                        )
                else:
                    self.logger.error(
                        f"Failed to generate summary for article {article['id']}"
                    )

            except Exception as e:
                self.logger.error(f"Error processing article {article['id']}: {e}")
                continue

            # Rate limiting: pause between requests
            if i < len(empty_articles):
                self.logger.debug(
                    f"Pausing {self.config.rate_limit_delay}s to respect "
                    "API rate limits"
                )
                time.sleep(self.config.rate_limit_delay)

        self.logger.info(
            f"Processing complete! {processed_count}/{len(empty_articles)} "
            "articles updated"
        )
        return processed_count

    def read_articles(self) -> None:
        """Read the latest unread articles with text-to-speech."""
        self.logger.info("Chirpy RSS Reader Starting...")

        try:
            # Get database statistics
            stats = self.db.get_database_stats()
            self.logger.info("Database Stats:")
            self.logger.info(f"   Total articles: {stats['total_articles']}")
            self.logger.info(f"   Read articles: {stats['read_articles']}")
            self.logger.info(f"   Unread articles: {stats['unread_articles']}")
            self.logger.info(f"   Empty summaries: {stats['empty_summaries']}")

            if stats["unread_articles"] == 0:
                self.logger.info("No unread articles found!")
                self.speak_text("No unread articles found. All caught up!")
                return

            # Get the latest unread articles
            self.logger.info(
                f"Fetching {self.config.max_articles} latest unread articles..."
            )
            articles = self.db.get_unread_articles(limit=self.config.max_articles)

            if not articles:
                self.logger.warning("No unread articles with content found")
                return

            self.logger.info(f"Found {len(articles)} unread articles to read")

            # Introduction
            intro_text = (
                f"Welcome to Chirpy! I found {len(articles)} unread articles "
                "to read for you."
            )
            self.speak_text(intro_text)

            # Read each article
            for i, article in enumerate(articles, 1):
                self.logger.info(f"Article {i} of {len(articles)}: {article['title']}")
                self.logger.debug(f"Link: {article['link']}")
                self.logger.debug(f"Published: {article['published']}")

                # Process article for language detection and translation if needed
                processed_article = self.process_article_for_reading(article)

                # Format and speak the article
                content = self.format_article_content(processed_article)
                self.speak_text(content)

                # Mark as read if configured
                if self.config.auto_mark_read:
                    if self.db.mark_article_as_read(article["id"]):
                        self.logger.debug(f"Marked article {article['id']} as read")
                    else:
                        self.logger.warning(
                            f"Failed to mark article {article['id']} as read"
                        )

                # Pause between articles (except for the last one)
                if i < len(articles) and self.config.pause_between_articles:
                    self.logger.debug("Pausing between articles...")
                    time.sleep(2)

            # Conclusion
            conclusion_text = (
                f"That's all for now! I've read {len(articles)} articles for you."
            )
            self.logger.info("Session complete!")
            self.speak_text(conclusion_text)

        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            self.speak_text("Sorry, an error occurred while reading articles.")
            sys.exit(1)

    def run(self) -> None:
        """Run the main application."""
        try:
            self.read_articles()
        except KeyboardInterrupt:
            self.logger.info("Chirpy interrupted by user. Goodbye!")
            self.speak_text("Goodbye!")
            sys.exit(0)
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            sys.exit(1)


def main() -> None:
    """Main entry point."""
    try:
        # Initialize configuration and logging
        config, logger = initialize_app_logging()

        # Parse command line arguments
        args = parse_args()

        # Apply CLI arguments to configuration
        config = apply_args_to_config(args, config)

        # Handle special modes that don't require main application flow
        if handle_special_modes(args, config):
            return

        # Create and run the reader
        reader = ChirpyReader(config)

        if args.process_summaries:
            reader.process_empty_summaries(config.max_articles)
        else:
            reader.run()

    except Exception as e:
        logging.error(f"Fatal error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
