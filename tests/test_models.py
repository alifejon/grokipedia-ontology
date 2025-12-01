"""Tests for data models."""

import pytest
from datetime import datetime

from grokipedia_ontology.models import (
    Article,
    Concept,
    Relation,
    ConceptType,
    RelationType,
    OntologyStats,
    SearchResult,
)


class TestArticle:
    """Tests for Article model."""

    def test_article_creation(self) -> None:
        """Test basic article creation."""
        article = Article(
            title="Test Article",
            url="https://grokipedia.com/page/Test_Article",
            slug="Test_Article",
            content="This is test content.",
            summary="Test summary.",
        )

        assert article.title == "Test Article"
        assert article.slug == "Test_Article"
        assert article.content == "This is test content."

    def test_article_concept_name(self) -> None:
        """Test concept name generation from title."""
        article = Article(
            title="Artificial Intelligence (AI)",
            url="https://grokipedia.com/page/AI",
            slug="AI",
        )

        assert article.concept_name == "Artificial_Intelligence_AI"

    def test_article_to_concept(self) -> None:
        """Test conversion from article to concept."""
        article = Article(
            title="Machine Learning",
            url="https://grokipedia.com/page/Machine_Learning",
            slug="Machine_Learning",
            summary="ML is a subset of AI.",
            categories=["Computer Science", "AI"],
            infobox={"type": "Technology"},
        )

        concept = article.to_concept()

        assert concept.name == "Machine_Learning"
        assert concept.label == "Machine Learning"
        assert concept.description == "ML is a subset of AI."
        assert concept.categories == ["Computer Science", "AI"]
        assert concept.properties == {"type": "Technology"}


class TestConcept:
    """Tests for Concept model."""

    def test_concept_creation(self) -> None:
        """Test basic concept creation."""
        concept = Concept(
            name="Test_Concept",
            label="Test Concept",
            description="A test concept.",
            concept_type=ConceptType.ENTITY,
        )

        assert concept.name == "Test_Concept"
        assert concept.label == "Test Concept"
        assert concept.concept_type == ConceptType.ENTITY

    def test_concept_uri(self) -> None:
        """Test URI generation."""
        concept = Concept(
            name="Neural_Network",
            label="Neural Network",
        )

        assert concept.uri == "http://grokipedia.org/ontology#Neural_Network"

    def test_concept_with_aliases(self) -> None:
        """Test concept with aliases."""
        concept = Concept(
            name="AI",
            label="Artificial Intelligence",
            aliases=["AI", "Machine Intelligence"],
        )

        assert len(concept.aliases) == 2
        assert "AI" in concept.aliases


class TestRelation:
    """Tests for Relation model."""

    def test_relation_creation(self) -> None:
        """Test basic relation creation."""
        relation = Relation(
            subject="Deep_Learning",
            predicate=RelationType.IS_A,
            object="Machine_Learning",
        )

        assert relation.subject == "Deep_Learning"
        assert relation.predicate == RelationType.IS_A
        assert relation.object == "Machine_Learning"
        assert relation.confidence == 1.0

    def test_relation_triple(self) -> None:
        """Test triple representation."""
        relation = Relation(
            subject="A",
            predicate=RelationType.RELATED_TO,
            object="B",
        )

        assert relation.triple == ("A", "related_to", "B")

    def test_relation_with_confidence(self) -> None:
        """Test relation with custom confidence."""
        relation = Relation(
            subject="X",
            predicate=RelationType.SUPPORTS,
            object="Y",
            confidence=0.8,
        )

        assert relation.confidence == 0.8


class TestConceptType:
    """Tests for ConceptType enum."""

    def test_all_concept_types(self) -> None:
        """Test all concept types exist."""
        expected_types = [
            "entity", "event", "process", "property", "relation",
            "abstract", "person", "organization", "location",
            "time_period", "work", "technology",
        ]

        for type_name in expected_types:
            assert ConceptType(type_name) is not None


class TestRelationType:
    """Tests for RelationType enum."""

    def test_all_relation_types(self) -> None:
        """Test all relation types exist."""
        expected_types = [
            "is_a", "part_of", "related_to", "instance_of",
            "has_property", "caused_by", "results_in", "used_for",
            "located_in", "occurs_in", "contradicts", "supports",
            "derived_from", "equivalent_to", "see_also",
        ]

        for type_name in expected_types:
            assert RelationType(type_name) is not None


class TestOntologyStats:
    """Tests for OntologyStats model."""

    def test_stats_defaults(self) -> None:
        """Test default stats values."""
        stats = OntologyStats()

        assert stats.total_concepts == 0
        assert stats.total_relations == 0
        assert stats.concepts_by_type == {}
        assert stats.relations_by_type == {}
        assert stats.average_relations_per_concept == 0.0

    def test_stats_with_data(self) -> None:
        """Test stats with data."""
        stats = OntologyStats(
            total_concepts=100,
            total_relations=250,
            concepts_by_type={"entity": 50, "technology": 30},
            relations_by_type={"is_a": 100, "related_to": 150},
            top_connected_concepts=[("AI", 20), ("ML", 15)],
            average_relations_per_concept=2.5,
        )

        assert stats.total_concepts == 100
        assert stats.concepts_by_type["entity"] == 50
        assert stats.average_relations_per_concept == 2.5
