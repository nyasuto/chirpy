"""
Content fetching and AI summarization module for Chirpy.

Handles fetching article content from URLs and generating summaries using OpenAI API.
"""

from typing import Any

import requests  # type: ignore
from bs4 import BeautifulSoup  # type: ignore

try:
    import openai  # type: ignore
except ImportError:
    openai = None  # type: ignore

try:
    from langdetect import detect  # type: ignore
except ImportError:
    detect = None  # type: ignore

from config import ChirpyConfig, get_logger


class ContentFetcher:
    """Handles content fetching and AI summarization."""

    def __init__(self, config: ChirpyConfig) -> None:
        """Initialize the content fetcher."""
        self.config = config
        self.logger = get_logger(__name__)
        self.openai_client = None

        if openai and config.openai_api_key:
            try:
                self.openai_client = openai.OpenAI(api_key=config.openai_api_key)
                self.logger.info("OpenAI client initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize OpenAI client: {e}")
        else:
            if not openai:
                self.logger.warning("OpenAI package not available")
            if not config.openai_api_key:
                self.logger.warning("OPENAI_API_KEY not found in configuration")

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
        Fetch article content from URL.

        Args:
            url: Article URL to fetch content from

        Returns:
            Extracted article text or None if failed
        """
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

            # Make request with configured timeout
            response = requests.get(
                url, headers=headers, timeout=self.config.fetch_timeout
            )
            response.raise_for_status()

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

        except requests.RequestException as e:
            self.logger.error(f"HTTP error fetching {url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching content from {url}: {e}")
            return None

    def summarize_content(self, content: str, title: str = "") -> str | None:
        """
        Summarize content using OpenAI API.

        Args:
            content: Article content to summarize
            title: Article title for context

        Returns:
            Generated summary or None if failed
        """
        if not self.openai_client:
            self.logger.error("OpenAI client not available for summarization")
            return None

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

            # Call OpenAI API with configured settings
            response = self.openai_client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant that creates concise, "
                            "accurate summaries of Japanese articles. Your summaries "
                            "should be informative and suitable for audio reading."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.config.openai_max_tokens,
                temperature=self.config.openai_temperature,
            )

            summary = response.choices[0].message.content
            if summary:
                summary = summary.strip()
                self.logger.info(f"AI summary generated: {len(summary)} characters")
                return str(summary)
            else:
                self.logger.error("Empty response from OpenAI")
                return None

        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
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
