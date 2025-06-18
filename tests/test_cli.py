"""Tests for CLI argument parsing and validation."""

import argparse
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cli import (
    apply_args_to_config,
    create_parser,
    handle_special_modes,
    parse_args,
    show_config,
)
from config import ChirpyConfig


class TestCLIArgumentParsing:
    """Test suite for CLI argument parsing."""

    @pytest.mark.unit
    def test_create_parser_returns_argparse_parser(self):
        """Test that create_parser returns a valid ArgumentParser."""
        parser = create_parser()

        assert isinstance(parser, argparse.ArgumentParser)
        assert parser.prog == "chirpy"
        assert "Chirpy RSS Reader" in parser.description

    @pytest.mark.unit
    def test_parse_args_no_arguments(self):
        """Test parsing with no command-line arguments."""
        args = parse_args([])

        assert args.database is None
        assert args.max_articles is None
        assert args.no_speech is False
        assert args.process_summaries is False
        assert args.stats is False
        assert args.interactive is False
        assert args.verbose is False
        assert args.quiet is False

    @pytest.mark.unit
    def test_parse_args_database_positional(self):
        """Test parsing database positional argument."""
        args = parse_args(["/path/to/database.db"])

        assert args.database == "/path/to/database.db"

    @pytest.mark.unit
    def test_parse_args_process_summaries_flag(self):
        """Test parsing --process-summaries flag."""
        args = parse_args(["--process-summaries"])

        assert args.process_summaries is True
        assert args.stats is False  # Mutually exclusive

    @pytest.mark.unit
    def test_parse_args_stats_flag(self):
        """Test parsing --stats flag."""
        args = parse_args(["--stats"])

        assert args.stats is True
        assert args.process_summaries is False  # Mutually exclusive

    @pytest.mark.unit
    def test_parse_args_mutual_exclusion_process_summaries_stats(self):
        """Test that --process-summaries and --stats are mutually exclusive."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--process-summaries", "--stats"])

    @pytest.mark.unit
    def test_parse_args_max_articles(self):
        """Test parsing --max-articles argument."""
        args = parse_args(["--max-articles", "5"])

        assert args.max_articles == 5

    @pytest.mark.unit
    def test_parse_args_max_articles_invalid(self):
        """Test parsing invalid --max-articles argument."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--max-articles", "invalid"])

    @pytest.mark.unit
    def test_parse_args_no_speech_flag(self):
        """Test parsing --no-speech flag."""
        args = parse_args(["--no-speech"])

        assert args.no_speech is True

    @pytest.mark.unit
    def test_parse_args_tts_options(self):
        """Test parsing TTS-related arguments."""
        args = parse_args(
            ["--tts-rate", "200", "--tts-volume", "0.8", "--tts-engine", "pyttsx3"]
        )

        assert args.tts_rate == 200
        assert args.tts_volume == 0.8
        assert args.tts_engine == "pyttsx3"

    @pytest.mark.unit
    def test_parse_args_tts_engine_invalid(self):
        """Test parsing invalid --tts-engine choice."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--tts-engine", "invalid"])

    @pytest.mark.unit
    def test_parse_args_interactive_flags(self):
        """Test parsing interactive mode flags."""
        args = parse_args(["--interactive", "--select-articles"])

        assert args.interactive is True
        assert args.select_articles is True

    @pytest.mark.unit
    def test_parse_args_interactive_short_flag(self):
        """Test parsing interactive mode short flag."""
        args = parse_args(["-i"])

        assert args.interactive is True

    @pytest.mark.unit
    def test_parse_args_content_fetching_options(self):
        """Test parsing content fetching arguments."""
        args = parse_args(["--fetch-timeout", "30", "--rate-limit", "2"])

        assert args.fetch_timeout == 30
        assert args.rate_limit_delay == 2

    @pytest.mark.unit
    def test_parse_args_logging_options(self):
        """Test parsing logging-related arguments."""
        args = parse_args(["--log-level", "DEBUG", "--log-file", "/path/to/log.txt"])

        assert args.log_level == "DEBUG"
        assert args.log_file == "/path/to/log.txt"

    @pytest.mark.unit
    def test_parse_args_logging_level_choices(self):
        """Test that log level accepts only valid choices."""
        parser = create_parser()

        # Valid choices
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            args = parser.parse_args(["--log-level", level])
            assert args.log_level == level

        # Invalid choice
        with pytest.raises(SystemExit):
            parser.parse_args(["--log-level", "INVALID"])

    @pytest.mark.unit
    def test_parse_args_verbose_flag(self):
        """Test parsing --verbose flag."""
        args = parse_args(["--verbose"])

        assert args.verbose is True

    @pytest.mark.unit
    def test_parse_args_verbose_short_flag(self):
        """Test parsing -v verbose flag."""
        args = parse_args(["-v"])

        assert args.verbose is True

    @pytest.mark.unit
    def test_parse_args_quiet_flag(self):
        """Test parsing --quiet flag."""
        args = parse_args(["--quiet"])

        assert args.quiet is True

    @pytest.mark.unit
    def test_parse_args_quiet_short_flag(self):
        """Test parsing -q quiet flag."""
        args = parse_args(["-q"])

        assert args.quiet is True

    @pytest.mark.unit
    def test_parse_args_config_file(self):
        """Test parsing --config-file argument."""
        args = parse_args(["--config-file", "custom.env"])

        assert args.config_file == "custom.env"

    @pytest.mark.unit
    def test_parse_args_show_config_flag(self):
        """Test parsing --show-config flag."""
        args = parse_args(["--show-config"])

        assert args.show_config is True

    @pytest.mark.unit
    def test_parse_args_translation_options(self):
        """Test parsing translation-related arguments."""
        args = parse_args(
            ["--no-translate", "--target-language", "en", "--translate-articles"]
        )

        assert args.no_translate is True
        assert args.target_language == "en"
        assert args.translate_articles is True

    @pytest.mark.unit
    def test_parse_args_behavior_options(self):
        """Test parsing application behavior arguments."""
        args = parse_args(["--no-mark-read", "--no-pause"])

        assert args.no_mark_read is True
        assert args.no_pause is True

    @pytest.mark.unit
    def test_parse_args_version_flag(self):
        """Test that --version flag causes SystemExit."""
        parser = create_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])

        assert exc_info.value.code == 0  # Successful exit

    @pytest.mark.unit
    def test_parse_args_help_flag(self):
        """Test that --help flag causes SystemExit."""
        parser = create_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])

        assert exc_info.value.code == 0  # Successful exit

    @pytest.mark.unit
    def test_parse_args_complex_combination(self):
        """Test parsing complex combination of arguments."""
        args = parse_args(
            [
                "/path/to/db.sqlite",
                "--process-summaries",
                "--max-articles",
                "10",
                "--tts-rate",
                "150",
                "--tts-volume",
                "0.9",
                "--interactive",
                "--log-level",
                "INFO",
                "--config-file",
                "config.env",
                "--target-language",
                "ja",
            ]
        )

        assert args.database == "/path/to/db.sqlite"
        assert args.process_summaries is True
        assert args.max_articles == 10
        assert args.tts_rate == 150
        assert args.tts_volume == 0.9
        assert args.interactive is True
        assert args.log_level == "INFO"
        assert args.config_file == "config.env"
        assert args.target_language == "ja"


class TestApplyArgsToConfig:
    """Test suite for applying CLI arguments to configuration."""

    @pytest.mark.unit
    def test_apply_args_to_config_no_changes(self):
        """Test applying arguments with no changes."""
        config = ChirpyConfig()
        args = argparse.Namespace(
            config_file=None,
            database=None,
            max_articles=None,
            no_speech=False,
            tts_rate=None,
            tts_volume=None,
            tts_engine=None,
            fetch_timeout=None,
            rate_limit_delay=None,
            verbose=False,
            quiet=False,
            log_level=None,
            log_file=None,
            no_translate=False,
            target_language=None,
            no_mark_read=False,
            no_pause=False,
            interactive=False,
            select_articles=False,
        )

        result_config = apply_args_to_config(args, config)

        # Should return same values as original config
        assert result_config.database_path == config.database_path
        assert result_config.max_articles == config.max_articles
        assert result_config.speech_enabled == config.speech_enabled

    @pytest.mark.unit
    def test_apply_args_to_config_database_path(self):
        """Test applying database path argument."""
        config = ChirpyConfig()
        args = argparse.Namespace(database="/custom/path.db")

        # Add all other required attributes
        for attr in [
            "config_file",
            "max_articles",
            "no_speech",
            "tts_rate",
            "tts_volume",
            "tts_engine",
            "fetch_timeout",
            "rate_limit_delay",
            "verbose",
            "quiet",
            "log_level",
            "log_file",
            "no_translate",
            "target_language",
            "no_mark_read",
            "no_pause",
            "interactive",
            "select_articles",
        ]:
            setattr(args, attr, None if attr != "interactive" else False)
        args.no_speech = False
        args.verbose = False
        args.quiet = False
        args.no_translate = False
        args.no_mark_read = False
        args.no_pause = False
        args.select_articles = False

        result_config = apply_args_to_config(args, config)

        assert result_config.database_path == "/custom/path.db"

    @pytest.mark.unit
    def test_apply_args_to_config_max_articles(self):
        """Test applying max_articles argument."""
        config = ChirpyConfig()
        args = self._create_basic_args(max_articles=5)

        result_config = apply_args_to_config(args, config)

        assert result_config.max_articles == 5

    @pytest.mark.unit
    def test_apply_args_to_config_no_speech(self):
        """Test applying --no-speech flag."""
        config = ChirpyConfig()
        args = self._create_basic_args(no_speech=True)

        result_config = apply_args_to_config(args, config)

        assert result_config.speech_enabled is False

    @pytest.mark.unit
    def test_apply_args_to_config_tts_settings(self):
        """Test applying TTS settings."""
        config = ChirpyConfig()
        args = self._create_basic_args(tts_rate=200, tts_volume=0.8, tts_engine="say")

        result_config = apply_args_to_config(args, config)

        assert result_config.tts_rate == 200
        assert result_config.tts_volume == 0.8
        assert result_config.tts_engine == "say"

    @pytest.mark.unit
    def test_apply_args_to_config_content_fetching(self):
        """Test applying content fetching settings."""
        config = ChirpyConfig()
        args = self._create_basic_args(fetch_timeout=60, rate_limit_delay=3)

        result_config = apply_args_to_config(args, config)

        assert result_config.fetch_timeout == 60
        assert result_config.rate_limit_delay == 3

    @pytest.mark.unit
    def test_apply_args_to_config_verbose_flag(self):
        """Test applying --verbose flag sets DEBUG log level."""
        config = ChirpyConfig()
        args = self._create_basic_args(verbose=True)

        result_config = apply_args_to_config(args, config)

        assert result_config.log_level == "DEBUG"

    @pytest.mark.unit
    def test_apply_args_to_config_quiet_flag(self):
        """Test applying --quiet flag sets ERROR log level."""
        config = ChirpyConfig()
        args = self._create_basic_args(quiet=True)

        result_config = apply_args_to_config(args, config)

        assert result_config.log_level == "ERROR"

    @pytest.mark.unit
    def test_apply_args_to_config_log_level_explicit(self):
        """Test applying explicit log level."""
        config = ChirpyConfig()
        args = self._create_basic_args(log_level="WARNING")

        result_config = apply_args_to_config(args, config)

        assert result_config.log_level == "WARNING"

    @pytest.mark.unit
    def test_apply_args_to_config_log_level_precedence(self):
        """Test that verbose/quiet takes precedence over explicit log level."""
        config = ChirpyConfig()

        # verbose should override explicit log level
        args = self._create_basic_args(verbose=True, log_level="WARNING")
        result_config = apply_args_to_config(args, config)
        assert result_config.log_level == "DEBUG"

        # quiet should override explicit log level
        args = self._create_basic_args(quiet=True, log_level="INFO")
        result_config = apply_args_to_config(args, config)
        assert result_config.log_level == "ERROR"

    @pytest.mark.unit
    def test_apply_args_to_config_log_file(self):
        """Test applying log file setting."""
        config = ChirpyConfig()
        args = self._create_basic_args(log_file="/path/to/log.txt")

        result_config = apply_args_to_config(args, config)

        assert result_config.log_file == "/path/to/log.txt"

    @pytest.mark.unit
    def test_apply_args_to_config_translation_settings(self):
        """Test applying translation settings."""
        config = ChirpyConfig()
        args = self._create_basic_args(no_translate=True, target_language="en")

        result_config = apply_args_to_config(args, config)

        assert result_config.auto_translate is False
        assert result_config.target_language == "en"

    @pytest.mark.unit
    def test_apply_args_to_config_behavior_settings(self):
        """Test applying application behavior settings."""
        config = ChirpyConfig()
        args = self._create_basic_args(no_mark_read=True, no_pause=True)

        result_config = apply_args_to_config(args, config)

        assert result_config.auto_mark_read is False
        assert result_config.pause_between_articles is False

    @pytest.mark.unit
    def test_apply_args_to_config_interactive_mode(self):
        """Test applying interactive mode setting."""
        config = ChirpyConfig()
        args = self._create_basic_args(interactive=True)

        result_config = apply_args_to_config(args, config)

        assert result_config.interactive_mode is True

    @pytest.mark.unit
    def test_apply_args_to_config_select_articles(self):
        """Test applying select_articles setting."""
        config = ChirpyConfig()
        args = self._create_basic_args(select_articles=True)

        result_config = apply_args_to_config(args, config)

        # This should be stored in the config via update_from_dict
        config_dict = result_config.to_dict()
        assert config_dict.get("select_articles") is True

    @pytest.mark.unit
    def test_apply_args_to_config_with_config_file(self):
        """Test applying configuration file argument."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("LOG_LEVEL=DEBUG\nMAX_ARTICLES=10\n")
            config_file_path = f.name

        try:
            config = ChirpyConfig()
            args = self._create_basic_args(config_file=config_file_path)

            with (
                patch("dotenv.load_dotenv") as mock_load_dotenv,
                patch("config.ChirpyConfig.from_env") as mock_from_env,
            ):
                mock_from_env.return_value = ChirpyConfig(
                    log_level="DEBUG", max_articles=10
                )

                result_config = apply_args_to_config(args, config)

                mock_load_dotenv.assert_called_once()
                mock_from_env.assert_called_once()
                assert result_config.log_level == "DEBUG"
                assert result_config.max_articles == 10
        finally:
            Path(config_file_path).unlink()

    @pytest.mark.unit
    def test_apply_args_to_config_missing_config_file(self):
        """Test applying missing configuration file prints warning."""
        config = ChirpyConfig()
        args = self._create_basic_args(config_file="/nonexistent/config.env")

        with patch("builtins.print") as mock_print:
            apply_args_to_config(args, config)

            mock_print.assert_called_once()
            assert "Warning: Configuration file not found" in mock_print.call_args[0][0]

    def _create_basic_args(self, **kwargs) -> argparse.Namespace:
        """Helper to create args namespace with defaults."""
        defaults = {
            "config_file": None,
            "database": None,
            "max_articles": None,
            "no_speech": False,
            "tts_rate": None,
            "tts_volume": None,
            "tts_engine": None,
            "fetch_timeout": None,
            "rate_limit_delay": None,
            "verbose": False,
            "quiet": False,
            "log_level": None,
            "log_file": None,
            "no_translate": False,
            "target_language": None,
            "no_mark_read": False,
            "no_pause": False,
            "interactive": False,
            "select_articles": False,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)


class TestShowConfig:
    """Test suite for show_config function."""

    @pytest.mark.unit
    def test_show_config_displays_configuration(self):
        """Test that show_config displays configuration sections."""
        config = ChirpyConfig(
            database_path="/test/db.sqlite",
            max_articles=5,
            openai_api_key="sk-test123456789012345",
            log_level="DEBUG",
        )

        with patch("builtins.print") as mock_print:
            show_config(config)

            # Verify that print was called multiple times
            assert mock_print.call_count > 5

            # Check that configuration sections are displayed
            print_args = [call[0][0] for call in mock_print.call_args_list if call[0]]
            output_text = " ".join(print_args)

            assert "Chirpy Configuration" in output_text
            assert "Database" in output_text
            assert "Article Processing" in output_text
            assert "Text-to-Speech" in output_text
            assert "database_path: /test/db.sqlite" in output_text
            assert "max_articles: 5" in output_text
            assert "log_level: DEBUG" in output_text

    @pytest.mark.unit
    def test_show_config_masks_api_key(self):
        """Test that show_config masks OpenAI API key for security."""
        config = ChirpyConfig(openai_api_key="sk-test123456789012345")

        with patch("builtins.print") as mock_print:
            show_config(config)

            print_args = [call[0][0] for call in mock_print.call_args_list if call[0]]
            output_text = " ".join(print_args)

            # API key should be completely masked (security improvement)
            assert "***configured***" in output_text
            assert "sk-test123456789012345" not in output_text
            assert "sk-test1" not in output_text  # No partial exposure

    @pytest.mark.unit
    def test_show_config_short_api_key(self):
        """Test that show_config handles short API keys."""
        config = ChirpyConfig(openai_api_key="short")

        with patch("builtins.print") as mock_print:
            show_config(config)

            print_args = [call[0][0] for call in mock_print.call_args_list if call[0]]
            output_text = " ".join(print_args)

            # Short API key should be completely masked
            assert "***" in output_text
            assert "short" not in output_text


class TestHandleSpecialModes:
    """Test suite for handle_special_modes function."""

    @pytest.mark.unit
    def test_handle_special_modes_show_config(self):
        """Test handling --show-config mode."""
        config = ChirpyConfig()
        args = argparse.Namespace(
            show_config=True, stats=False, translate_articles=False
        )

        with patch("cli.show_config") as mock_show_config:
            result = handle_special_modes(args, config)

            assert result is True
            mock_show_config.assert_called_once_with(config)

    @pytest.mark.unit
    def test_handle_special_modes_stats(self):
        """Test handling --stats mode."""
        config = ChirpyConfig()
        args = argparse.Namespace(
            show_config=False, stats=True, translate_articles=False
        )

        mock_stats = {
            "total_articles": 100,
            "read_articles": 30,
            "unread_articles": 70,
            "empty_summaries": 10,
        }

        with (
            patch("database_service.DatabaseManager") as mock_db_class,
            patch("builtins.print") as mock_print,
        ):
            mock_db = Mock()
            mock_db.get_database_stats.return_value = mock_stats
            mock_db_class.return_value = mock_db

            result = handle_special_modes(args, config)

            assert result is True
            mock_db_class.assert_called_once_with(config.database_path)
            mock_db.get_database_stats.assert_called_once()

            # Verify stats were printed
            print_calls = [call[0][0] for call in mock_print.call_args_list if call[0]]
            output_text = " ".join(print_calls)
            assert "Chirpy Database Statistics" in output_text
            assert "Total articles: 100" in output_text
            assert "Read articles: 30" in output_text

    @pytest.mark.unit
    def test_handle_special_modes_translate_articles_success(self):
        """Test handling --translate-articles mode with successful processing."""
        config = ChirpyConfig()
        args = argparse.Namespace(
            show_config=False, stats=False, translate_articles=True
        )

        mock_articles = [
            {"id": 1, "title": "Article 1", "summary": "English content"},
            {"id": 2, "title": "Article 2", "summary": "More English content"},
        ]

        with (
            patch("database_service.DatabaseManager") as mock_db_class,
            patch("content_fetcher.ContentFetcher") as mock_fetcher_class,
        ):
            # Setup mocks
            mock_db = Mock()
            mock_db.get_untranslated_articles.return_value = mock_articles
            mock_db_class.return_value = mock_db

            mock_fetcher = Mock()
            mock_fetcher.is_available.return_value = True
            mock_fetcher.process_article_with_translation.return_value = (
                "Translated summary",
                "en",
                True,
            )
            mock_fetcher_class.return_value = mock_fetcher

            result = handle_special_modes(args, config)

            assert result is True
            mock_fetcher.is_available.assert_called_once()
            mock_db.get_untranslated_articles.assert_called_once()
            assert mock_fetcher.process_article_with_translation.call_count == 2
            assert mock_db.update_article_summary.call_count == 2
            assert mock_db.update_article_language_info.call_count == 2

    @pytest.mark.unit
    def test_handle_special_modes_translate_articles_not_available(self):
        """Test handling --translate-articles when OpenAI API not available."""
        config = ChirpyConfig()
        args = argparse.Namespace(
            show_config=False, stats=False, translate_articles=True
        )

        with (
            patch("database_service.DatabaseManager") as mock_db_class,
            patch("content_fetcher.ContentFetcher") as mock_fetcher_class,
        ):
            mock_db = Mock()
            mock_db_class.return_value = mock_db

            mock_fetcher = Mock()
            mock_fetcher.is_available.return_value = False
            mock_fetcher_class.return_value = mock_fetcher

            result = handle_special_modes(args, config)

            assert result is True
            mock_fetcher.is_available.assert_called_once()
            mock_db.get_untranslated_articles.assert_not_called()

    @pytest.mark.unit
    def test_handle_special_modes_translate_articles_no_articles(self):
        """Test handling --translate-articles when no articles need translation."""
        config = ChirpyConfig()
        args = argparse.Namespace(
            show_config=False, stats=False, translate_articles=True
        )

        with (
            patch("database_service.DatabaseManager") as mock_db_class,
            patch("content_fetcher.ContentFetcher") as mock_fetcher_class,
        ):
            mock_db = Mock()
            mock_db.get_untranslated_articles.return_value = []
            mock_db_class.return_value = mock_db

            mock_fetcher = Mock()
            mock_fetcher.is_available.return_value = True
            mock_fetcher_class.return_value = mock_fetcher

            result = handle_special_modes(args, config)

            assert result is True
            mock_db.get_untranslated_articles.assert_called_once()
            mock_fetcher.process_article_with_translation.assert_not_called()

    @pytest.mark.unit
    def test_handle_special_modes_no_special_mode(self):
        """Test handling when no special mode is activated."""
        config = ChirpyConfig()
        args = argparse.Namespace(
            show_config=False,
            stats=False,
            translate_articles=False,
            cache_stats=False,
            clear_cache=False,
            cleanup_cache=False,
        )

        result = handle_special_modes(args, config)

        assert result is False

    @pytest.mark.unit
    def test_handle_special_modes_translate_articles_processing_error(self):
        """Test handling --translate-articles with processing errors."""
        config = ChirpyConfig()
        args = argparse.Namespace(
            show_config=False, stats=False, translate_articles=True
        )

        mock_articles = [{"id": 1, "title": "Article 1", "summary": "Content"}]

        with (
            patch("database_service.DatabaseManager") as mock_db_class,
            patch("content_fetcher.ContentFetcher") as mock_fetcher_class,
            patch("builtins.print") as mock_print,
        ):
            mock_db = Mock()
            mock_db.get_untranslated_articles.return_value = mock_articles
            mock_db_class.return_value = mock_db

            mock_fetcher = Mock()
            mock_fetcher.is_available.return_value = True
            mock_fetcher.process_article_with_translation.side_effect = Exception(
                "API Error"
            )
            mock_fetcher_class.return_value = mock_fetcher

            result = handle_special_modes(args, config)

            assert result is True
            # Should handle the exception gracefully
            print_calls = [call[0][0] for call in mock_print.call_args_list if call[0]]
            output_text = " ".join(print_calls)
            assert "Error processing article" in output_text
