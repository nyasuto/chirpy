"""
Content fetching and AI summarization module for Chirpy.

Handles fetching article content from URLs and generating summaries using OpenAI API.
"""

import time
from typing import Any

import requests  # type: ignore
from bs4 import BeautifulSoup  # type: ignore
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    import openai  # type: ignore
except ImportError:
    openai = None  # type: ignore

try:
    from langdetect import detect  # type: ignore
except ImportError:
    detect = None  # type: ignore

from config import ChirpyConfig, get_logger
from error_handling import (
    CircuitBreaker,
    ErrorHandler,
    create_retry_decorator,
    get_user_friendly_message,
    is_recoverable_error,
)


class ContentFetcher:
    """Handles content fetching and AI summarization."""

    def __init__(self, config: ChirpyConfig) -> None:
        """Initialize the content fetcher."""
        self.config = config
        self.logger = get_logger(__name__)
        self.openai_client = None

        # Initialize error handling components
        self.error_handler = ErrorHandler("content_fetcher")
        self.openai_circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker_failure_threshold,
            timeout=config.circuit_breaker_timeout,
            name="openai_api",
        )
        self.http_circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker_failure_threshold,
            timeout=config.circuit_breaker_timeout,
            name="http_requests",
        )

        # Create HTTP session with retry strategy
        self.session = self._create_http_session()

        # Create retry decorator for API calls
        self.retry_api_call = create_retry_decorator(
            max_retries=config.max_retries,
            backoff_multiplier=config.retry_backoff_multiplier,
            min_wait=config.retry_min_wait,
            max_wait=config.retry_max_wait,
            retry_on=(openai.APIError, openai.APITimeoutError) if openai else (),
        )

        if openai and config.openai_api_key:
            try:
                self.openai_client = openai.OpenAI(
                    api_key=config.openai_api_key, timeout=config.openai_timeout
                )
                self.logger.info("OpenAI client initialized successfully")
            except Exception as e:
                self.error_handler.handle_error(
                    "openai_client_initialization", e, recoverable=False
                )
        else:
            if not openai:
                self.logger.warning("OpenAI package not available")
            if not config.openai_api_key:
                self.logger.warning("OPENAI_API_KEY not found in configuration")

    def _create_http_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=self.config.retry_backoff_multiplier,
            raise_on_status=False,
        )

        # Mount adapter with retry strategy
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def detect_language(self, text: str) -> str:
        """
        Detect the language of the given text.

        Args:
            text: Text to analyze

        Returns:
            Language code (e.g., 'en', 'ja') or 'unknown' if detection fails
        """
        if not detect:
            self.logger.warning("langdetect library not available")
            return "unknown"

        if not text or len(text.strip()) < 10:
            return "unknown"

        try:
            # Clean text for better detection
            clean_text = " ".join(text.split())[:1000]  # Use first 1000 chars
            detected_lang = detect(clean_text)
            self.logger.debug(f"Detected language: {detected_lang}")
            return str(detected_lang)
        except Exception as e:
            self.logger.warning(f"Language detection failed: {e}")
            return "unknown"

    def fetch_article_content(self, url: str) -> str | None:
        """
        Fetch article content from URL with comprehensive error handling.

        Args:
            url: Article URL to fetch content from

        Returns:
            Extracted article text or None if failed
        """

        def _fetch_with_circuit_breaker() -> str | None:
            """Internal fetch function with error handling."""
            try:
                self.logger.info(f"Fetching content from: {url[:60]}...")

                # Set headers to mimic a real browser
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/91.0.4472.124 Safari/537.36"
                    ),
                    "Accept": (
                        "text/html,application/xhtml+xml,application/xml;"
                        "q=0.9,image/webp,*/*;q=0.8"
                    ),
                    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }

                # Make request with session (includes retry logic)
                response = self.session.get(
                    url, headers=headers, timeout=self.config.request_timeout
                )
                response.raise_for_status()

                return self._extract_content_from_response(response)

            except requests.exceptions.Timeout as e:
                self.error_handler.handle_error(
                    "fetch_article_content_timeout",
                    e,
                    context={"url": url, "timeout": self.config.request_timeout},
                )
                raise
            except requests.exceptions.ConnectionError as e:
                self.error_handler.handle_error(
                    "fetch_article_content_connection", e, context={"url": url}
                )
                raise
            except requests.exceptions.HTTPError as e:
                recoverable = is_recoverable_error(e)
                self.error_handler.handle_error(
                    "fetch_article_content_http",
                    e,
                    recoverable=recoverable,
                    context={
                        "url": url,
                        "status_code": getattr(e.response, "status_code", None),
                    },
                )
                raise
            except Exception as e:
                self.error_handler.handle_error(
                    "fetch_article_content_unexpected",
                    e,
                    recoverable=is_recoverable_error(e),
                    context={"url": url},
                )
                raise

        # Use circuit breaker for HTTP requests
        try:
            return self.http_circuit_breaker.call(_fetch_with_circuit_breaker)
        except Exception as e:
            # Log user-friendly message
            friendly_message = get_user_friendly_message(e, "fetching article content")
            self.logger.error(f"Content fetch failed: {friendly_message}")
            return None

    def _extract_content_from_response(self, response: requests.Response) -> str | None:
        """Extract text content from HTTP response."""
        try:
            # Parse HTML content
            soup = BeautifulSoup(response.content, "html.parser")

            # Remove unwanted elements
            for element in soup.find_all(
                ["script", "style", "nav", "footer", "header"]
            ):
                element.decompose()

            # Try to find main content using common selectors
            content_selectors = [
                "article",
                "[role='main']",
                ".content",
                ".post-content",
                ".entry-content",
                ".article-content",
                ".main-content",
                "#content",
                ".container",
            ]

            content_text = ""
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    content_text = content_element.get_text(strip=True)
                    break

            # Fallback to body if no specific content found
            if not content_text:
                body = soup.find("body")
                if body:
                    content_text = body.get_text(strip=True)

            # Clean up the text
            if content_text:
                # Remove excessive whitespace
                content_text = " ".join(content_text.split())

                # Limit content length to reasonable size for API
                if len(content_text) > 8000:
                    content_text = content_text[:8000] + "..."

                self.logger.info(f"Content fetched: {len(content_text)} characters")
                return content_text
            else:
                self.logger.warning("No content found in HTML")
                return None

        except Exception as e:
            self.logger.error(f"Error parsing HTML content: {e}")
            return None

    def summarize_content(self, content: str, title: str = "") -> str | None:
        """
        Summarize content using OpenAI API with comprehensive error handling.

        Args:
            content: Article content to summarize
            title: Article title for context

        Returns:
            Generated summary or None if failed
        """
        if not self.openai_client:
            self.logger.error("OpenAI client not available for summarization")
            return None

        def _summarize_with_circuit_breaker() -> str | None:
            """Internal summarization function with error handling."""
            try:
                self.logger.info(
                    f"Generating AI summary for content ({len(content)} chars)..."
                )

                # Create prompt for summarization
                prompt = f"""
Please summarize the following article in Japanese. Create a concise but
comprehensive summary that captures the main points and key information.

Title: {title}

Content: {content}

Please provide a summary in 2-3 paragraphs that would be suitable
for text-to-speech reading.
"""

                # Call OpenAI API with configured settings and retry logic
                @self.retry_api_call
                def _make_api_call():
                    return self.openai_client.chat.completions.create(
                        model=self.config.openai_model,
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You are a helpful assistant that creates concise, "
                                    "accurate summaries of Japanese articles. "
                                    "Your summaries should be informative and suitable "
                                    "for audio reading."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=self.config.openai_max_tokens,
                        temperature=self.config.openai_temperature,
                    )

                response = _make_api_call()

                summary = response.choices[0].message.content
                if summary:
                    summary = summary.strip()
                    self.logger.info(f"AI summary generated: {len(summary)} characters")
                    return str(summary)
                else:
                    self.logger.error("Empty response from OpenAI")
                    return None

            except openai.RateLimitError as e:
                self.error_handler.handle_error(
                    "openai_summarize_rate_limit",
                    e,
                    context={"content_length": len(content), "title": title},
                )
                # Add delay for rate limiting
                time.sleep(self.config.rate_limit_delay)
                raise
            except openai.APITimeoutError as e:
                self.error_handler.handle_error(
                    "openai_summarize_timeout",
                    e,
                    context={
                        "content_length": len(content),
                        "timeout": self.config.openai_timeout,
                    },
                )
                raise
            except openai.AuthenticationError as e:
                self.error_handler.handle_error(
                    "openai_summarize_auth", e, recoverable=False
                )
                raise
            except openai.APIError as e:
                recoverable = is_recoverable_error(e)
                self.error_handler.handle_error(
                    "openai_summarize_api",
                    e,
                    recoverable=recoverable,
                    context={"content_length": len(content)},
                )
                raise
            except Exception as e:
                self.error_handler.handle_error(
                    "openai_summarize_unexpected",
                    e,
                    recoverable=is_recoverable_error(e),
                    context={"content_length": len(content)},
                )
                raise

        # Use circuit breaker for OpenAI API calls
        try:
            return self.openai_circuit_breaker.call(_summarize_with_circuit_breaker)
        except Exception as e:
            friendly_message = get_user_friendly_message(e, "generating AI summary")
            self.logger.error(f"Summary generation failed: {friendly_message}")
            return None

    def summarize_and_translate(
        self, content: str, title: str = "", detected_language: str = "unknown"
    ) -> str | None:
        """
        Summarize and optionally translate content based on detected language.

        Args:
            content: Article content to process
            title: Article title for context
            detected_language: Detected language code

        Returns:
            Japanese summary (translated if needed) or None if failed
        """
        if not self.openai_client:
            self.logger.error("OpenAI client not available for translation")
            return None

        try:
            if detected_language == "en":
                # English article - translate and summarize
                self.logger.info("Translating and summarizing English article")
                prompt = f"""
Please translate the following English article to Japanese and create a
comprehensive summary.
The summary should capture all important points and be suitable for
text-to-speech reading.

Title: {title}

Content: {content}

Instructions:
1. First understand the full content of the English article
2. Create a comprehensive Japanese summary that covers all key points
3. Make the summary natural and fluent in Japanese
4. Ensure it's suitable for audio reading (2-3 paragraphs)
"""
                system_message = (
                    "You are a professional translator and summarizer. "
                    "You create accurate Japanese summaries of English articles that "
                    "preserve all important information while being natural and "
                    "readable."
                )
            else:
                # Japanese or other languages - normal summarization
                self.logger.info(f"Summarizing article in {detected_language}")
                prompt = f"""
Please summarize the following article in Japanese. Create a concise but
comprehensive summary that captures the main points and key information.

Title: {title}

Content: {content}

Please provide a summary in 2-3 paragraphs that would be suitable
for text-to-speech reading.
"""
                system_message = (
                    "You are a helpful assistant that creates concise, "
                    "accurate summaries in Japanese. Your summaries "
                    "should be informative and suitable for audio reading."
                )

            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.config.openai_max_tokens,
                temperature=self.config.openai_temperature,
            )

            summary = response.choices[0].message.content
            if summary:
                summary = summary.strip()
                action = (
                    "translated and summarized"
                    if detected_language == "en"
                    else "summarized"
                )
                self.logger.info(f"Article {action}: {len(summary)} characters")
                return str(summary)
            else:
                self.logger.error("Empty response from OpenAI")
                return None

        except Exception as e:
            self.logger.error(f"Error in translation/summarization: {e}")
            return None

    def process_empty_summary_article(self, article: dict[str, Any]) -> str | None:
        """
        Complete workflow: fetch content and generate summary.

        Args:
            article: Article dictionary with id, link, title

        Returns:
            Generated summary or None if failed
        """
        article_id = article.get("id")
        url = article.get("link")
        title = article.get("title", "")

        if not url:
            self.logger.error(f"No URL found for article {article_id}")
            return None

        self.logger.info(f"Processing article {article_id}: {title[:50]}...")

        # Step 1: Fetch content
        content = self.fetch_article_content(url)
        if not content:
            return None

        # Step 2: Generate summary
        summary = self.summarize_content(content, title)
        if not summary:
            return None

        self.logger.info(f"Successfully processed article {article_id}")
        return summary

    def process_article_with_translation(
        self, article: dict[str, Any]
    ) -> tuple[str | None, str, bool]:
        """
        Complete workflow with language detection and translation support.

        Args:
            article: Article dictionary with id, link, title, summary

        Returns:
            Tuple of (translated_summary, detected_language, is_translated)
        """
        article_id = article.get("id")
        title = article.get("title", "")
        existing_summary = article.get("summary", "")

        self.logger.info(
            f"Processing article {article_id} with translation: {title[:50]}..."
        )

        # Use existing summary if available, otherwise fetch content
        if existing_summary and existing_summary not in ("", "No summary available"):
            content = existing_summary
            self.logger.info("Using existing summary for processing")
        else:
            url = article.get("link")
            if not url:
                self.logger.error(f"No URL found for article {article_id}")
                return None, "unknown", False

            content = self.fetch_article_content(url)
            if not content:
                return None, "unknown", False

        # Detect language
        detected_language = self.detect_language(content)
        self.logger.info(f"Detected language: {detected_language}")

        # Process based on configuration and detected language
        if (
            self.config.auto_translate
            and detected_language == "en"
            and self.config.target_language == "ja"
        ):
            # Translate English to Japanese
            summary = self.summarize_and_translate(content, title, detected_language)
            is_translated = True if summary else False
        else:
            # Normal summarization for Japanese or other languages
            summary = self.summarize_content(content, title)
            is_translated = False

        if summary:
            self.logger.info(
                f"Successfully processed article {article_id} "
                f"(language: {detected_language}, translated: {is_translated})"
            )

        return summary, detected_language, is_translated

    def is_available(self) -> bool:
        """Check if content fetching and summarization is available."""
        return self.openai_client is not None
