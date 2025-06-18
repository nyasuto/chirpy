#!/usr/bin/env python3
"""
Chirpy RSS Reader - Main Application

MVP RSS reader with text-to-speech functionality.
Reads articles from SQLite database and provides audio narration.
"""

import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any

try:
    import pyttsx3  # type: ignore

    PYTTSX3_AVAILABLE = True
except ImportError:
    pyttsx3 = None
    PYTTSX3_AVAILABLE = False


from cli import apply_args_to_config, handle_special_modes, parse_args
from config import ChirpyConfig, get_logger, initialize_app_logging
from content_fetcher import ContentFetcher
from database_service import DatabaseManager
from tts_service import EnhancedTTSService, TTSQuality

try:
    from interactive_ui import ArticleSelector, InteractiveController, ProgressTracker
except Exception as e:
    # Fallback to safe version if interactive_ui has issues
    print(f"Warning: Using safe interactive UI due to: {e}")
    from interactive_ui_safe import (
        ArticleSelector,
        InteractiveController,
        ProgressTracker,
    )


class ChirpyReader:
    """Main application class for Chirpy RSS reader."""

    def __init__(self, config: ChirpyConfig):
        """Initialize Chirpy reader."""
        self.config = config
        self.logger = get_logger(__name__)
        self.db_path = Path(config.database_path)

        if not self.db_path.exists():
            self.logger.error(f"Database not found at {config.database_path}")
            self.logger.info("Tip: Run './collect.sh' to sync the database")
            sys.exit(1)

        self.db = DatabaseManager(str(self.db_path))
        self.tts_service = EnhancedTTSService(config)
        self.content_fetcher = ContentFetcher(config)

        # Interactive UI components
        self.interactive_controller = (
            InteractiveController(config) if config.interactive_mode else None
        )
        self.article_selector = ArticleSelector(config)
        self.progress_tracker = ProgressTracker(config)

        # Playback control state
        self.is_paused = False
        self.should_skip = False
        self.should_stop = False
        self.current_speed_multiplier = 1.0
        self.playback_lock = threading.Lock()

    def _log_tts_info(self) -> None:
        """Log TTS service information."""
        available_qualities = self.tts_service.get_available_qualities()
        self.logger.info(
            f"TTS service initialized with {len(available_qualities)} quality levels"
        )
        self.logger.info(f"Available: {[q.value for q in available_qualities]}")

        if (
            TTSQuality.HD in available_qualities
            or TTSQuality.STANDARD in available_qualities
        ):
            self.logger.info("✨ High-quality OpenAI TTS available!")
        else:
            self.logger.info(
                "Using system TTS (consider adding OPENAI_API_KEY for better quality)"
            )

    def speak_text(self, text: str) -> None:
        """Speak text using enhanced TTS service with interactive controls."""
        if not text.strip():
            return

        if not self.config.speech_enabled:
            self.logger.debug("Speech disabled, skipping TTS")
            return

        # Check for stop signal
        with self.playback_lock:
            if self.should_stop:
                return

        self.logger.info(f"Speaking: {text[:100]}{'...' if len(text) > 100 else ''}")

        # For OpenAI TTS, speak the entire text at once for better quality
        # For system TTS, split into sentences for pause/resume support
        if self.tts_service.current_quality in [TTSQuality.STANDARD, TTSQuality.HD]:
            # High-quality TTS - speak entire text
            with self.playback_lock:
                if self.should_stop or self.should_skip:
                    return

                # Wait while paused
                while self.is_paused and not self.should_stop:
                    time.sleep(0.1)

                if self.should_stop:
                    return

            try:
                success = self.tts_service.speak_text(
                    text, self.config.openai_tts_voice
                )
                if not success:
                    self.logger.warning("High-quality TTS failed, using fallback")
            except Exception as e:
                self.logger.error(f"TTS service error: {e}")
        else:
            # System TTS - split into sentences for interactive control
            sentences = self._split_text_for_playback(text)

            for sentence in sentences:
                with self.playback_lock:
                    if self.should_stop:
                        return
                    if self.should_skip:
                        self.should_skip = False  # Reset skip flag
                        return

                    # Wait while paused
                    while self.is_paused and not self.should_stop:
                        time.sleep(0.1)

                    if self.should_stop:
                        return

                try:
                    success = self.tts_service.speak_text(sentence)
                    if not success:
                        self.logger.error("TTS failed for sentence")
                        break
                except Exception as e:
                    self.logger.error(f"TTS error: {e}")
                    break

    def _split_text_for_playback(self, text: str) -> list[str]:
        """Split text into manageable chunks for interactive playback."""
        # Split by sentences, but keep reasonable chunk sizes
        import re

        sentences = re.split(r"[.!?]+", text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # If adding this sentence would make chunk too long, start new chunk
            if len(current_chunk) + len(sentence) > 200 and current_chunk:
                chunks.append(current_chunk)
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [text]

    def _setup_interactive_controls(self) -> None:
        """Set up interactive control callbacks."""
        if self.interactive_controller:
            self.interactive_controller.set_callbacks(
                pause=self._pause_playback,
                resume=self._resume_playback,
                skip=self._skip_current,
                speed=self._adjust_speed,
                volume=self._adjust_volume,
                stop=self._stop_playback,
            )

    def _pause_playback(self) -> None:
        """Pause current playback."""
        with self.playback_lock:
            self.is_paused = True

    def _resume_playback(self) -> None:
        """Resume paused playback."""
        with self.playback_lock:
            self.is_paused = False

    def _skip_current(self) -> None:
        """Skip current article."""
        with self.playback_lock:
            self.should_skip = True
            self.is_paused = False  # Resume if paused

    def _adjust_speed(self, multiplier: float) -> None:
        """Adjust playback speed."""
        with self.playback_lock:
            self.current_speed_multiplier = multiplier

    def _adjust_volume(self, volume: float) -> None:
        """Adjust playback volume."""
        self.config.tts_volume = volume
        # Volume adjustment for TTS service will be handled in the next audio clip

    def _stop_playback(self) -> None:
        """Stop playback completely."""
        with self.playback_lock:
            self.should_stop = True
            self.is_paused = False

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
            # Log TTS service information
            self._log_tts_info()

            # Setup interactive controls if enabled
            if self.interactive_controller:
                self._setup_interactive_controls()

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

            # Get all unread articles for selection
            # Get more articles for selection
            all_articles = self.db.get_unread_articles(limit=50)

            if not all_articles:
                self.logger.warning("No unread articles with content found")
                return

            # Article selection
            if self.config.select_articles:
                articles = self.article_selector.show_article_menu(all_articles)
            else:
                articles = all_articles[: self.config.max_articles]

            if not articles:
                self.logger.info("No articles selected for reading")
                return

            self.logger.info(f"Found {len(articles)} articles to read")

            # Start interactive session if enabled
            if self.interactive_controller:
                self.interactive_controller.start_session(len(articles))

            # Start progress tracking
            self.progress_tracker.session_start = time.time()

            # Introduction
            intro_text = (
                f"Welcome to Chirpy! I found {len(articles)} articles to read for you."
            )
            if self.interactive_controller:
                intro_text += " Press H for keyboard shortcuts."

            self.speak_text(intro_text)

            # Read each article
            for i, article in enumerate(articles):
                # Check for stop signal
                with self.playback_lock:
                    if self.should_stop:
                        break

                self.logger.info(
                    f"Article {i + 1} of {len(articles)}: {article['title']}"
                )
                self.logger.debug(f"Link: {article['link']}")
                self.logger.debug(f"Published: {article['published']}")

                # Update progress tracking and UI
                if self.interactive_controller:
                    self.interactive_controller.update_progress(i, article["title"])

                self.progress_tracker.update_statistics(article=article)

                # Process article for language detection and translation if needed
                processed_article = self.process_article_for_reading(article)

                # Format and speak the article
                content = self.format_article_content(processed_article)
                self.speak_text(content)

                # Check if we should skip to next article
                with self.playback_lock:
                    if self.should_skip:
                        self.should_skip = False
                        continue
                    if self.should_stop:
                        break

                # Mark as read if configured
                if self.config.auto_mark_read:
                    if self.db.mark_article_as_read(article["id"]):
                        self.logger.debug(f"Marked article {article['id']} as read")
                    else:
                        self.logger.warning(
                            f"Failed to mark article {article['id']} as read"
                        )

                # Pause between articles (except for the last one)
                if i < len(articles) - 1 and self.config.pause_between_articles:
                    self.logger.debug("Pausing between articles...")

                    # Interactive pause - can be interrupted
                    pause_start = time.time()
                    while time.time() - pause_start < 2:
                        with self.playback_lock:
                            if self.should_stop or self.should_skip:
                                break
                        time.sleep(0.1)

            # Show session summary
            self.progress_tracker.show_session_summary()

            # Conclusion
            if not self.should_stop:
                conclusion_text = (
                    f"That's all for now! I've read {len(articles)} articles for you."
                )
                self.logger.info("Session complete!")
                self.speak_text(conclusion_text)

            # End interactive session
            if self.interactive_controller:
                self.interactive_controller.end_session()

        except Exception as e:
            self.logger.error(f"An error occurred: {e}")
            self.speak_text("Sorry, an error occurred while reading articles.")
            if self.interactive_controller:
                self.interactive_controller.end_session()
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
