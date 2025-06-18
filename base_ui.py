"""
Base UI components for Chirpy RSS Reader.

Provides common functionality for interactive UI components to eliminate
code duplication between interactive_ui.py and interactive_ui_safe.py.
"""

import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import ChirpyConfig, get_logger


class PlaybackState(Enum):
    """Playback control states."""

    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    SKIPPING = "skipping"


class BaseInteractiveController(ABC):
    """Base class for interactive controllers with common functionality."""

    def __init__(self, config: ChirpyConfig):
        """Initialize base interactive controller."""
        self.config = config
        self.logger = get_logger(__name__)
        self.console = Console()

        # Playback state
        self.state = PlaybackState.STOPPED
        self.current_article_index = 0
        self.total_articles = 0
        self.current_speed_multiplier = 1.0
        self.volume_level = config.tts_volume

        # Control callbacks
        self.pause_callback: Callable[[], None] | None = None
        self.resume_callback: Callable[[], None] | None = None
        self.skip_callback: Callable[[], None] | None = None
        self.speed_callback: Callable[[float], None] | None = None
        self.volume_callback: Callable[[float], None] | None = None
        self.quit_callback: Callable[[], None] | None = None
        self.help_callback: Callable[[], None] | None = None
        self.save_callback: Callable[[], None] | None = None

        # Threading
        self._input_thread: threading.Thread | None = None
        self._running = False
        self._lock = threading.Lock()

        # Statistics
        self.session_start_time = time.time()
        self.articles_read = 0
        self.total_words_spoken = 0
        self.pauses_count = 0
        self.speed_adjustments = 0

    def _handle_space_key(self) -> None:
        """Handle spacebar press for play/pause toggle."""
        if self.state == PlaybackState.PLAYING:
            self._pause_playback()
        elif self.state == PlaybackState.PAUSED:
            self._resume_playback()

    def _handle_right_arrow(self) -> None:
        """Handle right arrow press for skip forward."""
        self._skip_forward()

    def _handle_left_arrow(self) -> None:
        """Handle left arrow press for skip backward."""
        self._skip_backward()

    def _handle_up_arrow(self) -> None:
        """Handle up arrow press for speed increase."""
        self._handle_speed_up()

    def _handle_down_arrow(self) -> None:
        """Handle down arrow press for speed decrease."""
        self._handle_speed_down()

    def _handle_speed_up(self) -> None:
        """Increase playback speed."""
        self._adjust_speed(0.25)

    def _handle_speed_down(self) -> None:
        """Decrease playback speed."""
        self._adjust_speed(-0.25)

    def _handle_quit(self) -> None:
        """Handle quit request."""
        self._stop_playback()

    def _handle_help(self) -> None:
        """Show help information."""
        self._show_help()

    def _handle_save_session(self) -> None:
        """Handle save session request."""
        if self.save_callback:
            self.save_callback()

    def _pause_playback(self) -> None:
        """Pause current playback."""
        if self.state == PlaybackState.PLAYING:
            self.state = PlaybackState.PAUSED
            self.pauses_count += 1
            if self.pause_callback:
                self.pause_callback()

    def _resume_playback(self) -> None:
        """Resume paused playback."""
        if self.state == PlaybackState.PAUSED:
            self.state = PlaybackState.PLAYING
            if self.resume_callback:
                self.resume_callback()

    def _skip_forward(self) -> None:
        """Skip to next article."""
        if self.state in (PlaybackState.PLAYING, PlaybackState.PAUSED):
            self.state = PlaybackState.SKIPPING
            if self.skip_callback:
                self.skip_callback()

    def _skip_backward(self) -> None:
        """Skip to previous article."""
        if self.current_article_index > 0:
            self.current_article_index -= 1

    def _adjust_speed(self, delta: float) -> None:
        """Adjust playback speed by delta amount."""
        new_speed = max(0.25, min(4.0, self.current_speed_multiplier + delta))
        if new_speed != self.current_speed_multiplier:
            self.current_speed_multiplier = new_speed
            self.speed_adjustments += 1
            if self.speed_callback:
                self.speed_callback(new_speed)

    def _adjust_volume(self, delta: float) -> None:
        """Adjust volume by delta amount."""
        new_volume = max(0.0, min(1.0, self.volume_level + delta))
        if new_volume != self.volume_level:
            self.volume_level = new_volume
            if self.volume_callback:
                self.volume_callback(new_volume)

    def _stop_playback(self) -> None:
        """Stop playback and cleanup."""
        self._running = False
        self.state = PlaybackState.STOPPED
        if self.quit_callback:
            self.quit_callback()

    @abstractmethod
    def _setup_keyboard_hooks(self) -> None:
        """Setup keyboard event hooks. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _show_help(self) -> None:
        """Show help information. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def end_session(self) -> None:
        """End the session and cleanup. Must be implemented by subclasses."""
        pass

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
    ) -> None:
        """Set control callbacks."""
        self.pause_callback = pause_callback
        self.resume_callback = resume_callback
        self.skip_callback = skip_callback
        self.speed_callback = speed_callback
        self.volume_callback = volume_callback
        self.quit_callback = quit_callback
        self.help_callback = help_callback
        self.save_callback = save_callback

    def start_session(self, total_articles: int) -> None:
        """Start interactive session."""
        self.total_articles = total_articles
        self.session_start_time = time.time()
        self._running = True
        self._setup_keyboard_hooks()
        self.logger.info(f"Interactive session started with {total_articles} articles")

    def update_progress(
        self, article_index: int, article_title: str, words_spoken: int = 0
    ) -> None:
        """Update progress information."""
        with self._lock:
            self.current_article_index = article_index
            if words_spoken > 0:
                self.total_words_spoken += words_spoken
            if article_index > self.articles_read:
                self.articles_read = article_index

        # Display progress
        title_excerpt = article_title[:50]
        article_num = f"{article_index + 1}/{self.total_articles}"
        progress_text = f"Article {article_num}: {title_excerpt}..."
        state_text = f"State: {self.state.value.title()}"
        speed_text = f"Speed: {self.current_speed_multiplier:.1f}x"
        volume_text = f"Volume: {self.volume_level:.1f}"

        panel_content = f"{progress_text}\n{state_text} | {speed_text} | {volume_text}"
        panel = Panel(panel_content, title="Chirpy Progress", border_style="blue")
        self.console.print(panel)


class BaseArticleSelector(ABC):
    """Base class for article selection functionality."""

    def __init__(self, config: ChirpyConfig):
        """Initialize base article selector."""
        self.config = config
        self.logger = get_logger(__name__)
        self.console = Console()

    @abstractmethod
    def show_article_menu(self, articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Show article selection menu. Must be implemented by subclasses."""
        pass


class BaseProgressTracker:
    """Base class for progress tracking functionality."""

    def __init__(self, config: ChirpyConfig):
        """Initialize base progress tracker."""
        self.config = config
        self.logger = get_logger(__name__)
        self.console = Console()
        self.session_stats = {
            "start_time": time.time(),
            "articles_processed": 0,
            "total_words": 0,
            "total_duration": 0.0,
            "pauses": 0,
            "speed_changes": 0,
        }

    def update_statistics(self, **kwargs: Any) -> None:
        """Update session statistics."""
        for key, value in kwargs.items():
            if key in self.session_stats:
                if key in (
                    "articles_processed",
                    "total_words",
                    "pauses",
                    "speed_changes",
                ):
                    self.session_stats[key] += value
                else:
                    self.session_stats[key] = value

    def show_session_summary(self) -> None:
        """Display session summary."""
        duration = time.time() - self.session_stats["start_time"]

        table = Table(title="Session Summary", border_style="green")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Duration", f"{duration:.1f} seconds")
        articles_count = str(self.session_stats["articles_processed"])
        table.add_row("Articles Processed", articles_count)
        table.add_row("Total Words", str(self.session_stats["total_words"]))
        table.add_row("Pauses", str(self.session_stats["pauses"]))
        table.add_row("Speed Changes", str(self.session_stats["speed_changes"]))

        if self.session_stats["total_words"] > 0 and duration > 0:
            wpm = (self.session_stats["total_words"] / duration) * 60
            table.add_row("Words per Minute", f"{wpm:.1f}")

        self.console.print(table)


class UIComponentFactory:
    """Factory for creating appropriate UI components."""

    @staticmethod
    def create_controller(
        config: ChirpyConfig, safe_mode: bool = False
    ) -> BaseInteractiveController:
        """Create appropriate interactive controller based on mode and availability."""
        if safe_mode:
            from interactive_ui_safe import InteractiveController as SafeController

            return SafeController(config)  # type: ignore[return-value]
        else:
            from interactive_ui import InteractiveController as FullController

            return FullController(config)  # type: ignore[return-value]

    @staticmethod
    def create_article_selector(
        config: ChirpyConfig, safe_mode: bool = False
    ) -> BaseArticleSelector:
        """Create appropriate article selector based on mode."""
        if safe_mode:
            from interactive_ui_safe import ArticleSelector as SafeSelector

            return SafeSelector(config)  # type: ignore[return-value]
        else:
            from interactive_ui import ArticleSelector as FullSelector

            return FullSelector(config)  # type: ignore[return-value]

    @staticmethod
    def create_progress_tracker(
        config: ChirpyConfig, safe_mode: bool = False
    ) -> BaseProgressTracker:
        """Create appropriate progress tracker based on mode."""
        if safe_mode:
            from interactive_ui_safe import ProgressTracker as SafeTracker

            return SafeTracker(config)  # type: ignore[return-value]
        else:
            from interactive_ui import ProgressTracker as FullTracker

            return FullTracker(config)  # type: ignore[return-value]
