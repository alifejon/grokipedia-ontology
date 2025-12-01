"""Tests for the caching module."""

import tempfile
import time
from pathlib import Path

import pytest

from grokipedia_ontology.cache import MemoryCache, DiskCache, ArticleCache
from grokipedia_ontology.models import Article, Concept, ConceptType


class TestMemoryCache:
    """Tests for MemoryCache."""

    def test_basic_operations(self) -> None:
        """Test basic get/set/delete operations."""
        cache = MemoryCache()

        # Set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Delete
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

        # Delete non-existent
        assert cache.delete("nonexistent") is False

    def test_expiration(self) -> None:
        """Test TTL expiration."""
        cache = MemoryCache(default_ttl=0.1)  # 100ms

        cache.set("key", "value")
        assert cache.get("key") == "value"

        # Wait for expiration
        time.sleep(0.15)
        assert cache.get("key") is None

    def test_lru_eviction(self) -> None:
        """Test LRU eviction when at capacity."""
        cache = MemoryCache(max_size=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        # Access 'a' to make it recently used
        cache.get("a")

        # Add new item - should evict 'b' (LRU)
        cache.set("d", 4)

        assert cache.get("a") == 1  # Still there
        assert cache.get("b") is None  # Evicted
        assert cache.get("c") == 3  # Still there
        assert cache.get("d") == 4  # New item

    def test_stats(self) -> None:
        """Test cache statistics."""
        cache = MemoryCache(max_size=10)

        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        stats = cache.stats
        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_contains(self) -> None:
        """Test __contains__ method."""
        cache = MemoryCache()
        cache.set("key", "value")

        assert "key" in cache
        assert "nonexistent" not in cache

    def test_clear(self) -> None:
        """Test clearing the cache."""
        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()
        assert len(cache) == 0
        assert cache.get("key1") is None


class TestDiskCache:
    """Tests for DiskCache."""

    def test_basic_operations(self) -> None:
        """Test basic get/set/delete with disk persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DiskCache(cache_dir=tmpdir)

            # Set and get
            cache.set("key1", {"data": "value1"})
            result = cache.get("key1")
            assert result == {"data": "value1"}

            # Delete
            assert cache.delete("key1") is True
            assert cache.get("key1") is None

    def test_article_serialization(self) -> None:
        """Test Article serialization/deserialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DiskCache(cache_dir=tmpdir)

            article = Article(
                title="Test Article",
                url="https://grokipedia.com/page/Test",
                slug="Test",
                content="Test content",
                summary="Test summary",
            )

            cache.set("article:test", article)
            loaded = cache.get("article:test")

            assert isinstance(loaded, Article)
            assert loaded.title == "Test Article"
            assert loaded.summary == "Test summary"

    def test_concept_serialization(self) -> None:
        """Test Concept serialization/deserialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DiskCache(cache_dir=tmpdir)

            concept = Concept(
                name="Test_Concept",
                label="Test Concept",
                description="A test concept",
                concept_type=ConceptType.ENTITY,
            )

            cache.set("concept:test", concept)
            loaded = cache.get("concept:test")

            assert isinstance(loaded, Concept)
            assert loaded.name == "Test_Concept"
            assert loaded.concept_type == ConceptType.ENTITY

    def test_expiration(self) -> None:
        """Test TTL expiration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DiskCache(cache_dir=tmpdir, default_ttl=0.1)

            cache.set("key", "value")
            assert cache.get("key") == "value"

            time.sleep(0.15)
            assert cache.get("key") is None

    def test_cleanup_expired(self) -> None:
        """Test cleanup of expired entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DiskCache(cache_dir=tmpdir, default_ttl=0.1)

            cache.set("key1", "value1")
            cache.set("key2", "value2", ttl=1000)  # Long TTL

            time.sleep(0.15)
            removed = cache.cleanup_expired()

            assert removed == 1
            assert cache.get("key1") is None
            assert cache.get("key2") == "value2"

    def test_stats(self) -> None:
        """Test cache statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DiskCache(cache_dir=tmpdir)

            cache.set("key1", "value1")
            cache.get("key1")

            stats = cache.stats
            assert stats["total_entries"] == 1
            assert stats["total_hits"] == 1


class TestArticleCache:
    """Tests for ArticleCache."""

    def test_two_tier_caching(self) -> None:
        """Test memory and disk caching together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ArticleCache(
                memory_size=10,
                memory_ttl=3600,
                disk_ttl=86400,
                cache_dir=tmpdir,
            )

            article = Article(
                title="Test",
                url="https://grokipedia.com/page/Test",
                slug="Test",
                content="Content",
            )

            cache.set("Test", article)

            # Should be in both memory and disk
            result = cache.get("Test")
            assert result is not None
            assert result.title == "Test"

    def test_memory_miss_disk_hit(self) -> None:
        """Test promotion from disk to memory on disk hit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create cache and add article
            cache1 = ArticleCache(
                memory_size=10,
                cache_dir=tmpdir,
            )
            article = Article(
                title="Test",
                url="https://grokipedia.com/page/Test",
                slug="Test",
            )
            cache1.set("Test", article)

            # Create new cache (empty memory, populated disk)
            cache2 = ArticleCache(
                memory_size=10,
                cache_dir=tmpdir,
            )

            # Should load from disk and promote to memory
            result = cache2.get("Test")
            assert result is not None
            assert result.title == "Test"

    def test_invalidation(self) -> None:
        """Test cache invalidation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ArticleCache(cache_dir=tmpdir)

            article = Article(
                title="Test",
                url="https://grokipedia.com/page/Test",
                slug="Test",
            )
            cache.set("Test", article)
            assert cache.get("Test") is not None

            cache.invalidate("Test")
            assert cache.get("Test") is None

    def test_stats(self) -> None:
        """Test combined statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ArticleCache(cache_dir=tmpdir)

            article = Article(
                title="Test",
                url="https://grokipedia.com/page/Test",
                slug="Test",
            )
            cache.set("Test", article)

            stats = cache.stats
            assert "memory" in stats
            assert "disk" in stats
