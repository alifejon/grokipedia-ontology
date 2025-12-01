"""
Caching module for Grokipedia Ontology.

Provides caching functionality for fetched articles and ontology data
to improve performance and reduce redundant API calls.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar, Generic

from grokipedia_ontology.models import Article, Concept, Relation
from grokipedia_ontology.utils import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """A cached item with metadata."""

    key: str
    value: T
    created_at: float
    expires_at: float | None
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class MemoryCache:
    """
    In-memory LRU cache for fast access.

    Features:
    - LRU eviction when max_size is exceeded
    - Optional TTL for entries
    - Thread-safe operations (for basic use cases)
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float | None = None,
    ) -> None:
        """
        Initialize the memory cache.

        Args:
            max_size: Maximum number of entries to store
            default_ttl: Default time-to-live in seconds (None = no expiry)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: dict[str, CacheEntry[Any]] = {}
        self._access_order: list[str] = []
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """
        Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        if entry.is_expired:
            self.delete(key)
            self._misses += 1
            return None

        # Update LRU order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

        entry.hit_count += 1
        self._hits += 1
        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: float | None = None,
    ) -> None:
        """
        Store a value in the cache.

        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (None = use default)
        """
        # Evict if at capacity
        while len(self._cache) >= self.max_size:
            self._evict_lru()

        effective_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + effective_ttl if effective_ttl else None

        self._cache[key] = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            expires_at=expires_at,
        )

        if key not in self._access_order:
            self._access_order.append(key)

    def delete(self, key: str) -> bool:
        """
        Delete an entry from the cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            if key in self._access_order:
                self._access_order.remove(key)
            return True
        return False

    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._cache.clear()
        self._access_order.clear()
        self._hits = 0
        self._misses = 0

    def _evict_lru(self) -> None:
        """Evict the least recently used entry."""
        if self._access_order:
            lru_key = self._access_order.pop(0)
            if lru_key in self._cache:
                del self._cache[lru_key]

    @property
    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }

    def __len__(self) -> int:
        return len(self._cache)

    def __contains__(self, key: str) -> bool:
        entry = self._cache.get(key)
        return entry is not None and not entry.is_expired


class DiskCache:
    """
    SQLite-based disk cache for persistent storage.

    Features:
    - Persistent storage across sessions
    - Automatic expiration cleanup
    - Support for Article and Concept serialization
    """

    def __init__(
        self,
        cache_dir: str | Path = ".grokipedia_cache",
        db_name: str = "cache.db",
        default_ttl: float = 86400 * 7,  # 7 days
    ) -> None:
        """
        Initialize the disk cache.

        Args:
            cache_dir: Directory to store cache files
            db_name: Name of the SQLite database file
            default_ttl: Default time-to-live in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / db_name
        self.default_ttl = default_ttl
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    value_type TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL,
                    hit_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at ON cache(expires_at)
            """)
            conn.commit()

    def _serialize(self, value: Any) -> tuple[str, str]:
        """Serialize a value for storage."""
        if isinstance(value, Article):
            return json.dumps(value.model_dump(mode="json")), "Article"
        elif isinstance(value, Concept):
            return json.dumps(value.model_dump(mode="json")), "Concept"
        elif isinstance(value, Relation):
            return json.dumps(value.model_dump(mode="json")), "Relation"
        else:
            return json.dumps(value), "json"

    def _deserialize(self, data: str, value_type: str) -> Any:
        """Deserialize a value from storage."""
        parsed = json.loads(data)
        if value_type == "Article":
            return Article(**parsed)
        elif value_type == "Concept":
            return Concept(**parsed)
        elif value_type == "Relation":
            return Relation(**parsed)
        else:
            return parsed

    def get(self, key: str) -> Any | None:
        """
        Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value, value_type, expires_at FROM cache WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            value_data, value_type, expires_at = row

            # Check expiration
            if expires_at and time.time() > expires_at:
                self.delete(key)
                return None

            # Update hit count
            conn.execute(
                "UPDATE cache SET hit_count = hit_count + 1 WHERE key = ?",
                (key,)
            )
            conn.commit()

            return self._deserialize(value_data, value_type)

    def set(
        self,
        key: str,
        value: Any,
        ttl: float | None = None,
    ) -> None:
        """
        Store a value in the cache.

        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (None = use default)
        """
        value_data, value_type = self._serialize(value)
        effective_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + effective_ttl if effective_ttl else None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache (key, value, value_type, created_at, expires_at, hit_count)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (key, value_data, value_type, time.time(), expires_at))
            conn.commit()

    def delete(self, key: str) -> bool:
        """
        Delete an entry from the cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()
            return cursor.rowcount > 0

    def clear(self) -> None:
        """Clear all entries from the cache."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache")
            conn.commit()

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM cache WHERE expires_at IS NOT NULL AND expires_at < ?",
                (time.time(),)
            )
            conn.commit()
            removed = cursor.rowcount
            if removed > 0:
                logger.info(f"Cleaned up {removed} expired cache entries")
            return removed

    @property
    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*), SUM(hit_count),
                       COUNT(CASE WHEN expires_at IS NOT NULL AND expires_at < ? THEN 1 END)
                FROM cache
            """, (time.time(),))
            row = cursor.fetchone()
            total_entries, total_hits, expired_entries = row

            return {
                "total_entries": total_entries or 0,
                "total_hits": total_hits or 0,
                "expired_entries": expired_entries or 0,
                "db_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
            }

    def __len__(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM cache")
            return cursor.fetchone()[0]


class ArticleCache:
    """
    Specialized cache for Grokipedia articles.

    Combines memory and disk caching for optimal performance.
    """

    def __init__(
        self,
        memory_size: int = 100,
        memory_ttl: float = 3600,  # 1 hour
        disk_ttl: float = 86400 * 7,  # 7 days
        cache_dir: str | Path = ".grokipedia_cache",
    ) -> None:
        """
        Initialize the article cache.

        Args:
            memory_size: Maximum articles in memory
            memory_ttl: Memory cache TTL in seconds
            disk_ttl: Disk cache TTL in seconds
            cache_dir: Directory for disk cache
        """
        self.memory = MemoryCache(max_size=memory_size, default_ttl=memory_ttl)
        self.disk = DiskCache(cache_dir=cache_dir, default_ttl=disk_ttl)

    @staticmethod
    def _make_key(topic: str) -> str:
        """Create a cache key from a topic name."""
        normalized = topic.lower().replace(" ", "_")
        return f"article:{hashlib.md5(normalized.encode()).hexdigest()}"

    def get(self, topic: str) -> Article | None:
        """
        Get an article from cache.

        Args:
            topic: Article topic name

        Returns:
            Cached Article or None
        """
        key = self._make_key(topic)

        # Try memory first
        article = self.memory.get(key)
        if article is not None:
            return article

        # Try disk
        article = self.disk.get(key)
        if article is not None:
            # Promote to memory cache
            self.memory.set(key, article)
            return article

        return None

    def set(self, topic: str, article: Article) -> None:
        """
        Store an article in cache.

        Args:
            topic: Article topic name
            article: Article to cache
        """
        key = self._make_key(topic)
        self.memory.set(key, article)
        self.disk.set(key, article)

    def invalidate(self, topic: str) -> None:
        """
        Remove an article from cache.

        Args:
            topic: Article topic name
        """
        key = self._make_key(topic)
        self.memory.delete(key)
        self.disk.delete(key)

    def clear(self) -> None:
        """Clear all cached articles."""
        self.memory.clear()
        self.disk.clear()

    @property
    def stats(self) -> dict[str, Any]:
        """Get combined cache statistics."""
        return {
            "memory": self.memory.stats,
            "disk": self.disk.stats,
        }


class CachedFetcher:
    """
    Wrapper around GrokipediaFetcher with caching support.

    Usage:
        async with CachedFetcher() as fetcher:
            article = await fetcher.fetch_article("Python")
    """

    def __init__(
        self,
        cache: ArticleCache | None = None,
        **fetcher_kwargs: Any,
    ) -> None:
        """
        Initialize the cached fetcher.

        Args:
            cache: ArticleCache instance (creates new if None)
            **fetcher_kwargs: Arguments passed to GrokipediaFetcher
        """
        from grokipedia_ontology.fetcher import GrokipediaFetcher
        self.cache = cache or ArticleCache()
        self._fetcher = GrokipediaFetcher(**fetcher_kwargs)

    async def __aenter__(self) -> CachedFetcher:
        await self._fetcher.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._fetcher.__aexit__(*args)

    async def fetch_article(
        self,
        topic: str,
        force_refresh: bool = False,
    ) -> Article | None:
        """
        Fetch an article with caching.

        Args:
            topic: Topic name to fetch
            force_refresh: If True, bypass cache and fetch fresh

        Returns:
            Article or None if not found
        """
        if not force_refresh:
            cached = self.cache.get(topic)
            if cached is not None:
                logger.debug(f"Cache hit for: {topic}")
                return cached

        logger.debug(f"Cache miss for: {topic}, fetching...")
        article = await self._fetcher.fetch_article(topic)

        if article is not None:
            self.cache.set(topic, article)

        return article

    async def fetch_multiple(
        self,
        topics: list[str],
        concurrency: int = 5,
        force_refresh: bool = False,
    ) -> list[Article]:
        """
        Fetch multiple articles with caching.

        Args:
            topics: List of topic names
            concurrency: Maximum concurrent requests (for cache misses)
            force_refresh: If True, bypass cache for all

        Returns:
            List of successfully fetched articles
        """
        results: list[Article] = []
        to_fetch: list[str] = []

        # Check cache first
        for topic in topics:
            if not force_refresh:
                cached = self.cache.get(topic)
                if cached is not None:
                    results.append(cached)
                    continue
            to_fetch.append(topic)

        # Fetch missing articles
        if to_fetch:
            fetched = await self._fetcher.fetch_multiple(to_fetch, concurrency)
            for article in fetched:
                self.cache.set(article.title, article)
            results.extend(fetched)

        return results

    def cleanup(self) -> None:
        """Clean up expired cache entries."""
        self.disk.cleanup_expired()

    @property
    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return self.cache.stats
