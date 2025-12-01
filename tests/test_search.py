"""Tests for the search indexing module."""

import tempfile
from pathlib import Path

import pytest

from grokipedia_ontology.search import (
    TextProcessor,
    InvertedIndex,
    SearchIndex,
    SearchHit,
)
from grokipedia_ontology.models import Concept, ConceptType


class TestTextProcessor:
    """Tests for TextProcessor."""

    def test_tokenize(self) -> None:
        """Test tokenization."""
        tokens = TextProcessor.tokenize("Hello, World! This is a test 123.")
        assert tokens == ["hello", "world", "this", "is", "a", "test", "123"]

    def test_tokenize_empty(self) -> None:
        """Test tokenization of empty string."""
        assert TextProcessor.tokenize("") == []
        assert TextProcessor.tokenize(None) == []  # type: ignore

    def test_normalize_with_stopwords(self) -> None:
        """Test normalization with stop word removal."""
        tokens = TextProcessor.normalize("This is a test of the system")
        assert "this" not in tokens
        assert "is" not in tokens
        assert "a" not in tokens
        assert "test" in tokens
        assert "system" in tokens

    def test_normalize_without_stopwords(self) -> None:
        """Test normalization without stop word removal."""
        tokens = TextProcessor.normalize("This is a test", remove_stopwords=False)
        assert "this" in tokens
        assert "is" in tokens
        assert "a" in tokens

    def test_stem(self) -> None:
        """Test stemming."""
        assert TextProcessor.stem("running") == "runn"
        assert TextProcessor.stem("tested") == "test"
        assert TextProcessor.stem("quickly") == "quick"
        assert TextProcessor.stem("cats") == "cat"
        assert TextProcessor.stem("cat") == "cat"  # Too short to stem

    def test_ngrams(self) -> None:
        """Test n-gram generation."""
        ngrams = TextProcessor.ngrams("hello", 3)
        assert ngrams == ["hel", "ell", "llo"]

        # Short text
        ngrams = TextProcessor.ngrams("hi", 3)
        assert ngrams == ["hi"]


class TestInvertedIndex:
    """Tests for InvertedIndex."""

    def test_add_and_search(self) -> None:
        """Test adding documents and searching."""
        index = InvertedIndex()

        index.add_document("doc1", {"title": "Python Programming", "body": "Learn Python basics"})
        index.add_document("doc2", {"title": "Java Development", "body": "Learn Java programming"})
        index.add_document("doc3", {"title": "Advanced Python", "body": "Python frameworks"})

        results = index.search("python")
        assert len(results) >= 2
        # Python docs should be ranked higher
        doc_ids = [r[0] for r in results]
        assert "doc1" in doc_ids or "doc3" in doc_ids

    def test_field_specific_search(self) -> None:
        """Test searching in specific fields."""
        index = InvertedIndex()

        index.add_document("doc1", {"title": "Python Guide", "body": "Java code examples"})
        index.add_document("doc2", {"title": "Java Guide", "body": "Python code examples"})

        # Search only in title
        results = index.search("python", fields=["title"])
        assert len(results) == 1
        assert results[0][0] == "doc1"

    def test_field_weights(self) -> None:
        """Test field weighting in search."""
        index = InvertedIndex()

        index.add_document("doc1", {"title": "Python", "body": "General programming"})
        index.add_document("doc2", {"title": "Guide", "body": "Python Python Python"})

        # With high title weight, doc1 should rank higher
        results = index.search("python", field_weights={"title": 10.0, "body": 1.0})
        assert results[0][0] == "doc1"

    def test_get_document(self) -> None:
        """Test document retrieval."""
        index = InvertedIndex()

        index.add_document("doc1", {"title": "Test"}, {"meta": "data"})

        doc = index.get_document("doc1")
        assert doc is not None
        assert doc["fields"]["title"] == "Test"
        assert doc["metadata"]["meta"] == "data"

        assert index.get_document("nonexistent") is None

    def test_remove_document(self) -> None:
        """Test document removal."""
        index = InvertedIndex()

        index.add_document("doc1", {"title": "Python"})
        index.add_document("doc2", {"title": "Java"})

        assert index.remove_document("doc1") is True
        assert index.remove_document("doc1") is False  # Already removed

        results = index.search("python")
        assert len(results) == 0

    def test_stats(self) -> None:
        """Test index statistics."""
        index = InvertedIndex()

        index.add_document("doc1", {"title": "Test Document"})
        index.add_document("doc2", {"title": "Another Test"})

        stats = index.stats
        assert stats["document_count"] == 2
        assert stats["term_count"] > 0


class TestSearchIndex:
    """Tests for SearchIndex."""

    def test_index_concept(self) -> None:
        """Test concept indexing."""
        index = SearchIndex()

        concept = Concept(
            name="Machine_Learning",
            label="Machine Learning",
            description="A field of artificial intelligence",
            concept_type=ConceptType.TECHNOLOGY,
            categories=["AI", "Computer Science"],
            aliases=["ML"],
        )

        index.index_concept(concept)

        results = index.search("machine learning")
        assert len(results) > 0
        assert results[0].concept_name == "Machine_Learning"

    def test_search_with_type_filter(self) -> None:
        """Test searching with concept type filter."""
        index = SearchIndex()

        index.index_concept(Concept(
            name="Python",
            label="Python",
            description="A programming language",
            concept_type=ConceptType.TECHNOLOGY,
        ))
        index.index_concept(Concept(
            name="Guido",
            label="Guido van Rossum",
            description="Python creator",
            concept_type=ConceptType.PERSON,
        ))

        # Filter by TECHNOLOGY
        results = index.search("python", concept_type=ConceptType.TECHNOLOGY)
        assert len(results) == 1
        assert results[0].concept_name == "Python"

    def test_search_highlights(self) -> None:
        """Test search result highlights."""
        index = SearchIndex()

        index.index_concept(Concept(
            name="AI",
            label="Artificial Intelligence",
            description="The simulation of human intelligence by machines",
        ))

        results = index.search("intelligence")
        assert len(results) > 0
        assert len(results[0].highlights) > 0

    def test_suggest(self) -> None:
        """Test autocomplete suggestions."""
        index = SearchIndex()

        index.index_concept(Concept(name="Python", label="Python"))
        index.index_concept(Concept(name="PyTorch", label="PyTorch"))
        index.index_concept(Concept(name="Java", label="Java"))

        suggestions = index.suggest("Py")
        assert "Python" in suggestions
        assert "PyTorch" in suggestions
        assert "Java" not in suggestions

    def test_persistence(self) -> None:
        """Test index save and load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "index.json"

            # Create and save index
            index1 = SearchIndex(index_path=index_path)
            index1.index_concept(Concept(
                name="Test",
                label="Test Concept",
                description="A test concept for persistence",
            ))
            index1.save()

            # Load in new index
            index2 = SearchIndex(index_path=index_path)

            results = index2.search("test")
            assert len(results) > 0
            assert results[0].concept_name == "Test"

    def test_clear(self) -> None:
        """Test clearing the index."""
        index = SearchIndex()

        index.index_concept(Concept(name="Test", label="Test"))
        assert len(index) == 1

        index.clear()
        assert len(index) == 0

    def test_stats(self) -> None:
        """Test index statistics."""
        index = SearchIndex()

        index.index_concept(Concept(name="A", label="A"))
        index.index_concept(Concept(name="B", label="B"))

        stats = index.stats
        assert stats["indexed_concepts"] == 2
        assert stats["document_count"] == 2

    def test_search_min_score(self) -> None:
        """Test minimum score threshold."""
        index = SearchIndex()

        index.index_concept(Concept(
            name="Exact_Match",
            label="Exact Match Query",
            description="This matches the query exactly",
        ))
        index.index_concept(Concept(
            name="Partial",
            label="Partial",
            description="Only slight relation",
        ))

        # High min_score should filter weak matches
        results = index.search("exact match query", min_score=0.5)
        # Should return fewer results than without filter
        assert all(r.score >= 0.5 for r in results)
