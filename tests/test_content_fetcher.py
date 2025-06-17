"""Tests for ContentFetcher web scraping and summarization."""

from unittest.mock import Mock, patch

import pytest
import requests

from config import ChirpyConfig
from content_fetcher import ContentFetcher


class TestContentFetcher:
    """Test suite for ContentFetcher class."""

    @pytest.mark.unit
    def test_content_fetcher_initialization_with_openai(self):
        """Test ContentFetcher initialization with valid OpenAI configuration."""
        config = ChirpyConfig(openai_api_key="test-key")

        with patch("content_fetcher.openai") as mock_openai_module:
            mock_client = Mock()
            mock_openai_module.OpenAI.return_value = mock_client

            fetcher = ContentFetcher(config)

            assert fetcher.config == config
            assert fetcher.openai_client == mock_client
            assert fetcher.logger is not None
            mock_openai_module.OpenAI.assert_called_once_with(api_key="test-key")

    @pytest.mark.unit
    def test_content_fetcher_initialization_without_openai(self):
        """Test ContentFetcher initialization without OpenAI available."""
        config = ChirpyConfig(openai_api_key="test-key")

        with patch("content_fetcher.openai", None):
            fetcher = ContentFetcher(config)

            assert fetcher.config == config
            assert fetcher.openai_client is None

    @pytest.mark.unit
    def test_content_fetcher_initialization_without_api_key(self):
        """Test ContentFetcher initialization without API key."""
        config = ChirpyConfig(openai_api_key="")

        with patch("content_fetcher.openai") as mock_openai_module:
            fetcher = ContentFetcher(config)

            assert fetcher.config == config
            assert fetcher.openai_client is None
            mock_openai_module.OpenAI.assert_not_called()

    @pytest.mark.unit
    def test_content_fetcher_initialization_openai_error(self):
        """Test ContentFetcher initialization with OpenAI client error."""
        config = ChirpyConfig(openai_api_key="test-key")

        with patch("content_fetcher.openai") as mock_openai_module:
            mock_openai_module.OpenAI.side_effect = Exception("API error")

            fetcher = ContentFetcher(config)

            assert fetcher.config == config
            assert fetcher.openai_client is None

    @pytest.mark.unit
    def test_detect_language_success(self):
        """Test successful language detection."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        with patch("content_fetcher.detect") as mock_detect:
            mock_detect.return_value = "en"

            result = fetcher.detect_language("This is English text")

            assert result == "en"
            mock_detect.assert_called_once()

    @pytest.mark.unit
    def test_detect_language_without_langdetect(self):
        """Test language detection without langdetect library."""
        config = ChirpyConfig()

        with patch("content_fetcher.detect", None):
            fetcher = ContentFetcher(config)
            result = fetcher.detect_language("Some text")

            assert result == "unknown"

    @pytest.mark.unit
    def test_detect_language_short_text(self):
        """Test language detection with text too short."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        with patch("content_fetcher.detect") as mock_detect:
            result = fetcher.detect_language("short")

            assert result == "unknown"
            mock_detect.assert_not_called()

    @pytest.mark.unit
    def test_detect_language_empty_text(self):
        """Test language detection with empty text."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        with patch("content_fetcher.detect") as mock_detect:
            result = fetcher.detect_language("")

            assert result == "unknown"
            mock_detect.assert_not_called()

    @pytest.mark.unit
    def test_detect_language_error(self):
        """Test language detection error handling."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        with patch("content_fetcher.detect") as mock_detect:
            mock_detect.side_effect = Exception("Detection error")

            result = fetcher.detect_language("This is some text for detection")

            assert result == "unknown"

    @pytest.mark.unit
    def test_fetch_article_content_success(self):
        """Test successful article content fetching."""
        config = ChirpyConfig(fetch_timeout=30)
        fetcher = ContentFetcher(config)

        mock_response = Mock()
        mock_response.content = b"""
        <html>
            <body>
                <article>
                    <h1>Test Title</h1>
                    <p>This is test content for the article.</p>
                    <p>Another paragraph with more content.</p>
                </article>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None

        with patch("content_fetcher.requests.get") as mock_get:
            mock_get.return_value = mock_response

            result = fetcher.fetch_article_content("https://example.com/article")

            assert result is not None
            assert "Test Title" in result
            assert "test content" in result
            assert "Another paragraph" in result
            mock_get.assert_called_once()

    @pytest.mark.unit
    def test_fetch_article_content_with_content_selectors(self):
        """Test content fetching with different content selectors."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        mock_response = Mock()
        mock_response.content = b"""
        <html>
            <body>
                <div class="content">
                    <h1>Main Content Title</h1>
                    <p>This is the main content area.</p>
                </div>
                <div class="sidebar">Sidebar content</div>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None

        with patch("content_fetcher.requests.get") as mock_get:
            mock_get.return_value = mock_response

            result = fetcher.fetch_article_content("https://example.com/article")

            assert result is not None
            assert "Main Content Title" in result
            assert "main content area" in result
            assert "Sidebar content" not in result

    @pytest.mark.unit
    def test_fetch_article_content_fallback_to_body(self):
        """Test content fetching fallback to body when no specific content found."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        mock_response = Mock()
        mock_response.content = b"""
        <html>
            <head><title>Page Title</title></head>
            <body>
                <nav>Navigation</nav>
                <div>Some body content here</div>
                <footer>Footer content</footer>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None

        with patch("content_fetcher.requests.get") as mock_get:
            mock_get.return_value = mock_response

            result = fetcher.fetch_article_content("https://example.com/article")

            assert result is not None
            assert "Some body content here" in result
            # Nav and footer should be removed
            assert "Navigation" not in result
            assert "Footer content" not in result

    @pytest.mark.unit
    def test_fetch_article_content_removes_unwanted_elements(self):
        """Test that unwanted HTML elements are removed."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        mock_response = Mock()
        mock_response.content = b"""
        <html>
            <body>
                <article>
                    <h1>Article Title</h1>
                    <script>console.log('should be removed');</script>
                    <p>Main content paragraph</p>
                    <style>body { margin: 0; }</style>
                    <nav>Navigation menu</nav>
                    <footer>Footer info</footer>
                </article>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None

        with patch("content_fetcher.requests.get") as mock_get:
            mock_get.return_value = mock_response

            result = fetcher.fetch_article_content("https://example.com/article")

            assert result is not None
            assert "Article Title" in result
            assert "Main content paragraph" in result
            assert "console.log" not in result
            assert "body { margin: 0; }" not in result
            assert "Navigation menu" not in result
            assert "Footer info" not in result

    @pytest.mark.unit
    def test_fetch_article_content_limits_length(self):
        """Test that content length is limited for API efficiency."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        # Create very long content
        long_content = "A" * 10000  # 10,000 characters
        mock_response = Mock()
        mock_response.content = f"""
        <html>
            <body>
                <article>{long_content}</article>
            </body>
        </html>
        """.encode()
        mock_response.raise_for_status.return_value = None

        with patch("content_fetcher.requests.get") as mock_get:
            mock_get.return_value = mock_response

            result = fetcher.fetch_article_content("https://example.com/article")

            assert result is not None
            assert len(result) <= 8003  # 8000 + "..."
            assert result.endswith("...")

    @pytest.mark.unit
    def test_fetch_article_content_http_error(self):
        """Test handling of HTTP errors during content fetching."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        with patch("content_fetcher.requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("404 Not Found")

            result = fetcher.fetch_article_content("https://example.com/article")

            assert result is None

    @pytest.mark.unit
    def test_fetch_article_content_timeout_error(self):
        """Test handling of timeout errors during content fetching."""
        config = ChirpyConfig(fetch_timeout=5)
        fetcher = ContentFetcher(config)

        with patch("content_fetcher.requests.get") as mock_get:
            mock_get.side_effect = requests.Timeout("Request timeout")

            result = fetcher.fetch_article_content("https://example.com/article")

            assert result is None

    @pytest.mark.unit
    def test_fetch_article_content_no_content_found(self):
        """Test handling when no content is found in HTML."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        mock_response = Mock()
        mock_response.content = (
            b"<html><head><title>Empty</title></head><body></body></html>"
        )
        mock_response.raise_for_status.return_value = None

        with patch("content_fetcher.requests.get") as mock_get:
            mock_get.return_value = mock_response

            result = fetcher.fetch_article_content("https://example.com/article")

            assert result is None

    @pytest.mark.unit
    def test_summarize_content_success(self):
        """Test successful content summarization."""
        config = ChirpyConfig(openai_api_key="test-key")

        with patch("content_fetcher.openai") as mock_openai_module:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "This is a test summary."
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_module.OpenAI.return_value = mock_client

            fetcher = ContentFetcher(config)
            result = fetcher.summarize_content(
                "Long article content here", "Article Title"
            )

            assert result == "This is a test summary."
            mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.unit
    def test_summarize_content_without_openai_client(self):
        """Test summarization without OpenAI client available."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        result = fetcher.summarize_content("Content", "Title")

        assert result is None

    @pytest.mark.unit
    def test_summarize_content_empty_response(self):
        """Test handling of empty response from OpenAI."""
        config = ChirpyConfig(openai_api_key="test-key")

        with patch("content_fetcher.openai") as mock_openai_module:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = None
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_module.OpenAI.return_value = mock_client

            fetcher = ContentFetcher(config)
            result = fetcher.summarize_content("Content", "Title")

            assert result is None

    @pytest.mark.unit
    def test_summarize_content_api_error(self):
        """Test handling of OpenAI API errors."""
        config = ChirpyConfig(openai_api_key="test-key")

        with patch("content_fetcher.openai") as mock_openai_module:
            mock_client = Mock()
            mock_client.chat.completions.create.side_effect = Exception("API Error")
            mock_openai_module.OpenAI.return_value = mock_client

            fetcher = ContentFetcher(config)
            result = fetcher.summarize_content("Content", "Title")

            assert result is None

    @pytest.mark.unit
    def test_summarize_and_translate_english_content(self):
        """Test summarization and translation of English content."""
        config = ChirpyConfig(
            openai_api_key="test-key", auto_translate=True, target_language="ja"
        )

        with patch("content_fetcher.openai") as mock_openai_module:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[
                0
            ].message.content = "これは英語記事の日本語要約です。"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_module.OpenAI.return_value = mock_client

            fetcher = ContentFetcher(config)
            result = fetcher.summarize_and_translate(
                "English article content", "English Title", "en"
            )

            assert result == "これは英語記事の日本語要約です。"
            # Verify translation prompt was used
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args[1]["messages"]
            assert "translate" in messages[1]["content"].lower()

    @pytest.mark.unit
    def test_summarize_and_translate_japanese_content(self):
        """Test summarization of Japanese content (no translation needed)."""
        config = ChirpyConfig(openai_api_key="test-key")

        with patch("content_fetcher.openai") as mock_openai_module:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "これは日本語記事の要約です。"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_module.OpenAI.return_value = mock_client

            fetcher = ContentFetcher(config)
            result = fetcher.summarize_and_translate(
                "日本語の記事内容", "日本語タイトル", "ja"
            )

            assert result == "これは日本語記事の要約です。"
            # Verify normal summarization prompt was used
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args[1]["messages"]
            assert "translate" not in messages[1]["content"].lower()

    @pytest.mark.unit
    def test_summarize_and_translate_without_openai(self):
        """Test translation attempt without OpenAI client."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        result = fetcher.summarize_and_translate("Content", "Title", "en")

        assert result is None

    @pytest.mark.unit
    def test_process_empty_summary_article_success(self):
        """Test complete workflow for processing article with empty summary."""
        config = ChirpyConfig(openai_api_key="test-key")

        article = {
            "id": 1,
            "title": "Test Article",
            "link": "https://example.com/article",
        }

        with patch("content_fetcher.openai") as mock_openai_module:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Generated summary"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_module.OpenAI.return_value = mock_client

            fetcher = ContentFetcher(config)

            # Mock the fetch_article_content method
            with patch.object(fetcher, "fetch_article_content") as mock_fetch:
                mock_fetch.return_value = "Article content from web"

                result = fetcher.process_empty_summary_article(article)

                assert result == "Generated summary"
                mock_fetch.assert_called_once_with("https://example.com/article")

    @pytest.mark.unit
    def test_process_empty_summary_article_no_url(self):
        """Test processing article without URL."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        article = {"id": 1, "title": "Test Article", "link": None}

        result = fetcher.process_empty_summary_article(article)

        assert result is None

    @pytest.mark.unit
    def test_process_empty_summary_article_fetch_failed(self):
        """Test processing when content fetching fails."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        article = {
            "id": 1,
            "title": "Test Article",
            "link": "https://example.com/article",
        }

        with patch.object(fetcher, "fetch_article_content") as mock_fetch:
            mock_fetch.return_value = None

            result = fetcher.process_empty_summary_article(article)

            assert result is None

    @pytest.mark.unit
    def test_process_article_with_translation_using_existing_summary(self):
        """Test translation workflow using existing summary."""
        config = ChirpyConfig(
            openai_api_key="test-key", auto_translate=True, target_language="ja"
        )

        article = {
            "id": 1,
            "title": "English Article",
            "summary": "Existing English summary content",
            "link": "https://example.com/article",
        }

        with patch("content_fetcher.openai") as mock_openai_module:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "翻訳された要約"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_module.OpenAI.return_value = mock_client

            fetcher = ContentFetcher(config)

            with patch.object(fetcher, "detect_language") as mock_detect:
                mock_detect.return_value = "en"

                summary, lang, translated = fetcher.process_article_with_translation(
                    article
                )

                assert summary == "翻訳された要約"
                assert lang == "en"
                assert translated is True
                mock_detect.assert_called_once_with("Existing English summary content")

    @pytest.mark.unit
    def test_process_article_with_translation_fetch_content(self):
        """Test translation workflow when fetching content from URL."""
        config = ChirpyConfig(openai_api_key="test-key")

        article = {
            "id": 1,
            "title": "Article Title",
            "summary": "",  # Empty summary
            "link": "https://example.com/article",
        }

        with patch("content_fetcher.openai") as mock_openai_module:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Generated summary"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_module.OpenAI.return_value = mock_client

            fetcher = ContentFetcher(config)

            with (
                patch.object(fetcher, "fetch_article_content") as mock_fetch,
                patch.object(fetcher, "detect_language") as mock_detect,
            ):
                mock_fetch.return_value = "Fetched article content"
                mock_detect.return_value = "ja"

                summary, lang, translated = fetcher.process_article_with_translation(
                    article
                )

                assert summary == "Generated summary"
                assert lang == "ja"
                assert translated is False
                mock_fetch.assert_called_once_with("https://example.com/article")

    @pytest.mark.unit
    def test_process_article_with_translation_no_url(self):
        """Test translation workflow with empty summary and no URL."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        article = {"id": 1, "title": "Article Title", "summary": "", "link": None}

        summary, lang, translated = fetcher.process_article_with_translation(article)

        assert summary is None
        assert lang == "unknown"
        assert translated is False

    @pytest.mark.unit
    def test_process_article_with_translation_fetch_failed(self):
        """Test translation workflow when content fetching fails."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        article = {
            "id": 1,
            "title": "Article Title",
            "summary": "",
            "link": "https://example.com/article",
        }

        with patch.object(fetcher, "fetch_article_content") as mock_fetch:
            mock_fetch.return_value = None

            summary, lang, translated = fetcher.process_article_with_translation(
                article
            )

            assert summary is None
            assert lang == "unknown"
            assert translated is False

    @pytest.mark.unit
    def test_is_available_with_openai_client(self):
        """Test availability check with OpenAI client."""
        config = ChirpyConfig(openai_api_key="test-key")

        with patch("content_fetcher.openai") as mock_openai_module:
            mock_client = Mock()
            mock_openai_module.OpenAI.return_value = mock_client

            fetcher = ContentFetcher(config)

            assert fetcher.is_available() is True

    @pytest.mark.unit
    def test_is_available_without_openai_client(self):
        """Test availability check without OpenAI client."""
        config = ChirpyConfig()
        fetcher = ContentFetcher(config)

        assert fetcher.is_available() is False

    @pytest.mark.unit
    def test_fetch_article_content_uses_correct_headers(self):
        """Test that content fetching uses appropriate browser headers."""
        config = ChirpyConfig(fetch_timeout=20)
        fetcher = ContentFetcher(config)

        mock_response = Mock()
        mock_response.content = b"<html><body><p>Content</p></body></html>"
        mock_response.raise_for_status.return_value = None

        with patch("content_fetcher.requests.get") as mock_get:
            mock_get.return_value = mock_response

            fetcher.fetch_article_content("https://example.com/article")

            # Verify headers and timeout were set correctly
            call_args = mock_get.call_args
            assert call_args[1]["timeout"] == 20

            headers = call_args[1]["headers"]
            assert "User-Agent" in headers
            assert "Mozilla" in headers["User-Agent"]
            assert "Accept" in headers
            assert "Accept-Language" in headers

    @pytest.mark.unit
    def test_summarize_content_uses_config_parameters(self):
        """Test that summarization uses configuration parameters correctly."""
        config = ChirpyConfig(
            openai_api_key="test-key",
            openai_model="gpt-4",
            openai_max_tokens=512,
            openai_temperature=0.7,
        )

        with patch("content_fetcher.openai") as mock_openai_module:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Summary"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_module.OpenAI.return_value = mock_client

            fetcher = ContentFetcher(config)
            fetcher.summarize_content("Content", "Title")

            # Verify API call used correct configuration
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]["model"] == "gpt-4"
            assert call_args[1]["max_tokens"] == 512
            assert call_args[1]["temperature"] == 0.7
