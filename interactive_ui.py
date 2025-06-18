"""
Interactive UI components for Chirpy RSS Reader.

Provides keyboard controls, rich terminal formatting, and interactive features
for enhanced user experience during article reading sessions.
"""

import time
from collections.abc import Callable
from typing import Any

try:
    import keyboard

    KEYBOARD_AVAILABLE = True
except ImportError:
    keyboard = None
    KEYBOARD_AVAILABLE = False
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from base_ui import (
    BaseArticleSelector,
    BaseInteractiveController,
    BaseProgressTracker,
    PlaybackState,
)
from config import ChirpyConfig, get_logger


class InteractiveController(BaseInteractiveController):
    """Handles keyboard input and playback control during article reading."""

    def __init__(self, config: ChirpyConfig):
        """Initialize interactive controller."""
        super().__init__(config)

        # Setup keyboard hooks specific to this implementation
        self._setup_keyboard_hooks()

    def _setup_keyboard_hooks(self) -> None:
        """Set up keyboard event handlers."""
        if not KEYBOARD_AVAILABLE:
            self.logger.warning(
                "Keyboard library not available - interactive controls disabled"
            )
            return

        try:
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
        except Exception as e:
            self.logger.warning(f"Failed to setup keyboard hooks: {e}")
            self.logger.info("Interactive controls will be limited")

    def _on_space_key(self, event: Any) -> None:
        """Handle spacebar press for pause/resume (keyboard event wrapper)."""
        with self._lock:
            self._handle_space_key()

    def _on_right_arrow(self, event: Any) -> None:
        """Handle right arrow for skip forward (keyboard event wrapper)."""
        with self._lock:
            self._handle_right_arrow()

    def _on_left_arrow(self, event: Any) -> None:
        """Handle left arrow for previous article (keyboard event wrapper)."""
        with self._lock:
            self._handle_left_arrow()

    def _on_up_arrow(self, event: Any) -> None:
        """Handle up arrow for volume up (keyboard event wrapper)."""
        with self._lock:
            old_volume = self.volume_level
            self._adjust_volume(0.1)
            if self.volume_level != old_volume:
                self._display_volume_change()

    def _on_down_arrow(self, event: Any) -> None:
        """Handle down arrow for volume down (keyboard event wrapper)."""
        with self._lock:
            old_volume = self.volume_level
            self._adjust_volume(-0.1)
            if self.volume_level != old_volume:
                self._display_volume_change()

    def _on_speed_up(self, event: Any) -> None:
        """Handle + key for speed increase (keyboard event wrapper)."""
        with self._lock:
            old_speed = self.current_speed_multiplier
            self._handle_speed_up()
            if self.current_speed_multiplier != old_speed:
                self._display_speed_change()

    def _on_speed_down(self, event: Any) -> None:
        """Handle - key for speed decrease (keyboard event wrapper)."""
        with self._lock:
            old_speed = self.current_speed_multiplier
            self._handle_speed_down()
            if self.current_speed_multiplier != old_speed:
                self._display_speed_change()

    def _display_volume_change(self) -> None:
        """Display volume change feedback."""
        volume_percent = int(self.volume_level * 100)
        self.console.print(f"[cyan]🔊 Volume: {volume_percent}%[/cyan]")
        self.logger.info(f"Volume adjusted to {volume_percent}%")

    def _display_speed_change(self) -> None:
        """Display speed change feedback."""
        speed_text = f"{self.current_speed_multiplier:.1f}x"
        self.console.print(f"[cyan]🎚️ Speed: {speed_text}[/cyan]")
        self.logger.info(f"Speed adjusted to {speed_text}")

    def _on_quit(self, event: Any) -> None:
        """Handle q key for quit (keyboard event wrapper)."""
        with self._lock:
            self._handle_quit()
            self.console.print("[red]⏹️  Stopping playback[/red]")
            self.logger.info("Playback stopped by user")

    def _on_help(self, event: Any) -> None:
        """Handle h key for help display (keyboard event wrapper)."""
        self._handle_help()

    def _on_save_session(self, event: Any) -> None:
        """Handle s key for save session (keyboard event wrapper)."""
        self._handle_save_session()
        # TODO: Implement session saving
        self.console.print("[yellow]Session saving not yet implemented[/yellow]")

    def _show_help(self) -> None:
        """Display keyboard shortcuts help."""
        help_table = Table(title="🎮 Keyboard Controls")
        help_table.add_column("Key", style="cyan", width=12)
        help_table.add_column("Action", style="white")

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

        self.console.print(Panel(help_table, border_style="blue"))

    def set_callbacks(
        self,
        pause_callback: Callable[[], None] | None = None,
        resume_callback: Callable[[], None] | None = None,
        skip_callback: Callable[[], None] | None = None,
        speed_callback: Callable[[float], None] | None = None,
        volume_callback: Callable[[float], None] | None = None,
        quit_callback: Callable[[], None] | None = None,
        help_callback: Callable[[], None] | None = None,
        save_callback: Callable[[], None] | None = None,
        # Legacy parameter names for backwards compatibility
        pause: Callable[[], None] | None = None,
        resume: Callable[[], None] | None = None,
        skip: Callable[[], None] | None = None,
        speed: Callable[[float], None] | None = None,
        volume: Callable[[float], None] | None = None,
        stop: Callable[[], None] | None = None,
    ) -> None:
        """Set callback functions for playback control."""
        # Handle legacy parameter names
        if pause is not None:
            pause_callback = pause
        if resume is not None:
            resume_callback = resume
        if skip is not None:
            skip_callback = skip
        if speed is not None:
            speed_callback = speed
        if volume is not None:
            volume_callback = volume
        if stop is not None:
            quit_callback = stop

        # Call base class method
        super().set_callbacks(
            pause_callback=pause_callback,
            resume_callback=resume_callback,
            skip_callback=skip_callback,
            speed_callback=speed_callback,
            volume_callback=volume_callback,
            quit_callback=quit_callback,
            help_callback=help_callback,
            save_callback=save_callback,
        )

        # Keep backwards compatibility with old names
        self.stop_callback = quit_callback

    def start_session(self, total_articles: int) -> None:
        """Start interactive session."""
        super().start_session(total_articles)
        self.current_article_index = 0
        self.state = PlaybackState.PLAYING

        # Show initial help
        self.console.print("[bold green]🎧 Interactive Mode Enabled[/bold green]")
        self.console.print("Press [bold cyan]H[/bold cyan] for keyboard shortcuts")

    def update_progress(
        self, article_index: int, article_title: str, words_spoken: int = 0
    ) -> None:
        """Update current playback progress."""
        with self._lock:
            # Call base class method first
            super().update_progress(article_index, article_title, words_spoken)

            # Additional display for this implementation
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

        if KEYBOARD_AVAILABLE:
            try:
                keyboard.unhook_all()
            except Exception as e:
                self.logger.debug(f"Error during keyboard cleanup: {e}")

        self.console.print("[bold green]✅ Session completed[/bold green]")
        self.logger.info("Interactive session ended")


class ArticleSelector(BaseArticleSelector):
    """Interactive article selection interface."""

    def __init__(self, config: ChirpyConfig):
        """Initialize article selector."""
        self.config = config
        self.console = Console()
        self.logger = get_logger(__name__)

    def show_article_menu(self, articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Show interactive article selection menu."""
        if not articles:
            self.console.print("[yellow]No articles available[/yellow]")
            return []

        # Filter options
        filtered_articles = self._apply_filters(articles)

        if not filtered_articles:
            self.console.print("[yellow]No articles match the current filters[/yellow]")
            return []

        self.console.print("[bold blue]📰 Article Selection[/bold blue]")

        # Show filter status
        self._show_filter_status(len(articles), len(filtered_articles))

        # Create article table
        table = self._create_article_table(filtered_articles[:20])
        self.console.print(table)

        # Show selection instructions
        self._show_selection_instructions()

        # For now, return unread articles (interactive selection coming later)
        selected_articles = [
            article
            for article in filtered_articles
            if not self._is_article_read(article)
        ]

        return selected_articles[: self.config.max_articles]

    def _apply_filters(self, articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply filters to article list."""
        filtered = articles.copy()

        # Filter by read status (default: unread only)
        filtered = [
            article for article in filtered if not self._is_article_read(article)
        ]

        # Sort by published date (newest first)
        filtered.sort(key=lambda x: x.get("published", ""), reverse=True)

        return filtered

    def _is_article_read(self, article: dict[str, Any]) -> bool:
        """Check if article is marked as read."""
        # This will be enhanced when we implement proper read tracking
        read_status = article.get("read", False)
        return bool(read_status)

    def _show_filter_status(self, total: int, filtered: int) -> None:
        """Show current filter status."""
        filter_info = f"Showing {filtered} of {total} articles (unread only)"
        self.console.print(f"[dim]{filter_info}[/dim]")

    def _create_article_table(self, articles: list[dict[str, Any]]) -> Table:
        """Create formatted article table."""
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="white", ratio=2)
        table.add_column("Published", style="cyan", width=12)
        table.add_column("Language", style="magenta", width=8)
        table.add_column("Preview", style="dim", ratio=1)

        for i, article in enumerate(articles):
            title = self._format_title(article.get("title", "No title"))
            published = self._format_date(article.get("published", "Unknown"))
            language = self._format_language(article)
            preview = self._format_preview(article.get("summary", ""))

            table.add_row(str(i + 1), title, published, language, preview)

        return table

    def _format_title(self, title: str) -> str:
        """Format article title for display."""
        if len(title) > 60:
            return title[:57] + "..."
        return title

    def _format_date(self, date_str: str) -> str:
        """Format publication date for display."""
        # Extract just the date part if it's a full datetime
        if " " in date_str:
            return date_str.split(" ")[0][:10]
        return date_str[:10]

    def _format_language(self, article: dict[str, Any]) -> str:
        """Format language information for display."""
        detected_lang = article.get("detected_language", "unknown")
        is_translated = article.get("is_translated", False)

        if is_translated:
            return f"[yellow]{detected_lang}→ja[/yellow]"
        elif detected_lang != "unknown":
            return f"[green]{detected_lang}[/green]"
        else:
            return "[dim]unknown[/dim]"

    def _format_preview(self, summary: str) -> str:
        """Format article preview for display."""
        if not summary:
            return "[dim]No preview[/dim]"

        # Get first sentence or first 50 characters
        first_sentence = summary.split(".")[0][:50]
        if len(first_sentence) < len(summary):
            first_sentence += "..."

        return first_sentence

    def _show_selection_instructions(self) -> None:
        """Show article selection instructions."""
        instructions = Panel(
            "[bold]Selection Mode:[/bold] Automatically selecting unread articles\n"
            "[dim]Future: Interactive selection with number input and search[/dim]",
            title="📝 Instructions",
            border_style="blue",
        )
        self.console.print(instructions)

    def search_articles(
        self, articles: list[dict[str, Any]], query: str
    ) -> list[dict[str, Any]]:
        """Search articles by title or content."""
        if not query.strip():
            return articles

        query_lower = query.lower()
        filtered = []

        for article in articles:
            title = article.get("title", "").lower()
            summary = article.get("summary", "").lower()

            if query_lower in title or query_lower in summary:
                filtered.append(article)

        return filtered

    def filter_by_date_range(
        self, articles: list[dict[str, Any]], days_back: int = 7
    ) -> list[dict[str, Any]]:
        """Filter articles by date range."""
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days_back)
        filtered = []

        for article in articles:
            pub_date_str = article.get("published", "")
            try:
                # Try to parse the date (this may need adjustment based on date format)
                pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                if pub_date >= cutoff_date:
                    filtered.append(article)
            except (ValueError, AttributeError):
                # If date parsing fails, include the article
                filtered.append(article)

        return filtered


class ProgressTracker(BaseProgressTracker):
    """Tracks and displays reading progress and statistics."""

    def __init__(self, config: ChirpyConfig):
        """Initialize progress tracker."""
        self.config = config
        self.console = Console()
        self.logger = get_logger(__name__)

        self.session_start = time.time()
        self.articles_read = 0
        self.words_read = 0
        self.estimated_time_remaining = 0.0

    def create_progress_display(self, total_articles: int) -> Live:
        """Create live progress display."""
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("[blue]{task.completed}/{task.total} articles"),
        )

        progress.add_task("Reading articles...", total=total_articles)
        return Live(progress, console=self.console, refresh_per_second=4)

    def update_statistics(self, **kwargs: Any) -> None:
        """Update reading statistics."""
        # Handle legacy article parameter
        if "article" in kwargs:
            article = kwargs["article"]
            self.articles_read += 1

            # Estimate word count
            title_words = len(article.get("title", "").split())
            summary_words = len(article.get("summary", "").split())
            self.words_read += title_words + summary_words

            # Update estimated time
            elapsed = time.time() - self.session_start
            if self.articles_read > 0:
                avg_time_per_article = elapsed / self.articles_read
                max_articles = self.config.max_articles
                remaining_articles = max(0, max_articles - self.articles_read)
                time_remaining = avg_time_per_article * remaining_articles
                self.estimated_time_remaining = time_remaining

        # Call base class method
        super().update_statistics(**kwargs)

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
