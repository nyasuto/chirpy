"""Tests for TTS service initialization and fallback logic."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from config import ChirpyConfig
from tts_service import (
    AudioFormat,
    EnhancedTTSService,
    OpenAITTSProvider,
    OpenAIVoice,
    SystemTTSProvider,
    TTSQuality,
)


class TestTTSQuality:
    """Test suite for TTSQuality enum."""

    @pytest.mark.unit
    def test_tts_quality_values(self):
        """Test that TTSQuality enum has correct values."""
        assert TTSQuality.BASIC.value == "basic"
        assert TTSQuality.STANDARD.value == "standard"
        assert TTSQuality.HD.value == "hd"

    @pytest.mark.unit
    def test_tts_quality_creation_from_string(self):
        """Test creating TTSQuality from string values."""
        assert TTSQuality("basic") == TTSQuality.BASIC
        assert TTSQuality("standard") == TTSQuality.STANDARD
        assert TTSQuality("hd") == TTSQuality.HD


class TestOpenAIVoice:
    """Test suite for OpenAIVoice enum."""

    @pytest.mark.unit
    def test_openai_voice_values(self):
        """Test that OpenAIVoice enum has correct values."""
        assert OpenAIVoice.ALLOY.value == "alloy"
        assert OpenAIVoice.ECHO.value == "echo"
        assert OpenAIVoice.FABLE.value == "fable"
        assert OpenAIVoice.ONYX.value == "onyx"
        assert OpenAIVoice.NOVA.value == "nova"
        assert OpenAIVoice.SHIMMER.value == "shimmer"


class TestAudioFormat:
    """Test suite for AudioFormat enum."""

    @pytest.mark.unit
    def test_audio_format_values(self):
        """Test that AudioFormat enum has correct values."""
        assert AudioFormat.MP3.value == "mp3"
        assert AudioFormat.OPUS.value == "opus"
        assert AudioFormat.AAC.value == "aac"
        assert AudioFormat.FLAC.value == "flac"
        assert AudioFormat.WAV.value == "wav"


class TestOpenAITTSProvider:
    """Test suite for OpenAI TTS provider initialization and functionality."""

    @pytest.mark.unit
    def test_openai_provider_initialization_with_api_key(self):
        """Test OpenAI provider initialization with valid API key."""
        config = ChirpyConfig()

        with (
            patch("tts_service.OpenAI") as mock_openai_class,
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}),
        ):
            mock_client = Mock()
            mock_openai_class.return_value = mock_client

            provider = OpenAITTSProvider(config)

            assert provider.config == config
            assert provider.client == mock_client
            assert provider.temp_dir.exists()
            assert provider.cache_dir.exists()
            mock_openai_class.assert_called_once_with(api_key="test-api-key")

    @pytest.mark.unit
    def test_openai_provider_initialization_without_api_key(self):
        """Test OpenAI provider initialization without API key."""
        config = ChirpyConfig()

        with patch.dict("os.environ", {}, clear=True):
            provider = OpenAITTSProvider(config)

            assert provider.config == config
            assert provider.client is None

    @pytest.mark.unit
    def test_openai_provider_initialization_api_error(self):
        """Test OpenAI provider initialization with API error."""
        config = ChirpyConfig()

        with (
            patch("tts_service.OpenAI") as mock_openai_class,
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}),
        ):
            mock_openai_class.side_effect = Exception("API initialization failed")

            provider = OpenAITTSProvider(config)

            assert provider.config == config
            assert provider.client is None

    @pytest.mark.unit
    def test_openai_provider_is_available_with_client(self):
        """Test availability check with initialized client."""
        config = ChirpyConfig()

        with (
            patch("tts_service.OpenAI") as mock_openai_class,
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}),
        ):
            mock_openai_class.return_value = Mock()

            provider = OpenAITTSProvider(config)

            assert provider.is_available() is True

    @pytest.mark.unit
    def test_openai_provider_is_available_without_client(self):
        """Test availability check without client."""
        config = ChirpyConfig()

        with patch.dict("os.environ", {}, clear=True):
            provider = OpenAITTSProvider(config)

            assert provider.is_available() is False

    @pytest.mark.unit
    def test_openai_provider_get_cost_estimate(self):
        """Test cost estimation calculation."""
        config = ChirpyConfig()

        with patch.dict("os.environ", {}, clear=True):
            provider = OpenAITTSProvider(config)

            # Test with 1000 characters
            cost = provider.get_cost_estimate("a" * 1000)
            expected_cost = (1000 / 1_000_000) * 15.0
            assert cost == expected_cost

            # Test with 1 million characters
            cost = provider.get_cost_estimate("a" * 1_000_000)
            assert cost == 15.0

    @pytest.mark.unit
    def test_openai_provider_cache_key_generation(self):
        """Test cache key generation."""
        config = ChirpyConfig()

        with patch.dict("os.environ", {}, clear=True):
            provider = OpenAITTSProvider(config)

            key1 = provider._get_cache_key("test text", "alloy", "tts-1", 1.0)
            key2 = provider._get_cache_key("test text", "alloy", "tts-1", 1.0)
            key3 = provider._get_cache_key("different text", "alloy", "tts-1", 1.0)

            # Same parameters should generate same key
            assert key1 == key2
            # Different parameters should generate different key
            assert key1 != key3
            # Keys should be MD5 hashes (32 chars)
            assert len(key1) == 32

    @pytest.mark.unit
    def test_openai_provider_get_cached_audio_exists(self):
        """Test getting cached audio when file exists."""
        config = ChirpyConfig()

        with (
            patch("os.getenv") as mock_getenv,
            tempfile.TemporaryDirectory() as temp_dir,
        ):
            mock_getenv.return_value = None

            provider = OpenAITTSProvider(config)
            provider.cache_dir = Path(temp_dir)

            # Create a cache file
            cache_key = "test_cache_key"
            cache_file = provider.cache_dir / f"{cache_key}.mp3"
            cache_file.write_bytes(b"fake audio data")

            result = provider._get_cached_audio(cache_key)

            assert result == cache_file
            assert result.exists()

    @pytest.mark.unit
    def test_openai_provider_get_cached_audio_not_exists(self):
        """Test getting cached audio when file doesn't exist."""
        config = ChirpyConfig()

        with (
            patch("os.getenv") as mock_getenv,
            tempfile.TemporaryDirectory() as temp_dir,
        ):
            mock_getenv.return_value = None

            provider = OpenAITTSProvider(config)
            provider.cache_dir = Path(temp_dir)

            result = provider._get_cached_audio("nonexistent_key")

            assert result is None

    @pytest.mark.unit
    def test_openai_provider_save_to_cache(self):
        """Test saving audio data to cache."""
        config = ChirpyConfig()

        with (
            patch("os.getenv") as mock_getenv,
            tempfile.TemporaryDirectory() as temp_dir,
        ):
            mock_getenv.return_value = None

            provider = OpenAITTSProvider(config)
            provider.cache_dir = Path(temp_dir)

            cache_key = "test_save_key"
            audio_data = b"test audio content"

            result = provider._save_to_cache(cache_key, audio_data)

            assert result.exists()
            assert result.read_bytes() == audio_data
            assert result.name == f"{cache_key}.mp3"

    @pytest.mark.unit
    def test_openai_provider_speak_text_unavailable(self):
        """Test speak_text when provider is unavailable."""
        config = ChirpyConfig()

        with patch.dict("os.environ", {}, clear=True):
            provider = OpenAITTSProvider(config)

            result = provider.speak_text("test text")

            assert result is False

    @pytest.mark.unit
    def test_openai_provider_speak_text_empty(self):
        """Test speak_text with empty text."""
        config = ChirpyConfig()

        with (
            patch("tts_service.OpenAI") as mock_openai_class,
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}),
        ):
            mock_openai_class.return_value = Mock()

            provider = OpenAITTSProvider(config)

            result = provider.speak_text("")

            assert result is True

    @pytest.mark.unit
    def test_openai_provider_speak_text_success_with_cache(self):
        """Test successful speech generation using cached audio."""
        config = ChirpyConfig(tts_quality="standard", openai_tts_voice="alloy")

        with (
            patch("tts_service.OpenAI") as mock_openai_class,
            patch("os.getenv") as mock_getenv,
            tempfile.TemporaryDirectory() as temp_dir,
        ):
            mock_getenv.return_value = "test-api-key"
            mock_client = Mock()
            mock_openai_class.return_value = mock_client

            provider = OpenAITTSProvider(config)
            provider.cache_dir = Path(temp_dir)

            # Create cached file
            cache_key = provider._get_cache_key("test text", "alloy", "tts-1", 1.0)
            cache_file = provider.cache_dir / f"{cache_key}.mp3"
            cache_file.write_bytes(b"cached audio data")

            with patch.object(provider, "_play_audio_file") as mock_play:
                result = provider.speak_text("test text")

                assert result is True
                mock_play.assert_called_once_with(cache_file)
                # Should not call OpenAI API since using cache
                mock_client.audio.speech.create.assert_not_called()

    @pytest.mark.unit
    def test_openai_provider_speak_text_success_no_cache(self):
        """Test successful speech generation without cache."""
        config = ChirpyConfig(
            tts_quality="hd",
            openai_tts_voice="echo",
            tts_speed_multiplier=1.2,
            audio_format="mp3",
        )

        with (
            patch("tts_service.OpenAI") as mock_openai_class,
            patch("os.getenv") as mock_getenv,
            tempfile.TemporaryDirectory() as temp_dir,
        ):
            mock_getenv.return_value = "test-api-key"
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = b"generated audio data"
            mock_client.audio.speech.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            provider = OpenAITTSProvider(config)
            provider.cache_dir = Path(temp_dir)

            with patch.object(provider, "_play_audio_file") as mock_play:
                result = provider.speak_text("test text")

                assert result is True

                # Verify API call
                mock_client.audio.speech.create.assert_called_once_with(
                    model="tts-1-hd",
                    voice="echo",
                    input="test text",
                    response_format="mp3",
                    speed=1.2,
                )

                # Verify audio was cached and played
                cache_key = provider._get_cache_key(
                    "test text", "echo", "tts-1-hd", 1.2
                )
                cache_file = provider.cache_dir / f"{cache_key}.mp3"
                assert cache_file.exists()
                assert cache_file.read_bytes() == b"generated audio data"
                mock_play.assert_called_once_with(cache_file)

    @pytest.mark.unit
    def test_openai_provider_speak_text_api_error(self):
        """Test speech generation with API error."""
        config = ChirpyConfig()

        with (
            patch("tts_service.OpenAI") as mock_openai_class,
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}),
        ):
            mock_client = Mock()
            mock_client.audio.speech.create.side_effect = Exception("API Error")
            mock_openai_class.return_value = mock_client

            provider = OpenAITTSProvider(config)

            result = provider.speak_text("test text")

            assert result is False

    @pytest.mark.unit
    def test_openai_provider_play_audio_file_macos(self):
        """Test audio playback on macOS."""
        config = ChirpyConfig()

        with (
            patch("os.getenv") as mock_getenv,
            patch("sys.platform", "darwin"),
            patch("subprocess.run") as mock_run,
        ):
            mock_getenv.return_value = None

            provider = OpenAITTSProvider(config)
            audio_file = Path("/test/audio.mp3")

            provider._play_audio_file(audio_file)

            mock_run.assert_called_once_with(["afplay", str(audio_file)], check=True)

    @pytest.mark.unit
    def test_openai_provider_play_audio_file_linux(self):
        """Test audio playback on Linux."""
        config = ChirpyConfig()

        with (
            patch("os.getenv") as mock_getenv,
            patch("sys.platform", "linux"),
            patch("subprocess.run") as mock_run,
        ):
            mock_getenv.return_value = None

            provider = OpenAITTSProvider(config)
            audio_file = Path("/test/audio.mp3")

            provider._play_audio_file(audio_file)

            # Should try paplay first
            mock_run.assert_called_with(
                ["paplay", str(audio_file)], check=True, capture_output=True
            )

    @pytest.mark.unit
    def test_openai_provider_play_audio_file_windows(self):
        """Test audio playback on Windows."""
        config = ChirpyConfig()

        with patch.dict("os.environ", {}, clear=True), patch("sys.platform", "win32"):
            provider = OpenAITTSProvider(config)
            audio_file = Path("/test/audio.mp3")

            # Mock winsound module import
            mock_winsound = Mock()
            mock_winsound.SND_FILENAME = 0x00020000  # Actual winsound constant

            with patch.dict("sys.modules", {"winsound": mock_winsound}):
                provider._play_audio_file(audio_file)

                mock_winsound.PlaySound.assert_called_once_with(
                    str(audio_file), mock_winsound.SND_FILENAME
                )

    @pytest.mark.unit
    def test_openai_provider_play_audio_file_unsupported_platform(self):
        """Test audio playback on unsupported platform."""
        config = ChirpyConfig()

        with patch.dict("os.environ", {}, clear=True), patch("sys.platform", "unknown"):
            provider = OpenAITTSProvider(config)
            audio_file = Path("/test/audio.mp3")

            with pytest.raises(Exception, match="Unsupported platform"):
                provider._play_audio_file(audio_file)


class TestSystemTTSProvider:
    """Test suite for System TTS provider initialization and functionality."""

    @pytest.mark.unit
    def test_system_provider_initialization_with_pyttsx3(self):
        """Test system provider initialization with pyttsx3 available."""
        config = ChirpyConfig(tts_rate=200, tts_volume=0.8)

        with patch("pyttsx3.init") as mock_init:
            mock_engine = Mock()
            mock_init.return_value = mock_engine

            provider = SystemTTSProvider(config)

            assert provider.config == config
            assert provider.engine == mock_engine
            assert provider.pyttsx3_available is True
            mock_init.assert_called_once()
            mock_engine.setProperty.assert_any_call("rate", 200)
            mock_engine.setProperty.assert_any_call("volume", 0.8)

    @pytest.mark.unit
    def test_system_provider_initialization_without_pyttsx3(self):
        """Test system provider initialization without pyttsx3."""
        config = ChirpyConfig()

        error_msg = "No module named 'pyttsx3'"
        with patch("pyttsx3.init", side_effect=ImportError(error_msg)):
            provider = SystemTTSProvider(config)

            assert provider.config == config
            assert provider.engine is None
            assert provider.pyttsx3_available is False

    @pytest.mark.unit
    def test_system_provider_is_available(self):
        """Test that system provider is always available."""
        config = ChirpyConfig()

        with patch("pyttsx3.init", side_effect=ImportError()):
            provider = SystemTTSProvider(config)

            assert provider.is_available() is True

    @pytest.mark.unit
    def test_system_provider_get_cost_estimate(self):
        """Test that system TTS is free."""
        config = ChirpyConfig()

        with patch("pyttsx3.init", side_effect=ImportError()):
            provider = SystemTTSProvider(config)

            assert provider.get_cost_estimate("any text") == 0.0

    @pytest.mark.unit
    def test_system_provider_speak_text_empty(self):
        """Test speak_text with empty text."""
        config = ChirpyConfig()

        with patch("pyttsx3.init") as mock_init:
            mock_init.return_value = Mock()

            provider = SystemTTSProvider(config)

            result = provider.speak_text("")

            assert result is True

    @pytest.mark.unit
    def test_system_provider_speak_text_with_pyttsx3(self):
        """Test speak_text using pyttsx3."""
        config = ChirpyConfig()

        with patch("pyttsx3.init") as mock_init:
            mock_engine = Mock()
            mock_init.return_value = mock_engine

            provider = SystemTTSProvider(config)

            result = provider.speak_text("test text")

            assert result is True
            mock_engine.say.assert_called_once_with("test text")
            mock_engine.runAndWait.assert_called_once()

    @pytest.mark.unit
    def test_system_provider_speak_text_with_say_command(self):
        """Test speak_text using 'say' command fallback."""
        config = ChirpyConfig(tts_rate=150)

        with (
            patch("pyttsx3.init", side_effect=ImportError()),
            patch("subprocess.run") as mock_run,
        ):
            provider = SystemTTSProvider(config)

            result = provider.speak_text("test text")

            assert result is True
            mock_run.assert_called_once_with(
                ["say", "-r", "150", "test text"],
                check=True,
                capture_output=True,
                timeout=30,
            )

    @pytest.mark.unit
    def test_system_provider_speak_text_pyttsx3_error(self):
        """Test speak_text with pyttsx3 error."""
        config = ChirpyConfig()

        with patch("pyttsx3.init") as mock_init:
            mock_engine = Mock()
            mock_engine.say.side_effect = Exception("TTS Error")
            mock_init.return_value = mock_engine

            provider = SystemTTSProvider(config)

            result = provider.speak_text("test text")

            assert result is False

    @pytest.mark.unit
    def test_system_provider_speak_text_say_command_error(self):
        """Test speak_text with 'say' command error."""
        config = ChirpyConfig()

        with (
            patch("pyttsx3.init", side_effect=ImportError()),
            patch("subprocess.run", side_effect=Exception("Command failed")),
        ):
            provider = SystemTTSProvider(config)

            result = provider.speak_text("test text")

            assert result is False


class TestEnhancedTTSService:
    """Test suite for Enhanced TTS service coordination and fallback logic."""

    @pytest.mark.unit
    def test_enhanced_service_initialization_basic_only(self):
        """Test enhanced service initialization with only basic TTS."""
        config = ChirpyConfig(tts_quality="basic")

        with (
            patch("tts_service.SystemTTSProvider") as mock_system_provider,
            patch("tts_service.OpenAITTSProvider") as mock_openai_provider,
        ):
            mock_system = Mock()
            mock_system_provider.return_value = mock_system

            mock_openai = Mock()
            mock_openai.is_available.return_value = False
            mock_openai_provider.return_value = mock_openai

            service = EnhancedTTSService(config)

            assert service.config == config
            assert service.current_quality == TTSQuality.BASIC
            assert service.current_provider == mock_system
            assert len(service.providers) == 1
            assert TTSQuality.BASIC in service.providers

    @pytest.mark.unit
    def test_enhanced_service_initialization_with_openai(self):
        """Test enhanced service initialization with OpenAI TTS available."""
        config = ChirpyConfig(tts_quality="standard")

        with (
            patch("tts_service.SystemTTSProvider") as mock_system_provider,
            patch("tts_service.OpenAITTSProvider") as mock_openai_provider,
        ):
            mock_system = Mock()
            mock_system_provider.return_value = mock_system

            mock_openai = Mock()
            mock_openai.is_available.return_value = True
            mock_openai_provider.return_value = mock_openai

            service = EnhancedTTSService(config)

            assert service.config == config
            assert service.current_quality == TTSQuality.STANDARD
            assert service.current_provider == mock_openai
            assert len(service.providers) == 3
            assert TTSQuality.BASIC in service.providers
            assert TTSQuality.STANDARD in service.providers
            assert TTSQuality.HD in service.providers

    @pytest.mark.unit
    def test_enhanced_service_initialization_hd_quality(self):
        """Test enhanced service initialization with HD quality."""
        config = ChirpyConfig(tts_quality="hd")

        with (
            patch("tts_service.SystemTTSProvider") as mock_system_provider,
            patch("tts_service.OpenAITTSProvider") as mock_openai_provider,
        ):
            mock_system = Mock()
            mock_system_provider.return_value = mock_system

            mock_openai = Mock()
            mock_openai.is_available.return_value = True
            mock_openai_provider.return_value = mock_openai

            service = EnhancedTTSService(config)

            assert service.current_quality == TTSQuality.HD
            assert service.current_provider == mock_openai

    @pytest.mark.unit
    def test_enhanced_service_get_best_available_provider_fallback(self):
        """Test fallback logic when requested quality is unavailable."""
        config = ChirpyConfig(tts_quality="hd")

        with (
            patch("tts_service.SystemTTSProvider") as mock_system_provider,
            patch("tts_service.OpenAITTSProvider") as mock_openai_provider,
        ):
            mock_system = Mock()
            mock_system_provider.return_value = mock_system

            mock_openai = Mock()
            mock_openai.is_available.return_value = False
            mock_openai_provider.return_value = mock_openai

            service = EnhancedTTSService(config)

            # Should fallback to BASIC since OpenAI is not available
            assert service.current_quality == TTSQuality.HD
            assert service.current_provider == mock_system

    @pytest.mark.unit
    def test_enhanced_service_speak_text_empty(self):
        """Test speak_text with empty text."""
        config = ChirpyConfig()

        with (
            patch("tts_service.SystemTTSProvider") as mock_system_provider,
            patch("tts_service.OpenAITTSProvider") as mock_openai_provider,
        ):
            mock_system = Mock()
            mock_system_provider.return_value = mock_system

            mock_openai = Mock()
            mock_openai.is_available.return_value = False
            mock_openai_provider.return_value = mock_openai

            service = EnhancedTTSService(config)

            result = service.speak_text("")

            assert result is True

    @pytest.mark.unit
    def test_enhanced_service_speak_text_success(self):
        """Test successful speech with current provider."""
        config = ChirpyConfig(tts_quality="standard")

        with (
            patch("tts_service.SystemTTSProvider") as mock_system_provider,
            patch("tts_service.OpenAITTSProvider") as mock_openai_provider,
        ):
            mock_system = Mock()
            mock_system_provider.return_value = mock_system

            mock_openai = Mock()
            mock_openai.is_available.return_value = True
            mock_openai.speak_text.return_value = True
            mock_openai.get_cost_estimate.return_value = 0.05
            mock_openai_provider.return_value = mock_openai

            service = EnhancedTTSService(config)

            result = service.speak_text("test text", "alloy")

            assert result is True
            mock_openai.speak_text.assert_called_once_with("test text", "alloy")

    @pytest.mark.unit
    def test_enhanced_service_speak_text_fallback_to_basic(self):
        """Test fallback to basic TTS when primary fails."""
        config = ChirpyConfig(tts_quality="standard")

        with (
            patch("tts_service.SystemTTSProvider") as mock_system_provider,
            patch("tts_service.OpenAITTSProvider") as mock_openai_provider,
        ):
            mock_system = Mock()
            mock_system.speak_text.return_value = True
            mock_system_provider.return_value = mock_system

            mock_openai = Mock()
            mock_openai.is_available.return_value = True
            mock_openai.speak_text.return_value = False  # Primary fails
            mock_openai.get_cost_estimate.return_value = 0.02
            mock_openai_provider.return_value = mock_openai

            service = EnhancedTTSService(config)

            result = service.speak_text("test text")

            assert result is True
            mock_openai.speak_text.assert_called_once_with("test text", None)
            mock_system.speak_text.assert_called_once_with("test text", None)

    @pytest.mark.unit
    def test_enhanced_service_speak_text_basic_quality_no_fallback(self):
        """Test that basic quality doesn't try fallback."""
        config = ChirpyConfig(tts_quality="basic")

        with (
            patch("tts_service.SystemTTSProvider") as mock_system_provider,
            patch("tts_service.OpenAITTSProvider") as mock_openai_provider,
        ):
            mock_system = Mock()
            mock_system.speak_text.return_value = False  # Basic fails
            mock_system_provider.return_value = mock_system

            mock_openai = Mock()
            mock_openai.is_available.return_value = False
            mock_openai_provider.return_value = mock_openai

            service = EnhancedTTSService(config)

            result = service.speak_text("test text")

            assert result is False
            mock_system.speak_text.assert_called_once_with("test text", None)

    @pytest.mark.unit
    def test_enhanced_service_set_quality_available(self):
        """Test changing to available quality."""
        config = ChirpyConfig(tts_quality="basic")

        with (
            patch("tts_service.SystemTTSProvider") as mock_system_provider,
            patch("tts_service.OpenAITTSProvider") as mock_openai_provider,
        ):
            mock_system = Mock()
            mock_system_provider.return_value = mock_system

            mock_openai = Mock()
            mock_openai.is_available.return_value = True
            mock_openai_provider.return_value = mock_openai

            service = EnhancedTTSService(config)

            result = service.set_quality(TTSQuality.STANDARD)

            assert result is True
            assert service.current_quality == TTSQuality.STANDARD
            assert service.current_provider == mock_openai

    @pytest.mark.unit
    def test_enhanced_service_set_quality_unavailable(self):
        """Test changing to unavailable quality."""
        config = ChirpyConfig(tts_quality="basic")

        with (
            patch("tts_service.SystemTTSProvider") as mock_system_provider,
            patch("tts_service.OpenAITTSProvider") as mock_openai_provider,
        ):
            mock_system = Mock()
            mock_system_provider.return_value = mock_system

            mock_openai = Mock()
            mock_openai.is_available.return_value = False
            mock_openai_provider.return_value = mock_openai

            service = EnhancedTTSService(config)

            result = service.set_quality(TTSQuality.STANDARD)

            assert result is False
            assert service.current_quality == TTSQuality.BASIC
            assert service.current_provider == mock_system

    @pytest.mark.unit
    def test_enhanced_service_get_available_qualities(self):
        """Test getting list of available qualities."""
        config = ChirpyConfig()

        with (
            patch("tts_service.SystemTTSProvider") as mock_system_provider,
            patch("tts_service.OpenAITTSProvider") as mock_openai_provider,
        ):
            mock_system = Mock()
            mock_system_provider.return_value = mock_system

            mock_openai = Mock()
            mock_openai.is_available.return_value = True
            mock_openai_provider.return_value = mock_openai

            service = EnhancedTTSService(config)

            qualities = service.get_available_qualities()

            assert TTSQuality.BASIC in qualities
            assert TTSQuality.STANDARD in qualities
            assert TTSQuality.HD in qualities
            assert len(qualities) == 3

    @pytest.mark.unit
    def test_enhanced_service_get_cost_estimate(self):
        """Test getting cost estimate from current provider."""
        config = ChirpyConfig(tts_quality="standard")

        with (
            patch("tts_service.SystemTTSProvider") as mock_system_provider,
            patch("tts_service.OpenAITTSProvider") as mock_openai_provider,
        ):
            mock_system = Mock()
            mock_system_provider.return_value = mock_system

            mock_openai = Mock()
            mock_openai.is_available.return_value = True
            mock_openai.get_cost_estimate.return_value = 0.025
            mock_openai_provider.return_value = mock_openai

            service = EnhancedTTSService(config)

            cost = service.get_cost_estimate("test text")

            assert cost == 0.025
            mock_openai.get_cost_estimate.assert_called_once_with("test text")

    @pytest.mark.unit
    def test_enhanced_service_is_available(self):
        """Test service availability check."""
        config = ChirpyConfig()

        with (
            patch("tts_service.SystemTTSProvider") as mock_system_provider,
            patch("tts_service.OpenAITTSProvider") as mock_openai_provider,
        ):
            mock_system = Mock()
            mock_system_provider.return_value = mock_system

            mock_openai = Mock()
            mock_openai.is_available.return_value = False
            mock_openai_provider.return_value = mock_openai

            service = EnhancedTTSService(config)

            assert service.is_available() is True

    @pytest.mark.unit
    def test_enhanced_service_cost_logging_threshold(self):
        """Test that cost logging only happens for significant costs."""
        config = ChirpyConfig(tts_quality="standard")

        with (
            patch("tts_service.SystemTTSProvider") as mock_system_provider,
            patch("tts_service.OpenAITTSProvider") as mock_openai_provider,
        ):
            mock_system = Mock()
            mock_system_provider.return_value = mock_system

            mock_openai = Mock()
            mock_openai.is_available.return_value = True
            mock_openai.speak_text.return_value = True
            mock_openai.get_cost_estimate.return_value = 0.005  # Below threshold
            mock_openai_provider.return_value = mock_openai

            service = EnhancedTTSService(config)

            with patch.object(service.logger, "info") as mock_log:
                service.speak_text("short text")

                # Should not log cost since it's below $0.01 threshold
                call_list = mock_log.call_args_list
                cost_logged = any("Estimated cost" in str(call) for call in call_list)
                assert not cost_logged

    @pytest.mark.unit
    def test_enhanced_service_runtime_error_no_providers(self):
        """Test RuntimeError when no providers are available."""
        config = ChirpyConfig(tts_quality="hd")

        # This test scenario is unlikely in real usage since SystemTTSProvider
        # should always be available. We'll test by creating a service with
        # empty providers dictionary to simulate the error condition.
        service = EnhancedTTSService.__new__(EnhancedTTSService)
        service.config = config
        service.logger = Mock()
        service.providers = {}  # No providers available
        service.current_quality = TTSQuality.HD

        with pytest.raises(RuntimeError, match="No TTS providers available"):
            service._get_best_available_provider()
