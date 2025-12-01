"""
Grokipedia data fetcher module.

Provides functionality to fetch and parse articles from Grokipedia,
extracting structured data for ontology construction.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any
from urllib.parse import quote, urljoin

import httpx
from bs4 import BeautifulSoup

from grokipedia_ontology.models import Article


class GrokipediaFetcher:
    """Fetches and parses articles from Grokipedia."""

    BASE_URL = "https://grokipedia.com"
    PAGE_URL_TEMPLATE = "https://grokipedia.com/page/{slug}"

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        delay_between_requests: float = 1.0,
    ) -> None:
        """
        Initialize the fetcher.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            delay_between_requests: Delay between consecutive requests (rate limiting)
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay = delay_between_requests
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> GrokipediaFetcher:
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "User-Agent": "GrokipediaOntology/0.1.0 (Research Project)",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _get_client(self) -> httpx.AsyncClient:
        """Get the HTTP client, ensuring it exists."""
        if self._client is None:
            raise RuntimeError(
                "Fetcher must be used as async context manager: async with GrokipediaFetcher()"
            )
        return self._client

    @staticmethod
    def build_url(topic: str) -> str:
        """
        Build a Grokipedia URL for a given topic.

        Args:
            topic: Topic name (spaces will be converted to underscores)

        Returns:
            Full URL to the Grokipedia page
        """
        slug = topic.replace(" ", "_")
        return GrokipediaFetcher.PAGE_URL_TEMPLATE.format(slug=quote(slug, safe="_"))

    @staticmethod
    def extract_slug(url: str) -> str:
        """Extract the page slug from a Grokipedia URL."""
        match = re.search(r"/page/(.+?)(?:\?|#|$)", url)
        return match.group(1) if match else ""

    async def fetch_page(self, topic: str) -> str | None:
        """
        Fetch the raw HTML content of a Grokipedia page.

        Args:
            topic: Topic name to fetch

        Returns:
            HTML content or None if fetch failed
        """
        client = self._get_client()
        url = self.build_url(topic)

        for attempt in range(self.max_retries):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)
            except httpx.RequestError:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)

        return None

    def parse_article(self, html: str, topic: str) -> Article:
        """
        Parse HTML content into an Article object.

        Args:
            html: Raw HTML content
            topic: Original topic name

        Returns:
            Parsed Article object
        """
        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title_elem = soup.find("h1") or soup.find("title")
        title = title_elem.get_text(strip=True) if title_elem else topic

        # Extract main content
        content_elem = soup.find("article") or soup.find("main") or soup.find("div", {"id": "content"})
        content = content_elem.get_text(separator="\n", strip=True) if content_elem else ""

        # Extract summary (first paragraph)
        first_para = soup.find("p")
        summary = first_para.get_text(strip=True) if first_para else content[:500]

        # Extract internal links
        links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "/page/" in href:
                slug = self.extract_slug(href)
                if slug:
                    links.append(slug.replace("_", " "))

        # Extract external links
        external_links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.startswith("http") and "grokipedia.com" not in href:
                external_links.append(href)

        # Extract categories (common patterns)
        categories = []
        cat_elem = soup.find("div", {"class": re.compile(r"categor", re.I)})
        if cat_elem:
            for cat_link in cat_elem.find_all("a"):
                categories.append(cat_link.get_text(strip=True))

        # Extract infobox data
        infobox = self._parse_infobox(soup)

        # Extract sections
        sections = self._parse_sections(soup)

        slug = topic.replace(" ", "_")
        return Article(
            title=title,
            url=self.build_url(topic),  # type: ignore
            slug=slug,
            content=content,
            summary=summary,
            categories=categories,
            links=links,
            external_links=external_links,
            infobox=infobox,
            sections=sections,
        )

    def _parse_infobox(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract infobox data from the page."""
        infobox: dict[str, Any] = {}

        # Look for common infobox patterns
        infobox_elem = soup.find("table", {"class": re.compile(r"infobox", re.I)})
        if not infobox_elem:
            infobox_elem = soup.find("aside", {"class": re.compile(r"infobox|sidebar", re.I)})

        if infobox_elem:
            rows = infobox_elem.find_all("tr")
            for row in rows:
                header = row.find("th")
                data = row.find("td")
                if header and data:
                    key = header.get_text(strip=True).lower().replace(" ", "_")
                    value = data.get_text(strip=True)
                    infobox[key] = value

        return infobox

    def _parse_sections(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        """Extract article sections with headers and content."""
        sections = []

        for header in soup.find_all(["h2", "h3"]):
            section_title = header.get_text(strip=True)
            section_content = []

            # Get content until next header
            for sibling in header.find_next_siblings():
                if sibling.name in ["h2", "h3"]:
                    break
                if sibling.name == "p":
                    section_content.append(sibling.get_text(strip=True))

            if section_content:
                sections.append({
                    "title": section_title,
                    "content": "\n".join(section_content),
                })

        return sections

    async def fetch_article(self, topic: str) -> Article | None:
        """
        Fetch and parse a complete article.

        Args:
            topic: Topic name to fetch

        Returns:
            Parsed Article or None if not found
        """
        html = await self.fetch_page(topic)
        if html is None:
            return None
        return self.parse_article(html, topic)

    async def fetch_multiple(
        self,
        topics: list[str],
        concurrency: int = 5,
    ) -> list[Article]:
        """
        Fetch multiple articles concurrently.

        Args:
            topics: List of topic names
            concurrency: Maximum concurrent requests

        Returns:
            List of successfully fetched articles
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def fetch_with_semaphore(topic: str) -> Article | None:
            async with semaphore:
                result = await self.fetch_article(topic)
                await asyncio.sleep(self.delay)  # Rate limiting
                return result

        results = await asyncio.gather(
            *[fetch_with_semaphore(topic) for topic in topics],
            return_exceptions=True,
        )

        return [r for r in results if isinstance(r, Article)]

    async def discover_related(
        self,
        start_topic: str,
        max_depth: int = 2,
        max_articles: int = 100,
    ) -> list[Article]:
        """
        Discover related articles starting from a topic.

        Performs breadth-first crawling following internal links.

        Args:
            start_topic: Starting topic
            max_depth: Maximum link depth to follow
            max_articles: Maximum articles to collect

        Returns:
            List of discovered articles
        """
        visited: set[str] = set()
        articles: list[Article] = []
        queue: list[tuple[str, int]] = [(start_topic, 0)]

        while queue and len(articles) < max_articles:
            topic, depth = queue.pop(0)

            if topic in visited or depth > max_depth:
                continue

            visited.add(topic)
            article = await self.fetch_article(topic)

            if article:
                articles.append(article)

                # Add linked topics to queue
                if depth < max_depth:
                    for link in article.links[:10]:  # Limit links per page
                        if link not in visited:
                            queue.append((link, depth + 1))

                await asyncio.sleep(self.delay)

        return articles
