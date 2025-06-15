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

    def is_available(self) -> bool:
        """Check if content fetching and summarization is available."""
        return self.openai_client is not None
