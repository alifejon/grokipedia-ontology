"""Tests for ontology module."""

import pytest
from pathlib import Path
import tempfile

from grokipedia_ontology.ontology import GrokipediaOntology
from grokipedia_ontology.models import Concept, Relation, ConceptType, RelationType


class TestGrokipediaOntology:
    """Tests for GrokipediaOntology class."""

    def test_ontology_creation(self) -> None:
        """Test basic ontology creation."""
        ontology = GrokipediaOntology()

        assert ontology.base_uri == "http://grokipedia.org/ontology"
        assert ontology.graph is not None

    def test_add_concept(self) -> None:
        """Test adding a concept."""
        ontology = GrokipediaOntology()

        concept = Concept(
            name="Test_Concept",
            label="Test Concept",
            description="A test concept for testing.",
            concept_type=ConceptType.ENTITY,
        )

        uri = ontology.add_concept(concept)

        assert uri is not None
        assert ontology.get_concept("Test_Concept") == concept

    def test_add_relation(self) -> None:
        """Test adding a relation."""
        ontology = GrokipediaOntology()

        # Add concepts first
        ontology.add_concept(Concept(name="A", label="A"))
        ontology.add_concept(Concept(name="B", label="B"))

        relation = Relation(
            subject="A",
            predicate=RelationType.RELATED_TO,
            object="B",
        )

        ontology.add_relation(relation)

        relations = ontology.get_relations(subject="A")
        assert len(relations) == 1
        assert relations[0].object == "B"

    def test_get_relations_filter(self) -> None:
        """Test filtering relations."""
        ontology = GrokipediaOntology()

        # Add concepts
        for name in ["X", "Y", "Z"]:
            ontology.add_concept(Concept(name=name, label=name))

        # Add relations
        ontology.add_relation(Relation(subject="X", predicate=RelationType.IS_A, object="Y"))
        ontology.add_relation(Relation(subject="X", predicate=RelationType.RELATED_TO, object="Z"))

        # Filter by predicate
        is_a_relations = ontology.get_relations(predicate=RelationType.IS_A)
        assert len(is_a_relations) == 1
        assert is_a_relations[0].object == "Y"

        # Filter by subject
        x_relations = ontology.get_relations(subject="X")
        assert len(x_relations) == 2

    def test_serialize_turtle(self) -> None:
        """Test serialization to Turtle format."""
        ontology = GrokipediaOntology()
        ontology.add_concept(Concept(name="Test", label="Test"))

        turtle = ontology.serialize(format="turtle")

        assert "@prefix" in turtle
        assert "Test" in turtle

    def test_serialize_xml(self) -> None:
        """Test serialization to RDF/XML format."""
        ontology = GrokipediaOntology()
        ontology.add_concept(Concept(name="Test", label="Test"))

        xml = ontology.serialize(format="xml")

        assert "rdf:RDF" in xml

    def test_save_and_load(self) -> None:
        """Test saving and loading ontology."""
        ontology = GrokipediaOntology()
        ontology.add_concept(Concept(name="Saved_Concept", label="Saved Concept"))

        with tempfile.NamedTemporaryFile(suffix=".ttl", delete=False) as f:
            path = Path(f.name)

        try:
            ontology.save(path, format="turtle")

            # Load into new ontology
            loaded = GrokipediaOntology()
            loaded.load(path)

            # Verify content was loaded (check triple count)
            original_count = len(list(ontology.graph))
            loaded_count = len(list(loaded.graph))
            assert loaded_count >= original_count
        finally:
            path.unlink()

    def test_sparql_query(self) -> None:
        """Test SPARQL querying."""
        ontology = GrokipediaOntology()
        ontology.add_concept(Concept(name="Query_Test", label="Query Test Label"))

        query = """
        SELECT ?label WHERE {
            ?s rdfs:label ?label .
            FILTER(CONTAINS(?label, "Query"))
        }
        """

        results = ontology.query(query)

        # Should find our label
        labels = [r.get("label", "") for r in results]
        assert any("Query" in label for label in labels)

    def test_get_stats(self) -> None:
        """Test statistics generation."""
        ontology = GrokipediaOntology()

        # Add concepts and relations
        ontology.add_concept(Concept(name="A", label="A", concept_type=ConceptType.ENTITY))
        ontology.add_concept(Concept(name="B", label="B", concept_type=ConceptType.ENTITY))
        ontology.add_concept(Concept(name="C", label="C", concept_type=ConceptType.TECHNOLOGY))

        ontology.add_relation(Relation(subject="A", predicate=RelationType.RELATED_TO, object="B"))
        ontology.add_relation(Relation(subject="B", predicate=RelationType.RELATED_TO, object="C"))

        stats = ontology.get_stats()

        assert stats.total_concepts == 3
        assert stats.total_relations == 2
        assert stats.concepts_by_type.get("entity", 0) == 2
        assert stats.concepts_by_type.get("technology", 0) == 1

    def test_merge_ontologies(self) -> None:
        """Test merging two ontologies."""
        ont1 = GrokipediaOntology()
        ont1.add_concept(Concept(name="From_Ont1", label="From Ont1"))

        ont2 = GrokipediaOntology()
        ont2.add_concept(Concept(name="From_Ont2", label="From Ont2"))

        ont1.merge(ont2)

        assert ont1.get_concept("From_Ont1") is not None
        assert ont1.get_concept("From_Ont2") is not None

    def test_infer_relations(self) -> None:
        """Test relation inference."""
        ontology = GrokipediaOntology()

        # Create IS_A hierarchy: C -> B -> A
        for name in ["A", "B", "C"]:
            ontology.add_concept(Concept(name=name, label=name))

        ontology.add_relation(Relation(subject="B", predicate=RelationType.IS_A, object="A"))
        ontology.add_relation(Relation(subject="C", predicate=RelationType.IS_A, object="B"))

        # Run inference
        inferred = ontology.infer_relations()

        # Should infer C -> A
        c_ancestors = ontology.get_relations(subject="C", predicate=RelationType.IS_A)
        objects = {r.object for r in c_ancestors}

        assert "A" in objects  # Transitive inference
