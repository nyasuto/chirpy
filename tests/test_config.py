"""Tests for ChirpyConfig configuration loading and validation."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from config import ChirpyConfig


class TestChirpyConfig:
    """Test suite for ChirpyConfig class."""

    @pytest.mark.unit
    def test_default_config_creation(self):
        """Test creating config with default values."""
        config = ChirpyConfig()

        assert config.database_path == "data/articles.db"
        assert config.max_articles == 3
        assert config.max_summary_length == 500
        assert config.openai_model == "gpt-4o"
        assert config.tts_rate == 180
        assert config.tts_volume == 0.9
        assert config.log_level == "INFO"
        assert config.auto_mark_read is True
        assert config.speech_enabled is True
        assert config.interactive_mode is False

    @pytest.mark.unit
    def test_config_creation_with_custom_values(self):
        """Test creating config with custom values."""
        config = ChirpyConfig(
            database_path="/custom/path/db.sqlite",
            max_articles=5,
            max_summary_length=1000,
            tts_rate=200,
            tts_volume=0.8,
            auto_mark_read=False,
            speech_enabled=False,
        )

        assert config.database_path == "/custom/path/db.sqlite"
        assert config.max_articles == 5
        assert config.max_summary_length == 1000
        assert config.tts_rate == 200
        assert config.tts_volume == 0.8
        assert config.auto_mark_read is False
        assert config.speech_enabled is False

    @pytest.mark.unit
    def test_config_validation_ranges(self):
        """Test that config values are validated within proper ranges."""
        config = ChirpyConfig(
            max_articles=0,  # Below minimum
            tts_rate=10,  # Below minimum
            tts_volume=-0.5,  # Below minimum
            openai_temperature=3.0,  # Above maximum
        )

        # Should be clamped to valid ranges
        assert config.max_articles == 1  # Minimum 1
        assert config.tts_rate == 50  # Minimum 50
        assert config.tts_volume == 0.0  # Minimum 0.0
        assert config.openai_temperature == 2.0  # Maximum 2.0

    @pytest.mark.unit
    def test_config_validation_upper_bounds(self):
        """Test config validation for upper bounds."""
        config = ChirpyConfig(
            max_articles=150,  # Above maximum
            tts_rate=600,  # Above maximum
            tts_volume=1.5,  # Above maximum
        )

        # Should be clamped to valid ranges
        assert config.max_articles == 100  # Maximum 100
        assert config.tts_rate == 500  # Maximum 500
        assert config.tts_volume == 1.0  # Maximum 1.0

    @pytest.mark.unit
    def test_path_expansion(self):
        """Test that database path is properly expanded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ChirpyConfig(database_path=f"{tmpdir}/test.db")

            # Path should be absolute
            assert Path(config.database_path).is_absolute()
            assert config.database_path.endswith("test.db")

    @pytest.mark.unit
    def test_update_from_dict(self):
        """Test updating config from dictionary."""
        config = ChirpyConfig()

        updates = {
            "max_articles": 7,
            "tts_rate": 220,
            "speech_enabled": False,
            "log_level": "DEBUG",
        }

        config.update_from_dict(updates)

        assert config.max_articles == 7
        assert config.tts_rate == 220
        assert config.speech_enabled is False
        assert config.log_level == "DEBUG"
        # Other values should remain unchanged
        assert config.max_summary_length == 500

    @pytest.mark.unit
    def test_update_from_dict_with_validation(self):
        """Test that update_from_dict still applies validation."""
        config = ChirpyConfig()

        updates = {
            "max_articles": 200,  # Above maximum
            "tts_volume": 2.0,  # Above maximum
        }

        config.update_from_dict(updates)

        # Should be clamped to valid ranges
        assert config.max_articles == 100
        assert config.tts_volume == 1.0

    @pytest.mark.unit
    def test_update_from_dict_ignores_invalid_keys(self):
        """Test that update_from_dict ignores keys that don't exist."""
        config = ChirpyConfig()

        updates = {
            "invalid_key": "should_be_ignored",
            "max_articles": 5,
        }

        config.update_from_dict(updates)

        assert config.max_articles == 5
        # Invalid key should not cause errors or create new attributes
        assert not hasattr(config, "invalid_key")

    @pytest.mark.unit
    def test_from_env_with_no_env_vars(self):
        """Test creating config from environment with no env vars set."""
        # Clean environment is handled by conftest.py fixture
        # Note: load_dotenv() may still load from .env file if present
        config = ChirpyConfig.from_env()

        # Should use default values or .env file values
        assert config.database_path == "data/articles.db"
        assert config.max_articles == 3
        assert config.tts_rate == 180
        # openai_model may be set from .env file, so check for either value
        assert config.openai_model in ["gpt-3.5-turbo", "gpt-4o"]

    @pytest.mark.unit
    def test_from_env_with_env_vars(self):
        """Test creating config from environment variables."""
        env_vars = {
            "CHIRPY_DATABASE_PATH": "/tmp/test.db",
            "CHIRPY_MAX_ARTICLES": "5",
            "CHIRPY_MAX_SUMMARY_LENGTH": "800",
            "OPENAI_API_KEY": "test-key-123",
            "OPENAI_MODEL": "gpt-4",
            "TTS_RATE": "200",
            "TTS_VOLUME": "0.8",
            "LOG_LEVEL": "DEBUG",
            "AUTO_MARK_READ": "false",
            "SPEECH_ENABLED": "false",
            "INTERACTIVE_MODE": "true",
        }

        with patch.dict(os.environ, env_vars):
            config = ChirpyConfig.from_env()

        assert config.database_path == "/tmp/test.db"
        assert config.max_articles == 5
        assert config.max_summary_length == 800
        assert config.openai_api_key == "test-key-123"
        assert config.openai_model == "gpt-4"
        assert config.tts_rate == 200
        assert config.tts_volume == 0.8
        assert config.log_level == "DEBUG"
        assert config.auto_mark_read is False
        assert config.speech_enabled is False
        assert config.interactive_mode is True

    @pytest.mark.unit
    def test_from_env_with_invalid_env_values(self):
        """Test from_env handles invalid environment values gracefully."""
        env_vars = {
            "CHIRPY_MAX_ARTICLES": "not_a_number",
            "TTS_VOLUME": "invalid_float",
            "AUTO_MARK_READ": "not_a_boolean",
        }

        with patch.dict(os.environ, env_vars):
            # Should not raise exception, but use defaults or handle gracefully
            with pytest.raises((ValueError, TypeError)):
                ChirpyConfig.from_env()

    @pytest.mark.unit
    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = ChirpyConfig(
            max_articles=5,
            tts_rate=200,
            speech_enabled=False,
        )

        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["max_articles"] == 5
        assert config_dict["tts_rate"] == 200
        assert config_dict["speech_enabled"] is False
        assert "database_path" in config_dict
        assert "openai_model" in config_dict

    @pytest.mark.unit
    def test_openai_tts_config_defaults(self):
        """Test OpenAI TTS configuration defaults."""
        config = ChirpyConfig()

        assert config.tts_quality == "hd"
        assert config.openai_tts_voice == "nova"
        assert config.audio_format == "mp3"
        assert config.tts_speed_multiplier == 1.0

    @pytest.mark.unit
    def test_openai_tts_config_from_env(self):
        """Test OpenAI TTS configuration from environment."""
        env_vars = {
            "TTS_QUALITY": "standard",
            "OPENAI_TTS_VOICE": "nova",
            "AUDIO_FORMAT": "opus",
            "TTS_SPEED_MULTIPLIER": "1.5",
        }

        with patch.dict(os.environ, env_vars):
            config = ChirpyConfig.from_env()

        assert config.tts_quality == "standard"
        assert config.openai_tts_voice == "nova"
        assert config.audio_format == "opus"
        assert config.tts_speed_multiplier == 1.5

    @pytest.mark.unit
    def test_translation_config_defaults(self):
        """Test translation configuration defaults."""
        config = ChirpyConfig()

        assert config.auto_translate is True
        assert config.target_language == "ja"
        assert config.preserve_original is True
        assert config.translation_provider == "openai"

    @pytest.mark.unit
    def test_config_immutability_after_post_init(self):
        """Test that post_init validation is applied correctly."""
        # Create config with invalid values
        config = ChirpyConfig()

        # Manually set invalid values (bypassing __init__)
        config.max_articles = 200
        config.tts_volume = 2.0

        # Call post_init to trigger validation
        config.__post_init__()

        # Should be corrected to valid ranges
        assert config.max_articles == 100
        assert config.tts_volume == 1.0
