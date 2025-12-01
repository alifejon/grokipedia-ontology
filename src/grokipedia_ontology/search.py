"""
Search indexing module for Grokipedia Ontology.

Provides full-text search capabilities with TF-IDF ranking
and support for fuzzy matching.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from grokipedia_ontology.models import Concept, Article, ConceptType
from grokipedia_ontology.utils import get_logger

logger = get_logger(__name__)


@dataclass
class SearchHit:
    """A search result with scoring information."""

    concept_name: str
    label: str
    description: str
    concept_type: str
    score: float
    matched_terms: list[str] = field(default_factory=list)
    matched_fields: list[str] = field(default_factory=list)
    highlights: dict[str, str] = field(default_factory=dict)


class TextProcessor:
    """Text preprocessing utilities for search indexing."""

    # Common English stop words
    STOP_WORDS = frozenset([
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
        "to", "was", "were", "will", "with", "the", "this", "but", "they",
        "have", "had", "what", "when", "where", "who", "which", "why", "how"
    ])

    @classmethod
    def tokenize(cls, text: str) -> list[str]:
        """
        Tokenize text into words.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        if not text:
            return []
        # Convert to lowercase and split on non-alphanumeric
        text = text.lower()
        tokens = re.findall(r"\b[a-z0-9]+\b", text)
        return tokens

    @classmethod
    def normalize(cls, text: str, remove_stopwords: bool = True) -> list[str]:
        """
        Normalize text: tokenize and optionally remove stop words.

        Args:
            text: Input text
            remove_stopwords: Whether to remove stop words

        Returns:
            List of normalized tokens
        """
        tokens = cls.tokenize(text)
        if remove_stopwords:
            tokens = [t for t in tokens if t not in cls.STOP_WORDS]
        return tokens

    @classmethod
    def stem(cls, word: str) -> str:
        """
        Simple suffix-stripping stemmer.

        Args:
            word: Input word

        Returns:
            Stemmed word
        """
        # Simple suffix removal rules
        suffixes = ["ing", "ed", "ly", "tion", "ness", "ment", "able", "ible", "ful", "less"]
        for suffix in suffixes:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                return word[:-len(suffix)]
        if word.endswith("s") and len(word) > 3:
            return word[:-1]
        return word

    @classmethod
    def ngrams(cls, text: str, n: int = 3) -> list[str]:
        """
        Generate character n-grams for fuzzy matching.

        Args:
            text: Input text
            n: N-gram size

        Returns:
            List of n-grams
        """
        text = text.lower()
        if len(text) < n:
            return [text]
        return [text[i:i+n] for i in range(len(text) - n + 1)]


class InvertedIndex:
    """
    Inverted index for efficient full-text search.

    Supports TF-IDF scoring and field-specific searching.
    """

    def __init__(self) -> None:
        """Initialize the inverted index."""
        # term -> {doc_id: {field: [positions]}}
        self._index: dict[str, dict[str, dict[str, list[int]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        # doc_id -> {field: term_count}
        self._doc_lengths: dict[str, dict[str, int]] = defaultdict(dict)
        # doc_id -> document data
        self._documents: dict[str, dict[str, Any]] = {}
        # Total documents
        self._doc_count = 0
        # Average document length per field
        self._avg_lengths: dict[str, float] = {}

    def add_document(
        self,
        doc_id: str,
        fields: dict[str, str],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add a document to the index.

        Args:
            doc_id: Unique document identifier
            fields: Dictionary of field_name -> text content
            metadata: Optional metadata to store with document
        """
        self._documents[doc_id] = {
            "fields": fields,
            "metadata": metadata or {},
        }

        for field_name, text in fields.items():
            tokens = TextProcessor.normalize(text)
            self._doc_lengths[doc_id][field_name] = len(tokens)

            for position, token in enumerate(tokens):
                # Index both original and stemmed forms
                self._index[token][doc_id][field_name].append(position)
                stemmed = TextProcessor.stem(token)
                if stemmed != token:
                    self._index[stemmed][doc_id][field_name].append(position)

        self._doc_count += 1
        self._update_avg_lengths()

    def _update_avg_lengths(self) -> None:
        """Update average document lengths."""
        field_totals: dict[str, int] = defaultdict(int)
        field_counts: dict[str, int] = defaultdict(int)

        for doc_lengths in self._doc_lengths.values():
            for field, length in doc_lengths.items():
                field_totals[field] += length
                field_counts[field] += 1

        self._avg_lengths = {
            field: field_totals[field] / field_counts[field]
            for field in field_totals
            if field_counts[field] > 0
        }

    def search(
        self,
        query: str,
        fields: list[str] | None = None,
        limit: int = 10,
        field_weights: dict[str, float] | None = None,
    ) -> list[tuple[str, float, list[str]]]:
        """
        Search the index using TF-IDF scoring.

        Args:
            query: Search query
            fields: Fields to search (None = all)
            limit: Maximum results
            field_weights: Weights for different fields

        Returns:
            List of (doc_id, score, matched_terms) tuples
        """
        query_tokens = TextProcessor.normalize(query)
        if not query_tokens:
            return []

        # Default field weights
        weights = field_weights or {"label": 2.0, "description": 1.0, "name": 1.5}

        # Calculate scores
        scores: dict[str, float] = defaultdict(float)
        matched_terms: dict[str, set[str]] = defaultdict(set)

        for token in query_tokens:
            # Also search stemmed form
            search_tokens = [token, TextProcessor.stem(token)]

            for search_token in search_tokens:
                if search_token not in self._index:
                    continue

                # IDF: log(N / df)
                df = len(self._index[search_token])
                idf = math.log((self._doc_count + 1) / (df + 1)) + 1

                for doc_id, field_positions in self._index[search_token].items():
                    for field_name, positions in field_positions.items():
                        if fields and field_name not in fields:
                            continue

                        # TF: term frequency in this field
                        tf = len(positions)
                        doc_length = self._doc_lengths[doc_id].get(field_name, 1)
                        avg_length = self._avg_lengths.get(field_name, doc_length)

                        # BM25-style normalization
                        k1 = 1.2
                        b = 0.75
                        normalized_tf = (tf * (k1 + 1)) / (
                            tf + k1 * (1 - b + b * doc_length / max(avg_length, 1))
                        )

                        # Apply field weight
                        weight = weights.get(field_name, 1.0)
                        scores[doc_id] += normalized_tf * idf * weight
                        matched_terms[doc_id].add(token)

        # Sort by score
        results = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        return [
            (doc_id, score, list(matched_terms[doc_id]))
            for doc_id, score in results
        ]

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        """Get document data by ID."""
        return self._documents.get(doc_id)

    def remove_document(self, doc_id: str) -> bool:
        """
        Remove a document from the index.

        Args:
            doc_id: Document ID to remove

        Returns:
            True if removed, False if not found
        """
        if doc_id not in self._documents:
            return False

        # Remove from index
        empty_terms = []
        for term, doc_dict in self._index.items():
            if doc_id in doc_dict:
                del doc_dict[doc_id]
                if not doc_dict:
                    empty_terms.append(term)

        for term in empty_terms:
            del self._index[term]

        # Remove document data
        del self._documents[doc_id]
        if doc_id in self._doc_lengths:
            del self._doc_lengths[doc_id]

        self._doc_count -= 1
        self._update_avg_lengths()
        return True

    def clear(self) -> None:
        """Clear the entire index."""
        self._index.clear()
        self._doc_lengths.clear()
        self._documents.clear()
        self._doc_count = 0
        self._avg_lengths.clear()

    @property
    def stats(self) -> dict[str, Any]:
        """Get index statistics."""
        return {
            "document_count": self._doc_count,
            "term_count": len(self._index),
            "avg_doc_lengths": self._avg_lengths,
        }


class SearchIndex:
    """
    High-level search index for the knowledge graph.

    Provides:
    - Concept indexing and search
    - Persistence to disk
    - Fuzzy matching support
    """

    def __init__(
        self,
        index_path: str | Path | None = None,
    ) -> None:
        """
        Initialize the search index.

        Args:
            index_path: Path to persist index (None = memory only)
        """
        self.index_path = Path(index_path) if index_path else None
        self._index = InvertedIndex()
        self._concept_data: dict[str, dict[str, Any]] = {}

        if self.index_path and self.index_path.exists():
            self.load()

    def index_concept(self, concept: Concept) -> None:
        """
        Add a concept to the search index.

        Args:
            concept: Concept to index
        """
        fields = {
            "name": concept.name.replace("_", " "),
            "label": concept.label,
            "description": concept.description,
            "categories": " ".join(concept.categories),
            "aliases": " ".join(concept.aliases),
        }

        metadata = {
            "concept_type": concept.concept_type.value,
            "source_url": str(concept.source_url) if concept.source_url else None,
        }

        self._index.add_document(concept.name, fields, metadata)
        self._concept_data[concept.name] = {
            "label": concept.label,
            "description": concept.description,
            "concept_type": concept.concept_type.value,
        }

    def index_article(self, article: Article) -> None:
        """
        Index an article (converted to concept).

        Args:
            article: Article to index
        """
        concept = article.to_concept()
        self.index_concept(concept)

    def index_graph(self, graph: Any) -> int:
        """
        Index all concepts from a knowledge graph.

        Args:
            graph: KnowledgeGraph instance

        Returns:
            Number of concepts indexed
        """
        count = 0
        for concept in graph.iterate_concepts():
            self.index_concept(concept)
            count += 1
        logger.info(f"Indexed {count} concepts")
        return count

    def search(
        self,
        query: str,
        limit: int = 10,
        concept_type: ConceptType | None = None,
        min_score: float = 0.0,
    ) -> list[SearchHit]:
        """
        Search for concepts.

        Args:
            query: Search query
            limit: Maximum results
            concept_type: Filter by concept type
            min_score: Minimum score threshold

        Returns:
            List of SearchHit results
        """
        # Get initial results
        raw_results = self._index.search(query, limit=limit * 2)

        hits: list[SearchHit] = []
        for doc_id, score, matched_terms in raw_results:
            if score < min_score:
                continue

            doc = self._index.get_document(doc_id)
            concept_data = self._concept_data.get(doc_id, {})

            # Apply concept type filter
            doc_type = concept_data.get("concept_type", "entity")
            if concept_type and doc_type != concept_type.value:
                continue

            # Build highlights
            highlights = self._build_highlights(doc, matched_terms)

            hit = SearchHit(
                concept_name=doc_id,
                label=concept_data.get("label", doc_id),
                description=concept_data.get("description", ""),
                concept_type=doc_type,
                score=score,
                matched_terms=matched_terms,
                matched_fields=list(highlights.keys()),
                highlights=highlights,
            )
            hits.append(hit)

            if len(hits) >= limit:
                break

        return hits

    def _build_highlights(
        self,
        doc: dict[str, Any] | None,
        matched_terms: list[str],
    ) -> dict[str, str]:
        """Build highlighted snippets for matched fields."""
        if not doc:
            return {}

        highlights: dict[str, str] = {}
        fields = doc.get("fields", {})

        for field_name, text in fields.items():
            if not text:
                continue

            # Check if any matched term is in this field
            text_lower = text.lower()
            for term in matched_terms:
                if term in text_lower:
                    # Create highlighted snippet
                    start = max(0, text_lower.find(term) - 30)
                    end = min(len(text), start + 100)
                    snippet = text[start:end]
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(text):
                        snippet = snippet + "..."
                    highlights[field_name] = snippet
                    break

        return highlights

    def suggest(
        self,
        prefix: str,
        limit: int = 10,
    ) -> list[str]:
        """
        Get autocomplete suggestions.

        Args:
            prefix: Input prefix
            limit: Maximum suggestions

        Returns:
            List of suggested labels
        """
        prefix_lower = prefix.lower()
        suggestions: list[tuple[str, str]] = []

        for name, data in self._concept_data.items():
            label = data.get("label", name)
            if label.lower().startswith(prefix_lower):
                suggestions.append((label, name))
            elif name.lower().startswith(prefix_lower):
                suggestions.append((label, name))

        # Sort by label and limit
        suggestions.sort(key=lambda x: x[0].lower())
        return [label for label, _ in suggestions[:limit]]

    def save(self, path: str | Path | None = None) -> None:
        """
        Save index to disk.

        Args:
            path: File path (uses self.index_path if None)
        """
        save_path = Path(path) if path else self.index_path
        if not save_path:
            raise ValueError("No save path specified")

        save_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "concept_data": self._concept_data,
            "documents": self._index._documents,
            "doc_lengths": dict(self._index._doc_lengths),
            "doc_count": self._index._doc_count,
            "index": {
                term: {
                    doc_id: dict(field_pos)
                    for doc_id, field_pos in doc_dict.items()
                }
                for term, doc_dict in self._index._index.items()
            },
        }

        save_path.write_text(json.dumps(data, default=str))
        logger.info(f"Saved search index to: {save_path}")

    def load(self, path: str | Path | None = None) -> None:
        """
        Load index from disk.

        Args:
            path: File path (uses self.index_path if None)
        """
        load_path = Path(path) if path else self.index_path
        if not load_path or not load_path.exists():
            return

        data = json.loads(load_path.read_text())

        self._concept_data = data.get("concept_data", {})
        self._index._documents = data.get("documents", {})
        self._index._doc_lengths = defaultdict(dict, data.get("doc_lengths", {}))
        self._index._doc_count = data.get("doc_count", 0)

        # Rebuild inverted index structure
        raw_index = data.get("index", {})
        self._index._index = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        for term, doc_dict in raw_index.items():
            for doc_id, field_pos in doc_dict.items():
                for field, positions in field_pos.items():
                    self._index._index[term][doc_id][field] = positions

        self._index._update_avg_lengths()
        logger.info(f"Loaded search index from: {load_path}")

    def clear(self) -> None:
        """Clear the index."""
        self._index.clear()
        self._concept_data.clear()

    @property
    def stats(self) -> dict[str, Any]:
        """Get index statistics."""
        return {
            **self._index.stats,
            "indexed_concepts": len(self._concept_data),
        }

    def __len__(self) -> int:
        return len(self._concept_data)
