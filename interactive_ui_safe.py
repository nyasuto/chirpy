"""
Safe Interactive UI components for Chirpy RSS Reader.

Provides keyboard controls and rich terminal formatting with graceful
fallbacks for environments where keyboard library is not available.
"""

import time
from collections.abc import Callable
from typing import Any

from rich.panel import Panel
from rich.table import Table

from base_ui import (
    BaseArticleSelector,
    BaseInteractiveController,
    BaseProgressTracker,
    PlaybackState,
)
from config import ChirpyConfig


class InteractiveController(BaseInteractiveController):
    """Handles keyboard input and playback control during article reading."""

    def __init__(self, config: ChirpyConfig):
        """Initialize interactive controller."""
        super().__init__(config)

        # Try to setup keyboard hooks safely
        self.keyboard_available = self._setup_keyboard_hooks_safe()

    def _setup_keyboard_hooks(self) -> None:
        """Setup keyboard hooks (overrides base method)."""
        self._setup_keyboard_hooks_safe()

    def _setup_keyboard_hooks_safe(self) -> bool:
        """Safely set up keyboard event handlers."""
        try:
            # Import keyboard only when needed
            import keyboard

            keyboard.on_press_key("space", self._on_space_key)
            keyboard.on_press_key("right", self._on_right_arrow)
            keyboard.on_press_key("left", self._on_left_arrow)
            keyboard.on_press_key("up", self._on_up_arrow)
            keyboard.on_press_key("down", self._on_down_arrow)
            keyboard.on_press_key("=", self._on_speed_up)
            keyboard.on_press_key("-", self._on_speed_down)
            keyboard.on_press_key("q", self._on_quit)
            keyboard.on_press_key("h", self._on_help)
            keyboard.on_press_key("s", self._on_save_session)

            self.logger.info("Interactive keyboard controls enabled")
            return True
        except (ImportError, Exception) as e:
            self.logger.warning(f"Keyboard controls not available: {e}")
            self.logger.info("Interactive mode will use basic controls only")
            return False

    def _on_space_key(self, event: Any) -> None:
        """Handle spacebar press for pause/resume (keyboard event wrapper)."""
        with self._lock:
            super()._handle_space_key()

    def _on_right_arrow(self, event: Any) -> None:
        """Handle right arrow for skip forward (keyboard event wrapper)."""
        with self._lock:
            super()._handle_right_arrow()

    def _on_left_arrow(self, event: Any) -> None:
        """Handle left arrow for previous article (keyboard event wrapper)."""
        with self._lock:
            super()._handle_left_arrow()

    def _on_up_arrow(self, event: Any) -> None:
        """Handle up arrow for volume up (keyboard event wrapper)."""
        with self._lock:
            self._adjust_volume(0.1)
            volume_percent = int(self.volume_level * 100)
            self.console.print(f"[cyan]🔊 Volume: {volume_percent}%[/cyan]")
            self.logger.info(f"Volume adjusted to {volume_percent}%")

    def _on_down_arrow(self, event: Any) -> None:
        """Handle down arrow for volume down (keyboard event wrapper)."""
        with self._lock:
            self._adjust_volume(-0.1)
            volume_percent = int(self.volume_level * 100)
            self.console.print(f"[cyan]🔊 Volume: {volume_percent}%[/cyan]")
            self.logger.info(f"Volume adjusted to {volume_percent}%")

    def _on_speed_up(self, event: Any) -> None:
        """Handle + key for speed increase (keyboard event wrapper)."""
        with self._lock:
            self._adjust_speed(0.2)
            speed_text = f"🎚️ Speed: {self.current_speed_multiplier:.1f}x"
            self.console.print(f"[cyan]{speed_text}[/cyan]")
            self.logger.info(f"Speed adjusted to {self.current_speed_multiplier:.1f}x")

    def _on_speed_down(self, event: Any) -> None:
        """Handle - key for speed decrease (keyboard event wrapper)."""
        with self._lock:
            self._adjust_speed(-0.2)
            speed_text = f"🎚️ Speed: {self.current_speed_multiplier:.1f}x"
            self.console.print(f"[cyan]{speed_text}[/cyan]")
            self.logger.info(f"Speed adjusted to {self.current_speed_multiplier:.1f}x")

    def _on_quit(self, event: Any) -> None:
        """Handle q key for quit (keyboard event wrapper)."""
        with self._lock:
            super()._handle_quit()

    def _on_help(self, event: Any) -> None:
        """Handle h key for help display (keyboard event wrapper)."""
        super()._handle_help()

    def _on_save_session(self, event: Any) -> None:
        """Handle s key for save session (keyboard event wrapper)."""
        # TODO: Implement session saving
        self.console.print("[yellow]Session saving not yet implemented[/yellow]")

    def _pause_playback(self) -> None:
        """Pause current playback (override for safe mode display)."""
        super()._pause_playback()
        if self.state == PlaybackState.PAUSED:
            self.console.print("[yellow]⏸️  Paused[/yellow]")
            self.logger.info("Playback paused by user")

    def _resume_playback(self) -> None:
        """Resume paused playback (override for safe mode display)."""
        super()._resume_playback()
        if self.state == PlaybackState.PLAYING:
            self.console.print("[green]▶️  Resumed[/green]")
            self.logger.info("Playback resumed by user")

    def _skip_forward(self) -> None:
        """Skip to next article (override for safe mode display)."""
        if self.skip_callback and self.current_article_index < self.total_articles - 1:
            super()._skip_forward()
            self.console.print("[blue]⏭️  Skipping to next article[/blue]")
            self.logger.info("Skipped to next article")

    def _skip_backward(self) -> None:
        """Skip to previous article (override for safe mode display)."""
        if self.current_article_index > 0:
            self.console.print("[blue]⏮️  Previous article (not yet implemented)[/blue]")
            # TODO: Implement previous article functionality

    def _stop_playback(self) -> None:
        """Stop playback and exit (override for safe mode display)."""
        super()._stop_playback()
        self.console.print("[red]⏹️  Stopping playback[/red]")
        self.logger.info("Playback stopped by user")

    def _show_help(self) -> None:
        """Display keyboard shortcuts help."""
        help_table = Table(title="🎮 Keyboard Controls")
        help_table.add_column("Key", style="cyan", width=12)
        help_table.add_column("Action", style="white")

        if self.keyboard_available:
            help_table.add_row("Space", "Pause/Resume playback")
            help_table.add_row("→ (Right)", "Skip to next article")
            help_table.add_row("← (Left)", "Previous article")
            help_table.add_row("↑ (Up)", "Volume up")
            help_table.add_row("↓ (Down)", "Volume down")
            help_table.add_row("+ (Plus)", "Speed up")
            help_table.add_row("- (Minus)", "Speed down")
            help_table.add_row("Q", "Quit application")
            help_table.add_row("H", "Show this help")
            help_table.add_row("S", "Save session (coming soon)")
        else:
            help_table.add_row("Ctrl+C", "Quit application")
            help_table.add_row("N/A", "Keyboard controls not available")

        self.console.print(Panel(help_table, border_style="blue"))

    def set_legacy_callbacks(
        self,
        pause: Callable[[], None] | None = None,
        resume: Callable[[], None] | None = None,
        skip: Callable[[], None] | None = None,
        speed: Callable[[float], None] | None = None,
        volume: Callable[[float], None] | None = None,
        stop: Callable[[], None] | None = None,
    ) -> None:
        """Set callback functions for playback control (legacy interface)."""
        # Map old callback names to new ones
        super().set_callbacks(
            pause_callback=pause,
            resume_callback=resume,
            skip_callback=skip,
            speed_callback=speed,
            volume_callback=volume,
            quit_callback=stop,
        )

    def start_session(self, total_articles: int) -> None:
        """Start interactive session."""
        super().start_session(total_articles)
        self.state = PlaybackState.PLAYING

        # Show initial help
        self.console.print("[bold green]🎧 Interactive Mode Enabled[/bold green]")
        if self.keyboard_available:
            self.console.print("Press [bold cyan]H[/bold cyan] for keyboard shortcuts")
        else:
            self.console.print("Keyboard controls not available - use Ctrl+C to quit")

    def update_progress(
        self, article_index: int, article_title: str, words_spoken: int = 0
    ) -> None:
        """Update current playback progress."""
        with self._lock:
            self.current_article_index = article_index

            # Create progress display
            progress_text = (
                f"📖 Article {article_index + 1}/{self.total_articles}: "
                f"{article_title[:50]}{'...' if len(article_title) > 50 else ''}"
            )

            # Show playback status
            status_color = {
                PlaybackState.PLAYING: "green",
                PlaybackState.PAUSED: "yellow",
                PlaybackState.STOPPED: "red",
                PlaybackState.SKIPPING: "blue",
            }.get(self.state, "white")

            status_text = f"[{status_color}]{self.state.value.upper()}[/{status_color}]"

            self.console.print(f"{progress_text} | {status_text}")

    def end_session(self) -> None:
        """End interactive session and cleanup."""
        self._running = False
        self.state = PlaybackState.STOPPED

        if self.keyboard_available:
            try:
                import keyboard

                keyboard.unhook_all()
            except Exception as e:
                self.logger.debug(f"Error during keyboard cleanup: {e}")

        self.console.print("[bold green]✅ Session completed[/bold green]")
        self.logger.info("Interactive session ended")


class ArticleSelector(BaseArticleSelector):
    """Interactive article selection interface - safe version."""

    def __init__(self, config: ChirpyConfig):
        """Initialize article selector."""
        super().__init__(config)

    def show_article_menu(self, articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Show article selection - simplified safe version."""
        if not articles:
            self.console.print("[yellow]No articles available[/yellow]")
            return []

        self.console.print("[bold blue]📰 Article Selection (Auto-mode)[/bold blue]")

        # Auto-select unread articles
        selected_articles = [
            article for article in articles if not article.get("read", False)
        ]

        return selected_articles[: self.config.max_articles]


class ProgressTracker(BaseProgressTracker):
    """Tracks and displays reading progress - safe version."""

    def __init__(self, config: ChirpyConfig):
        """Initialize progress tracker."""
        super().__init__(config)
        self.session_start = time.time()
        self.articles_read = 0
        self.words_read = 0

    def update_statistics(self, **kwargs: Any) -> None:
        """Update reading statistics."""
        # Handle both old-style article dict and new kwargs style
        if "article" in kwargs:
            article = kwargs["article"]
            self.articles_read += 1
            title_words = len(article.get("title", "").split())
            summary_words = len(article.get("summary", "").split())
            self.words_read += title_words + summary_words

            # Update base class statistics
            super().update_statistics(
                articles_processed=1, total_words=title_words + summary_words
            )
        else:
            # Pass through to base class
            super().update_statistics(**kwargs)

    def update_article_statistics(self, article: dict[str, Any]) -> None:
        """Update reading statistics for a specific article."""
        self.update_statistics(article=article)

    def show_session_summary(self) -> None:
        """Display session reading summary."""
        elapsed = time.time() - self.session_start
        summary_table = Table(title="📊 Reading Session Summary")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="white")

        summary_table.add_row("Articles Read", str(self.articles_read))
        summary_table.add_row("Words Read", f"{self.words_read:,}")
        summary_table.add_row("Session Time", f"{elapsed:.1f} seconds")

        if self.articles_read > 0:
            avg_wpm = (self.words_read / elapsed) * 60 if elapsed > 0 else 0
            summary_table.add_row("Average Speed", f"{avg_wpm:.0f} WPM")

        self.console.print(Panel(summary_table, border_style="green"))
