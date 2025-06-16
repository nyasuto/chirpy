"""
Unit tests for ContentFetcher web scraping and AI summarization.
"""

from unittest.mock import MagicMock, patch

import pytest
import responses

from content_fetcher import ContentFetcher


class TestContentFetcher:
    """Test ContentFetcher web scraping and AI operations."""

    def test_content_fetcher_initialization(self, test_config):
        """Test ContentFetcher initialization."""
        fetcher = ContentFetcher(test_config)
        assert fetcher.config == test_config
        assert fetcher.openai_client is None  # No real API key

    def test_content_fetcher_with_mock_openai(self, test_config, mock_openai_client):
        """Test ContentFetcher with mocked OpenAI client."""
        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client
            fetcher = ContentFetcher(test_config)
            assert fetcher.openai_client == mock_openai_client

    def test_is_available_without_openai(self, test_config):
        """Test availability check without OpenAI client."""
        fetcher = ContentFetcher(test_config)
        assert fetcher.is_available() is False

    def test_is_available_with_openai(self, test_config, mock_openai_client):
        """Test availability check with OpenAI client."""
        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client
            fetcher = ContentFetcher(test_config)
            assert fetcher.is_available() is True

    def test_detect_language_english(self, content_fetcher):
        """Test language detection for English text."""
        with patch("content_fetcher.detect") as mock_detect:
            mock_detect.return_value = "en"

            language = content_fetcher.detect_language("This is English text")
            assert language == "en"
            mock_detect.assert_called_once_with("This is English text")

    def test_detect_language_japanese(self, content_fetcher):
        """Test language detection for Japanese text."""
        with patch("content_fetcher.detect") as mock_detect:
            mock_detect.return_value = "ja"

            language = content_fetcher.detect_language("これは日本語です")
            assert language == "ja"
            mock_detect.assert_called_once_with("これは日本語です")

    def test_detect_language_error(self, content_fetcher):
        """Test language detection error handling."""
        with patch("content_fetcher.detect") as mock_detect:
            mock_detect.side_effect = Exception("Detection failed")

            language = content_fetcher.detect_language("Some text")
            assert language == "unknown"

    def test_detect_language_no_langdetect(self, content_fetcher):
        """Test language detection when langdetect is not available."""
        with patch("content_fetcher.detect", None):
            language = content_fetcher.detect_language("Some text")
            assert language == "unknown"

    @responses.activate
    def test_fetch_article_content_success(self, content_fetcher):
        """Test successful article content fetching."""
        url = "https://example.com/test"
        html_content = """
        <html>
            <body>
                <h1>Test Title</h1>
                <p>This is test content.</p>
                <p>More content here.</p>
            </body>
        </html>
        """

        responses.add(responses.GET, url, body=html_content, status=200)

        content = content_fetcher.fetch_article_content(url)
        assert content is not None
        assert "Test Title" in content
        assert "This is test content." in content
        assert "More content here." in content

    @responses.activate
    def test_fetch_article_content_404(self, content_fetcher):
        """Test article content fetching with 404 error."""
        url = "https://example.com/404"
        responses.add(responses.GET, url, status=404)

        content = content_fetcher.fetch_article_content(url)
        assert content is None

    @responses.activate
    def test_fetch_article_content_timeout(self, content_fetcher):
        """Test article content fetching with timeout."""
        url = "https://example.com/timeout"
        responses.add(responses.GET, url, body=Exception("Timeout"))

        with patch("content_fetcher.requests.get") as mock_get:
            mock_get.side_effect = Exception("Timeout")
            content = content_fetcher.fetch_article_content(url)
            assert content is None

    def test_fetch_article_content_invalid_url(self, content_fetcher):
        """Test article content fetching with invalid URL."""
        content = content_fetcher.fetch_article_content("not-a-url")
        assert content is None

    def test_summarize_content_success(self, test_config, mock_openai_client):
        """Test successful content summarization."""
        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client

            fetcher = ContentFetcher(test_config)

            content = "This is a long article about technology and AI."
            title = "Tech Article"

            summary = fetcher.summarize_content(content, title)
            assert summary == "Mocked Japanese translation"

            # Verify OpenAI was called correctly
            mock_openai_client.chat.completions.create.assert_called_once()
            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args.kwargs["model"] == test_config.openai_model
            assert call_args.kwargs["max_tokens"] == test_config.openai_max_tokens

    def test_summarize_content_no_openai(self, content_fetcher):
        """Test content summarization without OpenAI client."""
        summary = content_fetcher.summarize_content("Some content", "Title")
        assert summary is None

    def test_summarize_content_openai_error(self, test_config, mock_openai_client):
        """Test content summarization with OpenAI error."""
        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client
            mock_openai_client.chat.completions.create.side_effect = Exception(
                "API Error"
            )

            fetcher = ContentFetcher(test_config)
            summary = fetcher.summarize_content("Content", "Title")
            assert summary is None

    def test_summarize_and_translate_english(self, test_config, mock_openai_client):
        """Test English content translation and summarization."""
        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client

            fetcher = ContentFetcher(test_config)

            content = "This is English content about technology."
            title = "English Article"

            result = fetcher.summarize_and_translate(content, title, "en")
            assert result == "Mocked Japanese translation"

    def test_summarize_and_translate_non_english(self, test_config, mock_openai_client):
        """Test non-English content handling in translation."""
        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client

            fetcher = ContentFetcher(test_config)

            result = fetcher.summarize_and_translate("Content", "Title", "ja")
            assert result is None  # Should not translate Japanese content

    def test_process_empty_summary_article_success(
        self, test_config, mock_openai_client
    ):
        """Test processing article with empty summary."""
        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client

            fetcher = ContentFetcher(test_config)

            with patch.object(fetcher, "fetch_article_content") as mock_fetch:
                mock_fetch.return_value = "Fetched content"

                article = {
                    "id": 1,
                    "link": "https://example.com/test",
                    "title": "Test Article",
                }

                summary = fetcher.process_empty_summary_article(article)
                assert summary == "Mocked Japanese translation"
                mock_fetch.assert_called_once_with("https://example.com/test")

    def test_process_empty_summary_article_no_url(self, content_fetcher):
        """Test processing article without URL."""
        article = {"id": 1, "title": "Test Article"}

        summary = content_fetcher.process_empty_summary_article(article)
        assert summary is None

    def test_process_empty_summary_article_fetch_failed(
        self, test_config, mock_openai_client
    ):
        """Test processing article when content fetch fails."""
        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client

            fetcher = ContentFetcher(test_config)

            with patch.object(fetcher, "fetch_article_content") as mock_fetch:
                mock_fetch.return_value = None

                article = {
                    "id": 1,
                    "link": "https://example.com/test",
                    "title": "Test Article",
                }

                summary = fetcher.process_empty_summary_article(article)
                assert summary is None

    def test_process_article_with_translation_english(
        self, test_config, mock_openai_client
    ):
        """Test processing English article with translation."""
        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client

            fetcher = ContentFetcher(test_config)

            with patch.object(fetcher, "detect_language") as mock_detect:
                mock_detect.return_value = "en"

                article = {
                    "id": 1,
                    "title": "English Article",
                    "summary": "This is English content",
                }

                result = fetcher.process_article_with_translation(article)
                summary, detected_lang, is_translated = result

                assert summary == "Mocked Japanese translation"
                assert detected_lang == "en"
                assert is_translated is True

    def test_process_article_with_translation_japanese(
        self, test_config, mock_openai_client
    ):
        """Test processing Japanese article (no translation needed)."""
        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client

            fetcher = ContentFetcher(test_config)

            with patch.object(fetcher, "detect_language") as mock_detect:
                mock_detect.return_value = "ja"

                article = {
                    "id": 1,
                    "title": "Japanese Article",
                    "summary": "これは日本語です",
                }

                result = fetcher.process_article_with_translation(article)
                summary, detected_lang, is_translated = result

                assert summary == "Mocked Japanese translation"  # Normal summarization
                assert detected_lang == "ja"
                assert is_translated is False

    def test_process_article_with_translation_no_summary(
        self, test_config, mock_openai_client
    ):
        """Test processing article without existing summary."""
        with patch("content_fetcher.openai") as mock_openai:
            mock_openai.OpenAI.return_value = mock_openai_client

            fetcher = ContentFetcher(test_config)

            with patch.object(fetcher, "fetch_article_content") as mock_fetch:
                mock_fetch.return_value = "Fetched English content"

                with patch.object(fetcher, "detect_language") as mock_detect:
                    mock_detect.return_value = "en"

                    article = {
                        "id": 1,
                        "title": "Article",
                        "link": "https://example.com/test",
                        "summary": "",
                    }

                    result = fetcher.process_article_with_translation(article)
                    summary, detected_lang, is_translated = result

                    assert summary == "Mocked Japanese translation"
                    assert detected_lang == "en"
                    assert is_translated is True
                    mock_fetch.assert_called_once()

    def test_clean_text_content(self, content_fetcher):
        """Test text cleaning functionality."""
        # This is a private method test - access via public methods
        html_content = """
        <html>
            <body>
                <script>alert('test');</script>
                <style>body { color: red; }</style>
                <h1>Title</h1>
                <p>Content with <a href="#">link</a>.</p>
                <div>More content</div>
            </body>
        </html>
        """

        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, "https://test.com", body=html_content, status=200)

            content = content_fetcher.fetch_article_content("https://test.com")

            assert content is not None
            assert "alert('test')" not in content  # Scripts removed
            assert "color: red" not in content  # Styles removed
            assert "Title" in content
            assert "Content with link" in content
            assert "More content" in content
