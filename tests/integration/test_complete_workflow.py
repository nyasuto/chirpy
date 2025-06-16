"""
Integration tests for complete Chirpy workflows.
"""

from unittest.mock import MagicMock, patch

import pytest
import responses

from chirpy import ChirpyReader


class TestCompleteWorkflow:
    """Test complete article reading and processing workflows."""

    @pytest.fixture
    def mock_chirpy_reader(self, test_config, db_manager):
        """Create a ChirpyReader with mocked TTS for testing."""
        with patch("chirpy.ChirpyReader._initialize_tts") as mock_init_tts:
            mock_init_tts.return_value = None  # Disable TTS
            reader = ChirpyReader(test_config)
            reader.db = db_manager
            return reader

    def test_read_articles_workflow(self, mock_chirpy_reader, sample_articles):
        """Test complete article reading workflow."""
        # Mock TTS to avoid actual speech
        with patch.object(mock_chirpy_reader, "speak_text") as mock_speak:
            mock_chirpy_reader.read_articles()

            # Should speak introduction and conclusion
            assert mock_speak.call_count >= 2

            # Check intro and outro messages
            calls = [call.args[0] for call in mock_speak.call_args_list]
            intro_call = next(
                (call for call in calls if "Welcome to Chirpy" in call), None
            )
            outro_call = next(
                (call for call in calls if "That's all for now" in call), None
            )

            assert intro_call is not None
            assert outro_call is not None

    @pytest.mark.skip(reason="Complex OpenAI mocking needs refinement")
    def test_read_articles_with_translation(
        self, mock_chirpy_reader, mock_openai_client
    ):
        """Test article reading with on-demand translation."""
        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client

            # Mock language detection for unknown articles
            with patch("content_fetcher.detect") as mock_detect:
                mock_detect.return_value = "en"

                with patch.object(mock_chirpy_reader, "speak_text") as mock_speak:
                    mock_chirpy_reader.read_articles()

                    # Should have processed articles and spoken content
                    assert mock_speak.call_count >= 2

                    # Verify OpenAI was called for translation
                    assert mock_openai_client.chat.completions.create.called

    @pytest.mark.skip(reason="Complex OpenAI mocking needs refinement")
    def test_process_empty_summaries_workflow(
        self, mock_chirpy_reader, mock_openai_client
    ):
        """Test complete empty summary processing workflow."""
        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client

            with responses.RequestsMock() as rsps:
                # Mock successful content fetch
                rsps.add(
                    responses.GET,
                    "https://example.com/empty",
                    body="<html><body><p>Fetched content for empty summary</p></body></html>",
                    status=200,
                )

                # Process empty summaries
                processed_count = mock_chirpy_reader.process_empty_summaries()

                # Should have processed the empty summary article
                assert processed_count == 1

                # Verify OpenAI was called for summarization
                assert mock_openai_client.chat.completions.create.called

    @pytest.mark.skip(reason="Integration test needs refinement")
    def test_no_unread_articles_workflow(self, mock_chirpy_reader):
        """Test workflow when no unread articles exist."""
        # Mark all articles as read
        for article_id in range(1, 6):
            mock_chirpy_reader.db.mark_article_as_read(article_id)

        with patch.object(mock_chirpy_reader, "speak_text") as mock_speak:
            mock_chirpy_reader.read_articles()

            # Should speak "no unread articles" message
            calls = [call.args[0] for call in mock_speak.call_args_list]
            no_articles_call = next(
                (call for call in calls if "No unread articles" in call), None
            )
            assert no_articles_call is not None

    @pytest.mark.skip(reason="Integration test needs refinement")
    def test_read_articles_with_errors(self, mock_chirpy_reader):
        """Test article reading workflow with errors."""
        # Mock database error
        with patch.object(mock_chirpy_reader.db, "get_unread_articles") as mock_get:
            mock_get.side_effect = Exception("Database error")

            with patch.object(mock_chirpy_reader, "speak_text") as mock_speak:
                with pytest.raises(SystemExit):
                    mock_chirpy_reader.read_articles()

                # Should speak error message
                calls = [call.args[0] for call in mock_speak.call_args_list]
                error_call = next(
                    (call for call in calls if "error occurred" in call), None
                )
                assert error_call is not None

    def test_article_marking_as_read(self, mock_chirpy_reader):
        """Test articles are properly marked as read."""
        initial_read_count = mock_chirpy_reader.db.get_read_count()

        with patch.object(mock_chirpy_reader, "speak_text"):
            mock_chirpy_reader.read_articles()

        final_read_count = mock_chirpy_reader.db.get_read_count()

        # Should have marked articles as read
        assert final_read_count > initial_read_count

    def test_article_content_formatting(self, mock_chirpy_reader, sample_articles):
        """Test article content formatting for speech."""
        article = sample_articles[0]  # Japanese article

        content = mock_chirpy_reader.format_article_content(article)

        assert "Article title:" in content
        assert article["title"] in content
        assert "Content:" in content
        assert article["summary"] in content

    def test_translated_article_formatting(self, mock_chirpy_reader, sample_articles):
        """Test formatting of translated articles."""
        # Create a translated English article
        article = sample_articles[1].copy()
        article["detected_language"] = "en"
        article["is_translated"] = True
        article["summary"] = "これは翻訳された記事です。"

        content = mock_chirpy_reader.format_article_content(article)

        assert "英語記事 → 日本語翻訳済み" in content
        assert article["title"] in content
        assert "これは翻訳された記事です。" in content

    def test_configuration_integration(self, test_config, db_manager):
        """Test integration between configuration and components."""
        # Test with custom configuration
        custom_config = test_config
        custom_config.max_articles = 2
        custom_config.speech_enabled = False
        custom_config.auto_mark_read = False

        with patch("chirpy.ChirpyReader._initialize_tts"):
            reader = ChirpyReader(custom_config)
            reader.db = db_manager

            # Configuration should be properly applied
            assert reader.config.max_articles == 2
            assert reader.config.speech_enabled is False
            assert reader.config.auto_mark_read is False

    def test_database_statistics_integration(self, mock_chirpy_reader):
        """Test database statistics display integration."""
        stats = mock_chirpy_reader.db.get_database_stats()

        assert "total_articles" in stats
        assert "read_articles" in stats
        assert "unread_articles" in stats
        assert "empty_summaries" in stats

        # Stats should be consistent
        assert stats["total_articles"] >= stats["read_articles"]
        assert stats["total_articles"] >= stats["unread_articles"]

    @responses.activate
    @pytest.mark.skip(reason="Complex OpenAI mocking needs refinement")
    def test_content_fetching_integration(self, mock_chirpy_reader, mock_openai_client):
        """Test content fetching and processing integration."""
        # Mock web content
        responses.add(
            responses.GET,
            "https://example.com/test-integration",
            body="""
            <html>
                <body>
                    <h1>Integration Test Article</h1>
                    <p>This is content for integration testing.</p>
                    <p>Multiple paragraphs of content.</p>
                </body>
            </html>
            """,
            status=200,
        )

        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client

            # Test fetching and processing
            fetcher = mock_chirpy_reader.content_fetcher
            content = fetcher.fetch_article_content(
                "https://example.com/test-integration"
            )

            assert content is not None
            assert "Integration Test Article" in content
            assert "integration testing" in content

            # Test summarization
            summary = fetcher.summarize_content(content, "Test Article")
            assert summary == "Mocked Japanese translation"

    @pytest.mark.skip(reason="Integration test needs refinement")
    def test_error_recovery_integration(self, mock_chirpy_reader):
        """Test error recovery in complete workflow."""
        # Simulate various error conditions
        with patch.object(
            mock_chirpy_reader, "process_article_for_reading"
        ) as mock_process:
            # First article fails, second succeeds
            mock_process.side_effect = [
                Exception("Processing error"),
                sample_articles[1],  # Return second article normally
                sample_articles[2],  # Return third article normally
            ]

            with patch.object(mock_chirpy_reader, "speak_text") as mock_speak:
                # Should continue processing despite errors
                mock_chirpy_reader.read_articles()

                # Should still speak some content
                assert mock_speak.call_count >= 1

    @pytest.mark.skip(reason="Complex OpenAI mocking needs refinement")
    def test_rate_limiting_integration(self, mock_chirpy_reader, mock_openai_client):
        """Test rate limiting in processing workflows."""
        # Set rate limit delay
        mock_chirpy_reader.config.rate_limit_delay = 0.1

        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client

            with patch("time.sleep") as mock_sleep:
                # Process multiple empty summaries
                mock_chirpy_reader.process_empty_summaries(max_articles=2)

                # Should have used rate limiting
                assert mock_sleep.called

    def test_logging_integration(self, mock_chirpy_reader, caplog):
        """Test logging integration throughout workflow."""
        with patch.object(mock_chirpy_reader, "speak_text"):
            mock_chirpy_reader.read_articles()

        # Should have logged various stages
        log_messages = [record.message for record in caplog.records]

        # Look for key log messages
        start_log = any("Chirpy RSS Reader Starting" in msg for msg in log_messages)
        stats_log = any("Database Stats" in msg for msg in log_messages)
        complete_log = any("Session complete" in msg for msg in log_messages)

        assert start_log
        assert stats_log
        assert complete_log
