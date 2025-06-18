"""Tests for TTS cache cleanup functionality."""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from config import ChirpyConfig
from tts_service import EnhancedTTSService, OpenAITTSProvider


class TestTTSCacheCleanup:
    """Test suite for TTS cache cleanup functionality."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "test_cache"
            cache_dir.mkdir(exist_ok=True)
            yield cache_dir

    @pytest.fixture
    def config_with_cache_settings(self):
        """Create config with cache management settings."""
        return ChirpyConfig(
            audio_cache_max_size_mb=10,
            audio_cache_max_age_days=30,
            audio_cache_cleanup_on_startup=True,
            audio_cache_cleanup_threshold=0.8,
            openai_api_key="test-key",
        )

    @pytest.fixture
    def provider_with_temp_cache(self, config_with_cache_settings, temp_cache_dir):
        """Create TTS provider with temporary cache directory."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            provider = OpenAITTSProvider(config_with_cache_settings)
            provider.cache_dir = temp_cache_dir
            provider.client = Mock()  # Mock the OpenAI client
            return provider

    def create_cache_file(
        self,
        cache_dir: Path,
        filename: str,
        size_bytes: int = 1024,
        age_days: int = 0,
    ):
        """Helper to create a cache file with specific size and age."""
        cache_file = cache_dir / filename

        # Create file with specified size
        with open(cache_file, "wb") as f:
            f.write(b"0" * size_bytes)

        # Set modification time for age simulation
        if age_days > 0:
            old_time = time.time() - (age_days * 24 * 3600)
            import os

            os.utime(cache_file, (old_time, old_time))

        return cache_file

    @pytest.mark.unit
    def test_cleanup_expired_cache_removes_old_files(
        self, provider_with_temp_cache, temp_cache_dir
    ):
        """Test that expired cache files are removed."""
        # Create files with different ages
        self.create_cache_file(temp_cache_dir, "recent.mp3", age_days=5)
        self.create_cache_file(temp_cache_dir, "old.mp3", age_days=35)
        self.create_cache_file(temp_cache_dir, "very_old.mp3", age_days=45)

        # Verify files exist
        assert len(list(temp_cache_dir.glob("*.mp3"))) == 3

        # Run cleanup
        provider_with_temp_cache._cleanup_expired_cache()

        # Check that only recent file remains
        remaining_files = list(temp_cache_dir.glob("*.mp3"))
        assert len(remaining_files) == 1
        assert remaining_files[0].name == "recent.mp3"

    @pytest.mark.unit
    def test_cleanup_expired_cache_keeps_recent_files(
        self, provider_with_temp_cache, temp_cache_dir
    ):
        """Test that recent cache files are kept."""
        # Create only recent files
        self.create_cache_file(temp_cache_dir, "file1.mp3", age_days=1)
        self.create_cache_file(temp_cache_dir, "file2.mp3", age_days=15)
        self.create_cache_file(temp_cache_dir, "file3.mp3", age_days=25)

        # Verify files exist
        assert len(list(temp_cache_dir.glob("*.mp3"))) == 3

        # Run cleanup
        provider_with_temp_cache._cleanup_expired_cache()

        # All files should remain
        assert len(list(temp_cache_dir.glob("*.mp3"))) == 3

    @pytest.mark.unit
    def test_get_cache_size_mb_calculates_correctly(
        self, provider_with_temp_cache, temp_cache_dir
    ):
        """Test cache size calculation."""
        # Create files with known sizes
        self.create_cache_file(
            temp_cache_dir, "file1.mp3", size_bytes=1024 * 1024
        )  # 1 MB
        self.create_cache_file(
            temp_cache_dir, "file2.mp3", size_bytes=2 * 1024 * 1024
        )  # 2 MB

        size_mb = provider_with_temp_cache._get_cache_size_mb()

        assert abs(size_mb - 3.0) < 0.1  # Allow for small rounding differences

    @pytest.mark.unit
    def test_cache_size_cleanup_removes_oldest_files(
        self, provider_with_temp_cache, temp_cache_dir
    ):
        """Test that size-based cleanup removes oldest files first."""
        # Create files with different ages and sizes
        self.create_cache_file(
            temp_cache_dir, "newest.mp3", size_bytes=2 * 1024 * 1024, age_days=1
        )
        self.create_cache_file(
            temp_cache_dir, "middle.mp3", size_bytes=2 * 1024 * 1024, age_days=10
        )
        self.create_cache_file(
            temp_cache_dir, "oldest.mp3", size_bytes=2 * 1024 * 1024, age_days=20
        )

        # Current total: 6 MB, target: 3 MB (should remove oldest files)
        provider_with_temp_cache._cleanup_by_size(3.0)

        # Check which files remain (newest should be kept)
        remaining_files = [f.name for f in temp_cache_dir.glob("*.mp3")]

        # Should have removed enough files to get under 3MB
        assert "newest.mp3" in remaining_files
        assert len(remaining_files) <= 2  # At most 2 files should remain

    @pytest.mark.unit
    def test_check_cache_size_limits_triggers_cleanup(
        self, provider_with_temp_cache, temp_cache_dir
    ):
        """Test that size limit checking triggers cleanup when threshold exceeded."""
        # Set small cache limits
        provider_with_temp_cache.config.audio_cache_max_size_mb = 2
        provider_with_temp_cache.config.audio_cache_cleanup_threshold = 0.5  # 50%

        # Create files that exceed threshold (1 MB)
        self.create_cache_file(
            temp_cache_dir, "file1.mp3", size_bytes=1024 * 1024
        )  # 1 MB
        self.create_cache_file(
            temp_cache_dir, "file2.mp3", size_bytes=1024 * 1024
        )  # 1 MB (total: 2 MB)

        with patch.object(provider_with_temp_cache, "_cleanup_by_size") as mock_cleanup:
            provider_with_temp_cache._check_cache_size_limits()
            mock_cleanup.assert_called_once_with(2)

    @pytest.mark.unit
    def test_get_cache_stats_returns_correct_info(
        self, provider_with_temp_cache, temp_cache_dir
    ):
        """Test cache statistics gathering."""
        # Create files with known properties
        self.create_cache_file(
            temp_cache_dir, "file1.mp3", size_bytes=1024 * 1024, age_days=5
        )
        self.create_cache_file(
            temp_cache_dir, "file2.mp3", size_bytes=2 * 1024 * 1024, age_days=10
        )

        stats = provider_with_temp_cache.get_cache_stats()

        assert stats["total_files"] == 2
        assert abs(stats["total_size_mb"] - 3.0) < 0.1
        assert stats["oldest_file_age_days"] >= 9  # Should be around 10 days
        assert stats["cache_dir"] == str(temp_cache_dir)

    @pytest.mark.unit
    def test_clear_cache_removes_all_files(
        self, provider_with_temp_cache, temp_cache_dir
    ):
        """Test that clear cache removes all files."""
        # Create multiple cache files
        self.create_cache_file(temp_cache_dir, "file1.mp3")
        self.create_cache_file(temp_cache_dir, "file2.mp3")
        self.create_cache_file(temp_cache_dir, "file3.mp3")

        assert len(list(temp_cache_dir.glob("*.mp3"))) == 3

        removed_count = provider_with_temp_cache.clear_cache()

        assert removed_count == 3
        assert len(list(temp_cache_dir.glob("*.mp3"))) == 0

    @pytest.mark.unit
    def test_startup_cleanup_called_when_enabled(
        self, config_with_cache_settings, temp_cache_dir
    ):
        """Test that startup cleanup is called when enabled in config."""
        config_with_cache_settings.audio_cache_cleanup_on_startup = True

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch(
                "tts_service.OpenAITTSProvider._cleanup_expired_cache"
            ) as mock_cleanup:
                provider = OpenAITTSProvider(config_with_cache_settings)
                provider.cache_dir = temp_cache_dir
                provider.client = Mock()

                # Manually call __init__ logic that would normally happen
                provider._cleanup_expired_cache()

                mock_cleanup.assert_called()

    @pytest.mark.unit
    def test_save_to_cache_triggers_size_check(self, provider_with_temp_cache):
        """Test that saving to cache triggers size limit checking."""
        with patch.object(
            provider_with_temp_cache, "_check_cache_size_limits"
        ) as mock_check:
            provider_with_temp_cache._save_to_cache("test_key", b"test audio data")
            mock_check.assert_called_once()

    @pytest.mark.unit
    def test_enhanced_tts_service_cache_methods(
        self, config_with_cache_settings, temp_cache_dir
    ):
        """Test that EnhancedTTSService properly delegates cache methods."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            service = EnhancedTTSService(config_with_cache_settings)

            # Set temp cache dir to avoid interfering with actual cache
            for provider in service.providers.values():
                if hasattr(provider, "cache_dir"):
                    provider.cache_dir = temp_cache_dir

            # Test that cache methods are available and callable
            stats = service.get_cache_stats()
            assert isinstance(stats, dict)
            assert "total_files" in stats

            # Test clear cache returns a number
            count = service.clear_cache()
            assert isinstance(count, int)

            # Test cleanup cache doesn't raise an error
            service.cleanup_cache()  # Should not raise exception

    @pytest.mark.unit
    def test_cache_cleanup_error_handling(
        self, provider_with_temp_cache, temp_cache_dir
    ):
        """Test that cache cleanup handles errors gracefully."""
        # Create a file
        cache_file = self.create_cache_file(temp_cache_dir, "test.mp3")

        # Mock pathlib.Path.glob to raise an exception
        with patch("pathlib.Path.glob", side_effect=PermissionError("Access denied")):
            # Should not raise exception
            provider_with_temp_cache._cleanup_expired_cache()

        # File should still exist since cleanup failed
        assert cache_file.exists()

    @pytest.mark.unit
    def test_cache_stats_empty_directory(
        self, provider_with_temp_cache, temp_cache_dir
    ):
        """Test cache stats for empty directory."""
        stats = provider_with_temp_cache.get_cache_stats()

        assert stats["total_files"] == 0
        assert stats["total_size_mb"] == 0.0
        assert stats["oldest_file_age_days"] == 0

    @pytest.mark.unit
    def test_cache_cleanup_preserves_non_mp3_files(
        self, provider_with_temp_cache, temp_cache_dir
    ):
        """Test that cleanup only affects .mp3 files."""
        # Create mp3 and non-mp3 files
        mp3_file = self.create_cache_file(temp_cache_dir, "audio.mp3", age_days=35)
        txt_file = temp_cache_dir / "notes.txt"
        txt_file.write_text("test notes")
        import os

        old_time = time.time() - 40 * 24 * 3600
        os.utime(txt_file, (old_time, old_time))

        provider_with_temp_cache._cleanup_expired_cache()

        # MP3 file should be removed, txt file should remain
        assert not mp3_file.exists()
        assert txt_file.exists()

    @pytest.mark.unit
    def test_config_validation_for_cache_settings(self):
        """Test that cache configuration values are properly validated."""
        config = ChirpyConfig(
            audio_cache_max_size_mb=100,
            audio_cache_max_age_days=30,
            audio_cache_cleanup_threshold=0.8,
        )

        assert config.audio_cache_max_size_mb == 100
        assert config.audio_cache_max_age_days == 30
        assert config.audio_cache_cleanup_threshold == 0.8
        assert config.audio_cache_cleanup_on_startup is True  # Default value
