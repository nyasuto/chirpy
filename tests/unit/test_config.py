"""
Unit tests for ChirpyConfig configuration management.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from config import ChirpyConfig


class TestChirpyConfig:
    """Test ChirpyConfig configuration loading and validation."""

    def test_default_config_creation(self):
        """Test creating config with default values."""
        config = ChirpyConfig()

        assert config.database_path == "data/articles.db"
        assert config.max_articles == 3
        assert config.max_summary_length == 500
        assert config.openai_api_key is None
        assert config.openai_model == "gpt-4o"
        assert config.tts_engine == "pyttsx3"
        assert config.tts_rate == 180
        assert config.speech_enabled is True
        assert config.auto_translate is True

    def test_config_with_custom_values(self):
        """Test creating config with custom values."""
        config = ChirpyConfig(
            database_path="/custom/path.db",
            max_articles=5,
            openai_api_key="test-key",
            tts_rate=200,
            speech_enabled=False,
        )

        assert config.database_path == "/custom/path.db"
        assert config.max_articles == 5
        assert config.openai_api_key == "test-key"
        assert config.tts_rate == 200
        assert config.speech_enabled is False

    @patch.dict(
        os.environ,
        {
            "CHIRPY_DATABASE_PATH": "/env/test.db",
            "CHIRPY_MAX_ARTICLES": "10",
            "OPENAI_API_KEY": "env-api-key",
            "OPENAI_MODEL": "gpt-4o",
            "TTS_RATE": "220",
            "SPEECH_ENABLED": "false",
            "AUTO_TRANSLATE": "false",
            "TARGET_LANGUAGE": "en",
        },
    )
    def test_config_from_env(self):
        """Test loading config from environment variables."""
        config = ChirpyConfig.from_env()

        assert config.database_path == "/env/test.db"
        assert config.max_articles == 10
        assert config.openai_api_key == "env-api-key"
        assert config.openai_model == "gpt-4o"
        assert config.tts_rate == 220
        assert config.speech_enabled is False
        assert config.auto_translate is False
        assert config.target_language == "en"

    @patch.dict(os.environ, {"TTS_RATE": "invalid"})
    def test_config_invalid_int_env_var(self):
        """Test handling invalid integer environment variables."""
        config = ChirpyConfig.from_env()
        # Should use default value when env var is invalid
        assert config.tts_rate == 180

    @patch.dict(os.environ, {"SPEECH_ENABLED": "invalid"})
    def test_config_invalid_bool_env_var(self):
        """Test handling invalid boolean environment variables."""
        config = ChirpyConfig.from_env()
        # Should use default value when env var is invalid
        assert config.speech_enabled is True

    @patch.dict(os.environ, {"TTS_VOLUME": "2.0"})
    def test_config_out_of_range_volume(self):
        """Test handling out-of-range volume values."""
        config = ChirpyConfig.from_env()
        # Should clamp to valid range
        assert config.tts_volume == 1.0

    @patch.dict(os.environ, {"TTS_VOLUME": "-0.5"})
    def test_config_negative_volume(self):
        """Test handling negative volume values."""
        config = ChirpyConfig.from_env()
        # Should clamp to valid range
        assert config.tts_volume == 0.0

    def test_config_with_dotenv_file(self, temp_dir: Path):
        """Test loading config from .env file."""
        env_file = temp_dir / ".env"
        env_file.write_text("""
CHIRPY_DATABASE_PATH=/dotenv/test.db
CHIRPY_MAX_ARTICLES=7
OPENAI_API_KEY=dotenv-api-key
TTS_RATE=190
SPEECH_ENABLED=false
""")

        with patch.dict(os.environ, {}, clear=True):
            # Clear env and load from file
            from dotenv import load_dotenv

            load_dotenv(env_file)
            config = ChirpyConfig.from_env()

        assert config.database_path == "/dotenv/test.db"
        assert config.max_articles == 7
        assert config.openai_api_key == "dotenv-api-key"
        assert config.tts_rate == 190
        assert config.speech_enabled is False

    def test_config_validation_database_path(self):
        """Test database path validation."""
        # Empty database path should be invalid
        with pytest.raises(ValueError, match="Database path cannot be empty"):
            ChirpyConfig(database_path="")

    def test_config_validation_max_articles(self):
        """Test max articles validation."""
        # Negative max articles should be invalid
        with pytest.raises(ValueError, match="max_articles must be positive"):
            ChirpyConfig(max_articles=0)

        with pytest.raises(ValueError, match="max_articles must be positive"):
            ChirpyConfig(max_articles=-1)

    def test_config_validation_tts_rate(self):
        """Test TTS rate validation."""
        # Out of range TTS rate should be invalid
        with pytest.raises(ValueError, match="tts_rate must be between 50 and 500"):
            ChirpyConfig(tts_rate=49)

        with pytest.raises(ValueError, match="tts_rate must be between 50 and 500"):
            ChirpyConfig(tts_rate=501)

    def test_config_validation_tts_volume(self):
        """Test TTS volume validation."""
        # Out of range volume should be invalid
        with pytest.raises(ValueError, match="tts_volume must be between 0.0 and 1.0"):
            ChirpyConfig(tts_volume=-0.1)

        with pytest.raises(ValueError, match="tts_volume must be between 0.0 and 1.0"):
            ChirpyConfig(tts_volume=1.1)

    def test_config_validation_openai_temperature(self):
        """Test OpenAI temperature validation."""
        # Out of range temperature should be invalid
        with pytest.raises(
            ValueError, match="openai_temperature must be between 0.0 and 2.0"
        ):
            ChirpyConfig(openai_temperature=-0.1)

        with pytest.raises(
            ValueError, match="openai_temperature must be between 0.0 and 2.0"
        ):
            ChirpyConfig(openai_temperature=2.1)

    def test_config_validation_openai_max_tokens(self):
        """Test OpenAI max tokens validation."""
        # Invalid max tokens should be invalid
        with pytest.raises(ValueError, match="openai_max_tokens must be positive"):
            ChirpyConfig(openai_max_tokens=0)

        with pytest.raises(ValueError, match="openai_max_tokens must be positive"):
            ChirpyConfig(openai_max_tokens=-1)

    def test_config_str_representation(self):
        """Test config string representation."""
        config = ChirpyConfig(
            database_path="/test.db", max_articles=5, openai_api_key="test-key"
        )

        config_str = str(config)
        assert "ChirpyConfig" in config_str
        assert "/test.db" in config_str
        assert "max_articles=5" in config_str
        # API key should be masked
        assert "test-key" not in config_str
        assert "***" in config_str or "hidden" in config_str.lower()

    def test_config_repr_representation(self):
        """Test config repr representation."""
        config = ChirpyConfig(database_path="/test.db", max_articles=5)

        config_repr = repr(config)
        assert "ChirpyConfig" in config_repr
        assert "/test.db" in config_repr
