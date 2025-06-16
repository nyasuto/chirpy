#!/usr/bin/env python3
"""
Chirpy RSS Reader - Main Application

MVP RSS reader with text-to-speech functionality.
Reads articles from SQLite database and provides audio narration.
"""

import logging
import subprocess
import sys
import threading
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
from interactive_ui import ArticleSelector, InteractiveController, ProgressTracker


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
        self.tts_engine = self._initialize_tts()
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
        """Speak text using available TTS method with interactive controls."""
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

        # Split text into sentences for pause/resume support
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

            # Apply speed adjustment
            adjusted_rate = int(self.config.tts_rate * self.current_speed_multiplier)

            # Try TTS engine first
            if self.tts_engine:
                try:
                    # Update rate for current sentence
                    self.tts_engine.setProperty("rate", adjusted_rate)
                    self.tts_engine.setProperty("volume", self.config.tts_volume)
                    self.tts_engine.say(sentence)
                    self.tts_engine.runAndWait()
                    continue
                except Exception as e:
                    self.logger.warning(
                        f"TTS engine error: {e}, falling back to 'say' command"
                    )

            # Fallback to system 'say' command
            try:
                rate_arg = ["-r", str(adjusted_rate)] if adjusted_rate != 180 else []
                subprocess.run(
                    ["say"] + rate_arg + [sentence],
                    check=True,
                    capture_output=True,
                    timeout=30
                )
            except (
                subprocess.CalledProcessError,
                FileNotFoundError,
                subprocess.TimeoutExpired,
            ) as e:
                self.logger.error(f"Text-to-speech not available: {e}")
                break

    def _split_text_for_playback(self, text: str) -> list[str]:
        """Split text into manageable chunks for interactive playback."""
        # Split by sentences, but keep reasonable chunk sizes
        import re
        sentences = re.split(r'[.!?]+', text)
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
                stop=self._stop_playback
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
        if self.tts_engine:
            try:
                self.tts_engine.setProperty("volume", volume)
            except Exception as e:
                self.logger.debug(f"Failed to adjust TTS volume: {e}")

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
                selected_indices = self.article_selector.show_article_menu(all_articles)
                articles = [all_articles[i] for i in selected_indices]
            else:
                articles = all_articles[:self.config.max_articles]

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
                f"Welcome to Chirpy! I found {len(articles)} articles "
                "to read for you."
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
                    self.interactive_controller.update_progress(i, article['title'])

                self.progress_tracker.update_statistics(article)

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
