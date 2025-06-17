"""Tests for ChirpyLogger initialization and log formatting."""

import logging
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from config import ChirpyConfig, ChirpyLogger


class TestChirpyLogger:
    """Test suite for ChirpyLogger class."""

    @pytest.mark.unit
    def test_logger_initialization_with_defaults(self):
        """Test ChirpyLogger initialization with default configuration."""
        config = ChirpyConfig(log_level="INFO")
        logger_instance = ChirpyLogger(config)

        # Check that logger was properly initialized
        assert logger_instance.config == config

        # Check that root logger level was set
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    @pytest.mark.unit
    def test_logger_initialization_with_custom_level(self):
        """Test ChirpyLogger initialization with custom log level."""
        config = ChirpyConfig(log_level="DEBUG")
        _ = ChirpyLogger(config)

        # Check that root logger level was set to DEBUG
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    @pytest.mark.unit
    def test_logger_level_validation(self):
        """Test that logger handles invalid log levels gracefully."""
        config = ChirpyConfig(log_level="INVALID")
        _ = ChirpyLogger(config)

        # Should fall back to INFO level for invalid levels
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    @pytest.mark.unit
    def test_console_handler_configuration(self):
        """Test that console handler is properly configured."""
        config = ChirpyConfig(
            log_level="WARNING", log_format="TEST: %(levelname)s - %(message)s"
        )

        # Capture console output
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            _ = ChirpyLogger(config)

            # Get a logger and test it
            test_logger = logging.getLogger("test")
            test_logger.warning("Test warning message")

            # Check that message was formatted correctly
            output = mock_stderr.getvalue()
            assert "WARNING - Test warning message" in output

    @pytest.mark.unit
    def test_file_handler_configuration(self, temp_dir):
        """Test that file handler is properly configured when log_file is set."""
        log_file = temp_dir / "test.log"
        config = ChirpyConfig(
            log_level="INFO",
            log_file=str(log_file),
            log_format="%(levelname)s: %(message)s",
        )

        _ = ChirpyLogger(config)

        # Test that file handler was added
        root_logger = logging.getLogger()
        file_handlers = [
            h
            for h in root_logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) == 1

        # Test logging to file
        test_logger = logging.getLogger("test_file")
        test_logger.info("Test file message")

        # Check that file was created and contains message
        assert log_file.exists()
        with open(log_file) as f:
            content = f.read()
            assert "INFO: Test file message" in content

    @pytest.mark.unit
    def test_rotating_file_handler_settings(self, temp_dir):
        """Test that rotating file handler uses correct settings."""
        log_file = temp_dir / "rotating.log"
        config = ChirpyConfig(
            log_file=str(log_file), log_max_bytes=1024, log_backup_count=5
        )

        _ = ChirpyLogger(config)

        # Find the rotating file handler
        root_logger = logging.getLogger()
        file_handler = None
        for handler in root_logger.handlers:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                file_handler = handler
                break

        assert file_handler is not None
        assert file_handler.maxBytes == 1024
        assert file_handler.backupCount == 5

    @pytest.mark.unit
    def test_file_handler_directory_creation(self, temp_dir):
        """Test that parent directories are created for log files."""
        nested_log_file = temp_dir / "logs" / "nested" / "test.log"
        config = ChirpyConfig(log_file=str(nested_log_file))

        # Directory should not exist initially
        assert not nested_log_file.parent.exists()

        _ = ChirpyLogger(config)

        # Test logging to create the file
        test_logger = logging.getLogger("test_nested")
        test_logger.info("Test nested log")

        # Check that directories were created and file exists
        assert nested_log_file.parent.exists()
        assert nested_log_file.exists()

    @pytest.mark.unit
    def test_file_handler_error_handling(self, temp_dir):
        """Test that file handler errors are handled gracefully."""
        # Try to create log file in a read-only directory
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only

        invalid_log_file = readonly_dir / "test.log"
        config = ChirpyConfig(log_file=str(invalid_log_file))

        # Should not raise exception, just log warning
        with patch("logging.warning") as mock_warning:
            _ = ChirpyLogger(config)
            # Should have called warning about file logging failure
            mock_warning.assert_called_once()

    @pytest.mark.unit
    def test_third_party_logger_levels(self):
        """Test that third-party library loggers are set to WARNING level."""
        config = ChirpyConfig(log_level="DEBUG")
        _ = ChirpyLogger(config)

        # Check that third-party loggers are set to WARNING
        assert logging.getLogger("urllib3").level == logging.WARNING
        assert logging.getLogger("requests").level == logging.WARNING
        assert logging.getLogger("openai").level == logging.WARNING

    @pytest.mark.unit
    def test_logger_cleanup_and_reinitialization(self):
        """Test that existing handlers are cleaned up on reinitialization."""
        config = ChirpyConfig(log_level="INFO")

        # Initialize logger first time
        _ = ChirpyLogger(config)
        initial_handlers = len(logging.getLogger().handlers)

        # Initialize logger second time
        _ = ChirpyLogger(config)
        final_handlers = len(logging.getLogger().handlers)

        # Should not accumulate handlers
        assert final_handlers == initial_handlers

    @pytest.mark.unit
    def test_get_logger_static_method(self):
        """Test ChirpyLogger.get_logger static method."""
        logger = ChirpyLogger.get_logger("test_module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    @pytest.mark.unit
    def test_custom_log_format(self):
        """Test that custom log format is properly applied."""
        custom_format = "CUSTOM: %(name)s | %(levelname)s | %(message)s"
        config = ChirpyConfig(log_format=custom_format)

        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            _ = ChirpyLogger(config)

            test_logger = logging.getLogger("custom_test")
            test_logger.error("Custom format test")

            output = mock_stderr.getvalue()
            assert "CUSTOM: custom_test | ERROR | Custom format test" in output

    @pytest.mark.unit
    def test_log_level_hierarchy(self):
        """Test that log level hierarchy is respected."""
        config = ChirpyConfig(log_level="WARNING")

        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            _ = ChirpyLogger(config)

            test_logger = logging.getLogger("hierarchy_test")
            test_logger.debug("Debug message")  # Should not appear
            test_logger.info("Info message")  # Should not appear
            test_logger.warning("Warning message")  # Should appear
            test_logger.error("Error message")  # Should appear

            output = mock_stderr.getvalue()
            assert "Debug message" not in output
            assert "Info message" not in output
            assert "Warning message" in output
            assert "Error message" in output

    @pytest.mark.unit
    def test_integration_with_config_from_env(self):
        """Test ChirpyLogger integration with config loaded from environment."""
        import os
        from unittest.mock import patch

        env_vars = {
            "LOG_LEVEL": "DEBUG",
            "LOG_FORMAT": "ENV: %(levelname)s - %(message)s",
        }

        with patch.dict(os.environ, env_vars):
            config = ChirpyConfig.from_env()

            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                _ = ChirpyLogger(config)

                test_logger = logging.getLogger("env_test")
                test_logger.debug("Environment config test")

                output = mock_stderr.getvalue()
                assert "ENV: DEBUG - Environment config test" in output

    @pytest.mark.unit
    def test_logger_instance_reuse(self):
        """Test that logger instances can be reused safely."""
        config1 = ChirpyConfig(log_level="INFO")
        config2 = ChirpyConfig(log_level="DEBUG")

        _ = ChirpyLogger(config1)
        _ = ChirpyLogger(config2)

        # Both should work independently
        _ = logging.getLogger("reuse_test")

        # Should use the most recent configuration (DEBUG)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    @pytest.mark.unit
    def test_path_expansion_in_log_file(self, temp_dir):
        """Test that log file paths are properly expanded."""
        # Test with relative path
        config = ChirpyConfig(log_file="./test_logs/app.log")
        _ = ChirpyLogger(config)

        # Test that logging works with expanded path
        test_logger = logging.getLogger("path_test")
        test_logger.info("Path expansion test")

        # Should create the relative directory structure
        assert Path("./test_logs").exists()
        assert Path("./test_logs/app.log").exists()

        # Cleanup
        import shutil

        shutil.rmtree("./test_logs", ignore_errors=True)

    @pytest.mark.unit
    def test_multiple_loggers_same_config(self):
        """Test creating multiple named loggers with same configuration."""
        config = ChirpyConfig(log_level="INFO")
        logger_instance = ChirpyLogger(config)

        logger1 = logger_instance.get_logger("module1")
        logger2 = logger_instance.get_logger("module2")
        logger3 = logger_instance.get_logger("module3")

        assert logger1.name == "module1"
        assert logger2.name == "module2"
        assert logger3.name == "module3"

        # All should have the same effective level
        assert logger1.getEffectiveLevel() == logging.INFO
        assert logger2.getEffectiveLevel() == logging.INFO
        assert logger3.getEffectiveLevel() == logging.INFO
