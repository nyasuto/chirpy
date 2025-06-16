"""
Unit tests for ChirpyReader main application class.
"""

from unittest.mock import MagicMock, patch

import pytest

from chirpy import ChirpyReader


class TestChirpyReader:
    """Test ChirpyReader main application functionality."""

    @pytest.fixture
    def mock_chirpy_reader(self, test_config, db_manager):
        """Create a ChirpyReader with mocked components."""
        with patch("chirpy.ChirpyReader._initialize_tts"):
            reader = ChirpyReader(test_config)
            reader.db = db_manager
            return reader

    def test_chirpy_reader_initialization(self, test_config):
        """Test ChirpyReader initialization."""
        with patch("chirpy.ChirpyReader._initialize_tts"):
            reader = ChirpyReader(test_config)

            assert reader.config == test_config
            assert reader.tts_engine is None  # Mocked
            assert reader.db is not None
            assert reader.content_fetcher is not None

    def test_tts_initialization_pyttsx3(self, test_config):
        """Test TTS initialization with pyttsx3."""
        test_config.tts_engine = "pyttsx3"

        with patch("pyttsx3.init") as mock_init:
            mock_engine = MagicMock()
            mock_init.return_value = mock_engine

            reader = ChirpyReader(test_config)

            # Should have initialized pyttsx3
            mock_init.assert_called_once()
            assert reader.tts_engine == mock_engine

            # Should have set properties
            mock_engine.setProperty.assert_any_call("rate", test_config.tts_rate)
            mock_engine.setProperty.assert_any_call("volume", test_config.tts_volume)

    def test_tts_initialization_fallback(self, test_config):
        """Test TTS initialization fallback when pyttsx3 fails."""
        test_config.tts_engine = "pyttsx3"

        with patch("pyttsx3.init") as mock_init:
            mock_init.side_effect = Exception("TTS init failed")

            reader = ChirpyReader(test_config)

            # Should handle failure gracefully
            assert reader.tts_engine is None

    def test_speak_text_with_pyttsx3(self, mock_chirpy_reader):
        """Test speaking text with pyttsx3 engine."""
        mock_engine = MagicMock()
        mock_chirpy_reader.tts_engine = mock_engine
        mock_chirpy_reader.config.speech_enabled = True

        text = "Test speech content"
        mock_chirpy_reader.speak_text(text)

        mock_engine.say.assert_called_once_with(text)
        mock_engine.runAndWait.assert_called_once()

    def test_speak_text_fallback_to_say(self, mock_chirpy_reader):
        """Test speaking text fallback to say command."""
        mock_chirpy_reader.tts_engine = None
        mock_chirpy_reader.config.speech_enabled = True

        with patch("subprocess.run") as mock_run:
            text = "Test speech content"
            mock_chirpy_reader.speak_text(text)

            mock_run.assert_called_once_with(
                ["say", text], check=True, capture_output=True
            )

    def test_speak_text_disabled(self, mock_chirpy_reader):
        """Test speaking when speech is disabled."""
        mock_chirpy_reader.config.speech_enabled = False

        with patch("subprocess.run") as mock_run:
            mock_chirpy_reader.speak_text("Test content")

            # Should not call any speech commands
            mock_run.assert_not_called()

    def test_speak_text_empty_content(self, mock_chirpy_reader):
        """Test speaking empty text."""
        mock_chirpy_reader.config.speech_enabled = True

        with patch("subprocess.run") as mock_run:
            mock_chirpy_reader.speak_text("")
            mock_chirpy_reader.speak_text("   ")

            # Should not call speech for empty content
            mock_run.assert_not_called()

    def test_speak_text_pyttsx3_error_fallback(self, mock_chirpy_reader):
        """Test fallback when pyttsx3 fails during speech."""
        mock_engine = MagicMock()
        mock_engine.say.side_effect = Exception("TTS error")
        mock_chirpy_reader.tts_engine = mock_engine
        mock_chirpy_reader.config.speech_enabled = True

        with patch("subprocess.run") as mock_run:
            text = "Test speech content"
            mock_chirpy_reader.speak_text(text)

            # Should fallback to say command
            mock_run.assert_called_once_with(
                ["say", text], check=True, capture_output=True
            )

    def test_format_article_content_basic(self, mock_chirpy_reader, sample_articles):
        """Test basic article content formatting."""
        article = sample_articles[0]

        content = mock_chirpy_reader.format_article_content(article)

        assert "Article title:" in content
        assert article["title"] in content
        assert "Content:" in content
        assert article["summary"] in content

    def test_format_article_content_translated(self, mock_chirpy_reader):
        """Test formatting translated article content."""
        article = {
            "title": "English Article",
            "summary": "Japanese translation",
            "detected_language": "en",
            "is_translated": True,
        }

        content = mock_chirpy_reader.format_article_content(article)

        assert "English Article (英語記事 → 日本語翻訳済み)" in content
        assert "Japanese translation" in content

    def test_format_article_content_cleanup(self, mock_chirpy_reader):
        """Test article content text cleanup."""
        article = {
            "title": "Test Article",
            "summary": "Text with\n\nmultiple\r\nlines   and   spaces",
            "detected_language": "unknown",
            "is_translated": False,
        }

        content = mock_chirpy_reader.format_article_content(article)

        # Should normalize whitespace
        assert "multiple lines and spaces" in content
        assert "\n" not in content
        assert "\r" not in content

    def test_format_article_content_length_limit(self, mock_chirpy_reader):
        """Test article content length limiting."""
        long_summary = "A" * 1000  # Long summary
        mock_chirpy_reader.config.max_summary_length = 100

        article = {
            "title": "Test Article",
            "summary": long_summary,
            "detected_language": "unknown",
            "is_translated": False,
        }

        content = mock_chirpy_reader.format_article_content(article)

        # Should be truncated with ellipsis
        assert len(content) < len(long_summary) + 50  # Account for title and formatting
        assert "..." in content

    def test_format_article_content_missing_fields(self, mock_chirpy_reader):
        """Test formatting article with missing fields."""
        article = {}  # Empty article

        content = mock_chirpy_reader.format_article_content(article)

        assert "No title" in content
        assert "No summary available" in content

    def test_process_article_for_reading_no_translation_needed(
        self, mock_chirpy_reader
    ):
        """Test processing article that doesn't need translation."""
        article = {
            "id": 1,
            "title": "Japanese Article",
            "summary": "これは日本語です",
            "detected_language": "ja",
            "is_translated": False,
        }

        result = mock_chirpy_reader.process_article_for_reading(article)

        # Should return article unchanged
        assert result == article

    def test_process_article_for_reading_unknown_language(
        self, mock_chirpy_reader, mock_openai_client
    ):
        """Test processing article with unknown language."""
        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client

            with patch("content_fetcher.detect") as mock_detect:
                mock_detect.return_value = "en"

                article = {
                    "id": 1,
                    "title": "Unknown Article",
                    "summary": "This is English content",
                    "detected_language": "unknown",
                    "is_translated": False,
                }

                result = mock_chirpy_reader.process_article_for_reading(article)

                # Should have been processed and translated
                assert result["detected_language"] == "en"
                assert result["is_translated"] is True
                assert result["summary"] == "Mocked Japanese translation"

    def test_process_article_for_reading_no_openai(self, mock_chirpy_reader):
        """Test processing article when OpenAI is not available."""
        mock_chirpy_reader.content_fetcher.openai_client = None

        article = {
            "id": 1,
            "title": "Unknown Article",
            "summary": "Some content",
            "detected_language": "unknown",
            "is_translated": False,
        }

        result = mock_chirpy_reader.process_article_for_reading(article)

        # Should return article unchanged when OpenAI not available
        assert result == article

    def test_process_article_for_reading_translation_disabled(self, mock_chirpy_reader):
        """Test processing article when translation is disabled."""
        mock_chirpy_reader.config.auto_translate = False

        article = {
            "id": 1,
            "title": "Unknown Article",
            "summary": "Some content",
            "detected_language": "unknown",
            "is_translated": False,
        }

        result = mock_chirpy_reader.process_article_for_reading(article)

        # Should return article unchanged when translation disabled
        assert result == article

    def test_process_article_for_reading_empty_summary(self, mock_chirpy_reader):
        """Test processing article with empty summary."""
        article = {
            "id": 1,
            "title": "Empty Article",
            "summary": "",
            "detected_language": "unknown",
            "is_translated": False,
        }

        result = mock_chirpy_reader.process_article_for_reading(article)

        # Should return article unchanged for empty summary
        assert result == article

    def test_process_article_for_reading_invalid_id(self, mock_chirpy_reader):
        """Test processing article with invalid ID."""
        article = {
            "id": "invalid",  # Non-integer ID
            "title": "Test Article",
            "summary": "Some content",
            "detected_language": "unknown",
        }

        result = mock_chirpy_reader.process_article_for_reading(article)

        # Should return article unchanged for invalid ID
        assert result == article

    def test_process_article_for_reading_exception_handling(
        self, mock_chirpy_reader, mock_openai_client
    ):
        """Test exception handling in article processing."""
        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client

            with patch.object(
                mock_chirpy_reader.content_fetcher, "process_article_with_translation"
            ) as mock_process:
                mock_process.side_effect = Exception("Processing failed")

                article = {
                    "id": 1,
                    "title": "Test Article",
                    "summary": "Some content",
                    "detected_language": "unknown",
                    "is_translated": False,
                }

                result = mock_chirpy_reader.process_article_for_reading(article)

                # Should return original article when processing fails
                assert result == article

    def test_run_method(self, mock_chirpy_reader):
        """Test the main run method."""
        with patch.object(mock_chirpy_reader, "read_articles") as mock_read:
            mock_chirpy_reader.run()
            mock_read.assert_called_once()

    def test_run_method_keyboard_interrupt(self, mock_chirpy_reader):
        """Test run method with keyboard interrupt."""
        with patch.object(mock_chirpy_reader, "read_articles") as mock_read:
            mock_read.side_effect = KeyboardInterrupt()

            with patch.object(mock_chirpy_reader, "speak_text") as mock_speak:
                mock_chirpy_reader.run()

                # Should handle interrupt gracefully
                calls = [call.args[0] for call in mock_speak.call_args_list]
                goodbye_call = next((call for call in calls if "Goodbye" in call), None)
                assert goodbye_call is not None
