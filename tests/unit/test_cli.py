"""
Unit tests for CLI argument parsing and validation.
"""

import argparse
from io import StringIO
from unittest.mock import patch

import pytest

from cli import create_parser, parse_args, apply_args_to_config
from config import ChirpyConfig


class TestCLIArgumentParsing:
    """Test CLI argument parsing functionality."""

    def test_create_parser(self):
        """Test parser creation."""
        parser = create_parser()
        assert isinstance(parser, argparse.ArgumentParser)
        assert "chirpy" in parser.prog.lower()

    def test_parse_args_default(self):
        """Test parsing with default arguments."""
        args = parse_args([])
        
        assert args.database is None
        assert args.max_articles is None
        assert args.no_speech is False
        assert args.stats is False
        assert args.show_config is False
        assert args.process_summaries is False
        assert args.translate_articles is False

    def test_parse_args_database_positional(self):
        """Test parsing database path as positional argument."""
        args = parse_args(["/path/to/db.sqlite"])
        assert args.database == "/path/to/db.sqlite"

    def test_parse_args_max_articles(self):
        """Test parsing max articles argument."""
        args = parse_args(["--max-articles", "5"])
        assert args.max_articles == 5

    def test_parse_args_max_articles_invalid(self):
        """Test parsing invalid max articles argument."""
        with pytest.raises(SystemExit):
            parse_args(["--max-articles", "invalid"])

    def test_parse_args_no_speech(self):
        """Test parsing no-speech flag."""
        args = parse_args(["--no-speech"])
        assert args.no_speech is True

    def test_parse_args_tts_settings(self):
        """Test parsing TTS settings."""
        args = parse_args([
            "--tts-rate", "200",
            "--tts-volume", "0.8",
            "--tts-engine", "say"
        ])
        
        assert args.tts_rate == 200
        assert args.tts_volume == 0.8
        assert args.tts_engine == "say"

    def test_parse_args_tts_engine_invalid(self):
        """Test parsing invalid TTS engine."""
        with pytest.raises(SystemExit):
            parse_args(["--tts-engine", "invalid"])

    def test_parse_args_translation_settings(self):
        """Test parsing translation settings."""
        args = parse_args([
            "--no-translate",
            "--target-language", "en"
        ])
        
        assert args.no_translate is True
        assert args.target_language == "en"

    def test_parse_args_special_modes(self):
        """Test parsing special mode arguments."""
        args = parse_args([
            "--stats",
            "--show-config",
            "--process-summaries",
            "--translate-articles"
        ])
        
        assert args.stats is True
        assert args.show_config is True
        assert args.process_summaries is True
        assert args.translate_articles is True

    def test_parse_args_logging_settings(self):
        """Test parsing logging settings."""
        args = parse_args([
            "--log-level", "DEBUG",
            "--log-file", "/path/to/log.txt",
            "--verbose",
            "--quiet"
        ])
        
        assert args.log_level == "DEBUG"
        assert args.log_file == "/path/to/log.txt"
        assert args.verbose is True
        assert args.quiet is True

    def test_parse_args_log_level_invalid(self):
        """Test parsing invalid log level."""
        with pytest.raises(SystemExit):
            parse_args(["--log-level", "INVALID"])

    def test_parse_args_config_file(self):
        """Test parsing config file argument."""
        args = parse_args(["--config-file", "/path/to/config.env"])
        assert args.config_file == "/path/to/config.env"

    def test_parse_args_application_control(self):
        """Test parsing application control arguments."""
        args = parse_args([
            "--no-mark-read",
            "--no-pause"
        ])
        
        assert args.no_mark_read is True
        assert args.no_pause is True

    def test_parse_args_fetch_timeout(self):
        """Test parsing fetch timeout argument."""
        args = parse_args(["--fetch-timeout", "60"])
        assert args.fetch_timeout == 60

    def test_parse_args_help(self):
        """Test help output."""
        with pytest.raises(SystemExit) as exc_info:
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                parse_args(["--help"])
        
        assert exc_info.value.code == 0  # Help should exit with code 0

    def test_parse_args_version(self):
        """Test version output."""
        with pytest.raises(SystemExit) as exc_info:
            with patch('sys.stdout', new_callable=StringIO):
                parse_args(["--version"])
        
        assert exc_info.value.code == 0  # Version should exit with code 0


class TestConfigApplication:
    """Test applying CLI arguments to configuration."""

    def test_apply_args_to_config_default(self, test_config):
        """Test applying default arguments to config."""
        args = parse_args([])
        config = apply_args_to_config(args, test_config)
        
        # Should return the same config when no args are provided
        assert config.database_path == test_config.database_path
        assert config.max_articles == test_config.max_articles

    def test_apply_args_to_config_database(self, test_config):
        """Test applying database path argument."""
        args = parse_args(["/custom/db.sqlite"])
        config = apply_args_to_config(args, test_config)
        
        assert config.database_path == "/custom/db.sqlite"

    def test_apply_args_to_config_max_articles(self, test_config):
        """Test applying max articles argument."""
        args = parse_args(["--max-articles", "10"])
        config = apply_args_to_config(args, test_config)
        
        assert config.max_articles == 10

    def test_apply_args_to_config_speech_disabled(self, test_config):
        """Test applying no-speech argument."""
        args = parse_args(["--no-speech"])
        config = apply_args_to_config(args, test_config)
        
        assert config.speech_enabled is False

    def test_apply_args_to_config_tts_settings(self, test_config):
        """Test applying TTS settings."""
        args = parse_args([
            "--tts-rate", "250",
            "--tts-volume", "0.7",
            "--tts-engine", "say"
        ])
        config = apply_args_to_config(args, test_config)
        
        assert config.tts_rate == 250
        assert config.tts_volume == 0.7
        assert config.tts_engine == "say"

    def test_apply_args_to_config_translation_disabled(self, test_config):
        """Test applying translation disabled argument."""
        args = parse_args(["--no-translate"])
        config = apply_args_to_config(args, test_config)
        
        assert config.auto_translate is False

    def test_apply_args_to_config_target_language(self, test_config):
        """Test applying target language argument."""
        args = parse_args(["--target-language", "en"])
        config = apply_args_to_config(args, test_config)
        
        assert config.target_language == "en"

    def test_apply_args_to_config_fetch_timeout(self, test_config):
        """Test applying fetch timeout argument."""
        args = parse_args(["--fetch-timeout", "45"])
        config = apply_args_to_config(args, test_config)
        
        assert config.fetch_timeout == 45

    def test_apply_args_to_config_log_settings(self, test_config):
        """Test applying log settings."""
        args = parse_args([
            "--log-level", "WARNING",
            "--log-file", "/tmp/test.log"
        ])
        config = apply_args_to_config(args, test_config)
        
        assert config.log_level == "WARNING"
        assert config.log_file == "/tmp/test.log"

    def test_apply_args_to_config_verbose(self, test_config):
        """Test applying verbose argument."""
        args = parse_args(["--verbose"])
        config = apply_args_to_config(args, test_config)
        
        assert config.log_level == "DEBUG"

    def test_apply_args_to_config_quiet(self, test_config):
        """Test applying quiet argument."""
        args = parse_args(["--quiet"])
        config = apply_args_to_config(args, test_config)
        
        assert config.log_level == "ERROR"

    def test_apply_args_to_config_application_control(self, test_config):
        """Test applying application control arguments."""
        args = parse_args(["--no-mark-read", "--no-pause"])
        config = apply_args_to_config(args, test_config)
        
        assert config.auto_mark_read is False
        assert config.pause_between_articles is False

    def test_apply_args_to_config_config_file(self, test_config, temp_dir):
        """Test applying config file argument."""
        # Create a test config file
        config_file = temp_dir / "test.env"
        config_file.write_text("""
CHIRPY_MAX_ARTICLES=7
TTS_RATE=200
SPEECH_ENABLED=false
""")
        
        args = parse_args(["--config-file", str(config_file)])
        
        with patch.dict('os.environ', {}, clear=True):
            config = apply_args_to_config(args, test_config)
            
            # Config should be reloaded from file
            assert config.max_articles == 7
            assert config.tts_rate == 200
            assert config.speech_enabled is False

    def test_apply_args_to_config_config_file_not_found(self, test_config, temp_dir):
        """Test applying non-existent config file argument."""
        config_file = temp_dir / "nonexistent.env"
        args = parse_args(["--config-file", str(config_file)])
        
        # Should handle missing file gracefully
        config = apply_args_to_config(args, test_config)
        assert config.database_path == test_config.database_path

    def test_apply_args_to_config_multiple_overrides(self, test_config):
        """Test applying multiple configuration overrides."""
        args = parse_args([
            "/custom/db.sqlite",
            "--max-articles", "15",
            "--no-speech",
            "--tts-rate", "300",
            "--no-translate",
            "--log-level", "WARNING"
        ])
        
        config = apply_args_to_config(args, test_config)
        
        assert config.database_path == "/custom/db.sqlite"
        assert config.max_articles == 15
        assert config.speech_enabled is False
        assert config.tts_rate == 300
        assert config.auto_translate is False
        assert config.log_level == "WARNING"