"""
High-quality TTS Service for Chirpy RSS Reader.

Provides OpenAI TTS API integration with fallback to system TTS.
"""

import hashlib
import os
import tempfile
import time
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from openai import OpenAI

from config import ChirpyConfig, get_logger


class TTSQuality(Enum):
    """TTS quality levels."""

    BASIC = "basic"  # System TTS (pyttsx3/say)
    STANDARD = "standard"  # OpenAI TTS standard
    HD = "hd"  # OpenAI TTS HD


class OpenAIVoice(Enum):
    """OpenAI TTS voice options."""

    ALLOY = "alloy"  # Balanced, neutral
    ECHO = "echo"  # Clear, professional
    FABLE = "fable"  # Warm, engaging
    ONYX = "onyx"  # Deep, authoritative
    NOVA = "nova"  # Bright, energetic
    SHIMMER = "shimmer"  # Soft, pleasant


class AudioFormat(Enum):
    """Supported audio formats."""

    MP3 = "mp3"
    OPUS = "opus"
    AAC = "aac"
    FLAC = "flac"
    WAV = "wav"


class TTSProvider(Protocol):
    """Protocol for TTS providers."""

    def speak_text(self, text: str, voice: str | None = None) -> bool:
        """Speak text using the provider."""
        ...

    def is_available(self) -> bool:
        """Check if provider is available."""
        ...

    def get_cost_estimate(self, text: str) -> float:
        """Estimate cost for text in USD."""
        ...


class OpenAITTSProvider:
    """OpenAI TTS API provider."""

    def __init__(self, config: ChirpyConfig):
        """Initialize OpenAI TTS provider."""
        self.config = config
        self.logger = get_logger(__name__)
        self.client: OpenAI | None = None
        self.temp_dir = Path(tempfile.gettempdir()) / "chirpy_audio"
        self.temp_dir.mkdir(exist_ok=True)

        # Audio cache directory
        self.cache_dir = Path.home() / ".chirpy" / "audio_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize client if API key available
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
                self.logger.info("OpenAI TTS provider initialized")

                # Perform startup cleanup if enabled
                if self.config.audio_cache_cleanup_on_startup:
                    self._cleanup_expired_cache()

            except Exception as e:
                self.logger.warning(f"Failed to initialize OpenAI client: {e}")
        else:
            self.logger.info("OpenAI API key not found - provider unavailable")

    def is_available(self) -> bool:
        """Check if OpenAI TTS is available."""
        return self.client is not None

    def get_cost_estimate(self, text: str) -> float:
        """Estimate cost for text in USD."""
        # OpenAI TTS pricing: $15 per 1M characters
        char_count = len(text)
        return (char_count / 1_000_000) * 15.0

    def _get_cache_key(self, text: str, voice: str, model: str, speed: float) -> str:
        """Generate cache key for audio content."""
        content = f"{text}|{voice}|{model}|{speed}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cached_audio(self, cache_key: str) -> Path | None:
        """Get cached audio file if it exists."""
        cache_file = self.cache_dir / f"{cache_key}.mp3"
        if cache_file.exists():
            # Check if cache file is not too old (max 30 days)
            if time.time() - cache_file.stat().st_mtime < 30 * 24 * 3600:
                return cache_file
            else:
                # Remove old cache file
                try:
                    cache_file.unlink()
                except Exception as e:
                    self.logger.debug(f"Failed to remove old cache file: {e}")
        return None

    def _save_to_cache(self, cache_key: str, audio_data: bytes) -> Path:
        """Save audio data to cache."""
        cache_file = self.cache_dir / f"{cache_key}.mp3"
        with open(cache_file, "wb") as f:
            f.write(audio_data)

        # Check if we need size-based cleanup after saving
        self._check_cache_size_limits()

        return cache_file

    def _cleanup_expired_cache(self) -> None:
        """Remove expired cache files proactively."""
        if not self.cache_dir.exists():
            return

        current_time = time.time()
        max_age_seconds = self.config.audio_cache_max_age_days * 24 * 3600
        removed_count = 0
        removed_size = 0

        try:
            for cache_file in self.cache_dir.glob("*.mp3"):
                try:
                    file_age = current_time - cache_file.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_size = cache_file.stat().st_size
                        cache_file.unlink()
                        removed_count += 1
                        removed_size += file_size
                        self.logger.debug(
                            f"Removed expired cache file: {cache_file.name}"
                        )

                except OSError as e:
                    self.logger.debug(f"Failed to remove cache file {cache_file}: {e}")

        except Exception as e:
            self.logger.warning(f"Error during cache cleanup: {e}")

        if removed_count > 0:
            size_mb = removed_size / (1024 * 1024)
            self.logger.info(
                f"Cache cleanup: removed {removed_count} expired files "
                f"({size_mb:.1f} MB)"
            )

    def _get_cache_size_mb(self) -> float:
        """Get current cache size in MB."""
        if not self.cache_dir.exists():
            return 0.0

        total_size = 0
        try:
            for cache_file in self.cache_dir.glob("*.mp3"):
                try:
                    total_size += cache_file.stat().st_size
                except OSError:
                    continue  # Skip files we can't read
        except Exception:
            return 0.0

        return total_size / (1024 * 1024)

    def _check_cache_size_limits(self) -> None:
        """Check cache size and perform cleanup if needed."""
        current_size = self._get_cache_size_mb()
        max_size = self.config.audio_cache_max_size_mb
        threshold_size = max_size * self.config.audio_cache_cleanup_threshold

        if current_size > threshold_size:
            self.logger.info(
                f"Cache size ({current_size:.1f} MB) exceeds threshold, cleaning up..."
            )
            self._cleanup_by_size(max_size)

    def _cleanup_by_size(self, target_size_mb: float) -> None:
        """Remove oldest cache files to stay within size limit."""
        if not self.cache_dir.exists():
            return

        try:
            # Get all cache files with their modification times
            cache_files = []
            for cache_file in self.cache_dir.glob("*.mp3"):
                try:
                    stat = cache_file.stat()
                    cache_files.append((cache_file, stat.st_mtime, stat.st_size))
                except OSError:
                    continue

            # Sort by modification time (oldest first)
            cache_files.sort(key=lambda x: x[1])

            current_size = sum(size for _, _, size in cache_files) / (1024 * 1024)
            removed_count = 0
            removed_size = 0

            # Remove oldest files until we're under the target size
            for cache_file, _, file_size in cache_files:
                if current_size <= target_size_mb:
                    break

                try:
                    cache_file.unlink()
                    current_size -= file_size / (1024 * 1024)
                    removed_size += file_size
                    removed_count += 1
                    self.logger.debug(f"Removed old cache file: {cache_file.name}")
                except OSError as e:
                    self.logger.debug(f"Failed to remove cache file {cache_file}: {e}")

            if removed_count > 0:
                size_mb = removed_size / (1024 * 1024)
                self.logger.info(
                    f"Size-based cleanup: removed {removed_count} files "
                    f"({size_mb:.1f} MB)"
                )

        except Exception as e:
            self.logger.warning(f"Error during size-based cleanup: {e}")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        if not self.cache_dir.exists():
            return {
                "total_files": 0,
                "total_size_mb": 0.0,
                "oldest_file_age_days": 0,
                "cache_dir": str(self.cache_dir),
            }

        try:
            cache_files = list(self.cache_dir.glob("*.mp3"))
            total_files = len(cache_files)

            if total_files == 0:
                return {
                    "total_files": 0,
                    "total_size_mb": 0.0,
                    "oldest_file_age_days": 0,
                    "cache_dir": str(self.cache_dir),
                }

            current_time = time.time()
            total_size = 0
            oldest_time = current_time

            for cache_file in cache_files:
                try:
                    stat = cache_file.stat()
                    total_size += stat.st_size
                    oldest_time = min(oldest_time, stat.st_mtime)
                except OSError:
                    continue

            oldest_age_days = (current_time - oldest_time) / (24 * 3600)

            return {
                "total_files": total_files,
                "total_size_mb": total_size / (1024 * 1024),
                "oldest_file_age_days": oldest_age_days,
                "cache_dir": str(self.cache_dir),
            }

        except Exception as e:
            self.logger.warning(f"Error getting cache stats: {e}")
            return {
                "total_files": 0,
                "total_size_mb": 0.0,
                "oldest_file_age_days": 0,
                "cache_dir": str(self.cache_dir),
                "error": str(e),
            }

    def clear_cache(self) -> int:
        """Clear all cache files. Returns number of files removed."""
        if not self.cache_dir.exists():
            return 0

        removed_count = 0
        try:
            for cache_file in self.cache_dir.glob("*.mp3"):
                try:
                    cache_file.unlink()
                    removed_count += 1
                except OSError as e:
                    self.logger.debug(f"Failed to remove cache file {cache_file}: {e}")

            if removed_count > 0:
                self.logger.info(f"Cleared {removed_count} cache files")

        except Exception as e:
            self.logger.warning(f"Error clearing cache: {e}")

        return removed_count

    def speak_text(self, text: str, voice: str | None = None) -> bool:
        """Generate and play speech using OpenAI TTS with caching."""
        if not self.is_available() or not self.client:
            return False

        if not text.strip():
            return True

        try:
            # Use configured voice or default
            voice_name = (
                voice or self.config.openai_tts_voice or OpenAIVoice.ALLOY.value
            )

            # Determine model based on quality setting
            model = "tts-1-hd" if self.config.tts_quality == "hd" else "tts-1"
            speed = self.config.tts_speed_multiplier or 1.0

            # Check cache first
            cache_key = self._get_cache_key(text, voice_name, model, speed)
            cached_file = self._get_cached_audio(cache_key)

            if cached_file:
                self.logger.info(f"Using cached audio for text: {text[:50]}...")
                self._play_audio_file(cached_file)
                return True

            self.logger.info(f"Generating TTS: {model} voice={voice_name}")

            # Generate speech
            # Generate speech
            audio_format = self.config.audio_format or "mp3"
            response = self.client.audio.speech.create(
                model=model,
                voice=voice_name,  # type: ignore
                input=text,
                response_format=audio_format,  # type: ignore
                speed=speed,
            )

            # Save to cache
            cached_file = self._save_to_cache(cache_key, response.content)

            # Play audio file
            self._play_audio_file(cached_file)

            return True

        except Exception as e:
            self.logger.error(f"OpenAI TTS failed: {e}")
            return False

    def _play_audio_file(self, audio_file: Path) -> None:
        """Play audio file using system player."""
        import subprocess
        import sys

        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["afplay", str(audio_file)], check=True)
            elif sys.platform.startswith("linux"):
                # Try different players
                for player in ["paplay", "aplay", "mpg123", "ffplay"]:
                    try:
                        subprocess.run(
                            [player, str(audio_file)], check=True, capture_output=True
                        )
                        break
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
                else:
                    raise Exception("No audio player found")
            elif sys.platform == "win32":
                import winsound

                winsound.PlaySound(str(audio_file), winsound.SND_FILENAME)
            else:
                raise Exception(f"Unsupported platform: {sys.platform}")

        except Exception as e:
            self.logger.error(f"Failed to play audio: {e}")
            raise


class SystemTTSProvider:
    """System TTS provider (pyttsx3/say fallback)."""

    def __init__(self, config: ChirpyConfig):
        """Initialize system TTS provider."""
        self.config = config
        self.logger = get_logger(__name__)

        # Try to import pyttsx3
        try:
            import pyttsx3  # type: ignore

            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", config.tts_rate)
            self.engine.setProperty("volume", config.tts_volume)
            self.pyttsx3_available = True
            self.logger.info("System TTS provider initialized with pyttsx3")
        except ImportError:
            self.engine = None
            self.pyttsx3_available = False
            self.logger.info(
                "System TTS provider initialized with 'say' command fallback"
            )

    def is_available(self) -> bool:
        """System TTS is always available as fallback."""
        return True

    def get_cost_estimate(self, text: str) -> float:
        """System TTS is free."""
        return 0.0

    def speak_text(self, text: str, voice: str | None = None) -> bool:
        """Speak text using system TTS."""
        if not text.strip():
            return True

        try:
            if self.pyttsx3_available and self.engine:
                self.engine.say(text)
                self.engine.runAndWait()
                return True
            else:
                # Fallback to 'say' command
                import subprocess

                subprocess.run(
                    ["say", "-r", str(self.config.tts_rate), text],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
                return True

        except Exception as e:
            self.logger.error(f"System TTS failed: {e}")
            return False


class EnhancedTTSService:
    """Enhanced TTS service with multiple provider support."""

    def __init__(self, config: ChirpyConfig):
        """Initialize enhanced TTS service."""
        self.config = config
        self.logger = get_logger(__name__)

        # Initialize providers
        self.providers: dict[TTSQuality, TTSProvider] = {}

        # Always have system TTS as fallback
        self.providers[TTSQuality.BASIC] = SystemTTSProvider(config)

        # Initialize OpenAI TTS if available
        openai_provider = OpenAITTSProvider(config)
        if openai_provider.is_available():
            self.providers[TTSQuality.STANDARD] = openai_provider
            self.providers[TTSQuality.HD] = openai_provider

        # Determine current provider
        quality_str = config.tts_quality or "basic"
        self.current_quality = TTSQuality(quality_str)
        self.current_provider = self._get_best_available_provider()

        self.logger.info(
            f"Enhanced TTS service initialized with {len(self.providers)} providers"
        )
        self.logger.info(f"Current quality: {self.current_quality.value}")
        self.logger.info(
            f"Available qualities: {[q.value for q in self.providers.keys()]}"
        )

    def _get_best_available_provider(self) -> TTSProvider:
        """Get the best available provider for current quality setting."""
        if self.current_quality in self.providers:
            return self.providers[self.current_quality]

        # Fallback priority: HD -> STANDARD -> BASIC
        fallback_order = [TTSQuality.HD, TTSQuality.STANDARD, TTSQuality.BASIC]

        for quality in fallback_order:
            if quality in self.providers:
                self.logger.info(f"Falling back to {quality.value} quality")
                return self.providers[quality]

        # Should never happen since BASIC is always available
        raise RuntimeError("No TTS providers available")

    def speak_text(self, text: str, voice: str | None = None) -> bool:
        """Speak text using the current provider."""
        if not text.strip():
            return True

        # Show cost estimate for paid services
        if self.current_quality != TTSQuality.BASIC:
            cost = self.current_provider.get_cost_estimate(text)
            if cost > 0.01:  # Only show if cost is significant
                self.logger.info(f"Estimated cost: ${cost:.4f}")

        # Try current provider
        success = self.current_provider.speak_text(text, voice)

        if not success and self.current_quality != TTSQuality.BASIC:
            # Fallback to system TTS
            self.logger.warning("Primary TTS failed, falling back to system TTS")
            return self.providers[TTSQuality.BASIC].speak_text(text, voice)

        return success

    def set_quality(self, quality: TTSQuality) -> bool:
        """Change TTS quality if provider is available."""
        if quality in self.providers:
            self.current_quality = quality
            self.current_provider = self.providers[quality]
            self.logger.info(f"TTS quality changed to {quality.value}")
            return True
        else:
            self.logger.warning(f"TTS quality {quality.value} not available")
            return False

    def get_available_qualities(self) -> list[TTSQuality]:
        """Get list of available TTS qualities."""
        return list(self.providers.keys())

    def get_cost_estimate(self, text: str) -> float:
        """Get cost estimate for current provider."""
        return self.current_provider.get_cost_estimate(text)

    def is_available(self) -> bool:
        """Check if service is available."""
        return len(self.providers) > 0

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics from OpenAI provider."""
        for provider in self.providers.values():
            if isinstance(provider, OpenAITTSProvider):
                return provider.get_cache_stats()
        return {"error": "OpenAI TTS provider not available"}

    def clear_cache(self) -> int:
        """Clear cache files from OpenAI provider."""
        for provider in self.providers.values():
            if isinstance(provider, OpenAITTSProvider):
                return provider.clear_cache()
        return 0

    def cleanup_cache(self) -> None:
        """Manually trigger cache cleanup."""
        for provider in self.providers.values():
            if isinstance(provider, OpenAITTSProvider):
                provider._cleanup_expired_cache()
                break
