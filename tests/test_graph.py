"""Tests for knowledge graph module."""

import pytest

from grokipedia_ontology.graph import KnowledgeGraph
from grokipedia_ontology.models import Concept, Relation, ConceptType, RelationType, Article


class TestKnowledgeGraph:
    """Tests for KnowledgeGraph class."""

    def test_graph_creation(self) -> None:
        """Test basic graph creation."""
        graph = KnowledgeGraph()

        assert graph.graph is not None
        assert len(graph) == 0

    def test_add_concept(self) -> None:
        """Test adding a concept."""
        graph = KnowledgeGraph()

        concept = Concept(
            name="Test",
            label="Test",
            concept_type=ConceptType.ENTITY,
        )

        graph.add_concept(concept)

        assert len(graph) == 1
        assert "Test" in graph
        assert graph.get_concept("Test") == concept

    def test_add_relation(self) -> None:
        """Test adding a relation."""
        graph = KnowledgeGraph()

        graph.add_concept(Concept(name="A", label="A"))
        graph.add_concept(Concept(name="B", label="B"))

        relation = Relation(
            subject="A",
            predicate=RelationType.RELATED_TO,
            object="B",
        )

        graph.add_relation(relation)

        # Check edge exists
        assert graph.graph.has_edge("A", "B")

    def test_add_article(self) -> None:
        """Test adding an article."""
        graph = KnowledgeGraph()

        article = Article(
            title="Test Article",
            url="https://grokipedia.com/page/Test",
            slug="Test",
            summary="Test summary",
            links=["Related_Topic"],
        )

        graph.add_article(article)

        assert "Test_Article" in graph
        assert graph.graph.has_edge("Test_Article", "Related_Topic")

    def test_get_neighbors(self) -> None:
        """Test getting neighbors."""
        graph = KnowledgeGraph()

        # Create a simple graph: A -> B -> C
        for name in ["A", "B", "C"]:
            graph.add_concept(Concept(name=name, label=name))

        graph.add_relation(Relation(subject="A", predicate=RelationType.RELATED_TO, object="B"))
        graph.add_relation(Relation(subject="B", predicate=RelationType.RELATED_TO, object="C"))

        # Outgoing neighbors of B
        out_neighbors = graph.get_neighbors("B", direction="out")
        assert "C" in out_neighbors

        # Incoming neighbors of B
        in_neighbors = graph.get_neighbors("B", direction="in")
        assert "A" in in_neighbors

        # Both directions
        all_neighbors = graph.get_neighbors("B", direction="both")
        assert "A" in all_neighbors
        assert "C" in all_neighbors

    def test_find_path(self) -> None:
        """Test path finding."""
        graph = KnowledgeGraph()

        # Create chain: A -> B -> C -> D
        for name in ["A", "B", "C", "D"]:
            graph.add_concept(Concept(name=name, label=name))

        graph.add_relation(Relation(subject="A", predicate=RelationType.RELATED_TO, object="B"))
        graph.add_relation(Relation(subject="B", predicate=RelationType.RELATED_TO, object="C"))
        graph.add_relation(Relation(subject="C", predicate=RelationType.RELATED_TO, object="D"))

        path = graph.find_path("A", "D")

        assert path is not None
        assert path == ["A", "B", "C", "D"]

    def test_find_path_not_exists(self) -> None:
        """Test path finding when no path exists."""
        graph = KnowledgeGraph()

        graph.add_concept(Concept(name="X", label="X"))
        graph.add_concept(Concept(name="Y", label="Y"))
        # No edge between X and Y

        path = graph.find_path("X", "Y")

        assert path is None

    def test_find_all_paths(self) -> None:
        """Test finding all paths."""
        graph = KnowledgeGraph()

        # Create graph with multiple paths: A->B->D and A->C->D
        for name in ["A", "B", "C", "D"]:
            graph.add_concept(Concept(name=name, label=name))

        graph.add_relation(Relation(subject="A", predicate=RelationType.RELATED_TO, object="B"))
        graph.add_relation(Relation(subject="A", predicate=RelationType.RELATED_TO, object="C"))
        graph.add_relation(Relation(subject="B", predicate=RelationType.RELATED_TO, object="D"))
        graph.add_relation(Relation(subject="C", predicate=RelationType.RELATED_TO, object="D"))

        paths = graph.find_all_paths("A", "D")

        assert len(paths) == 2

    def test_get_subgraph(self) -> None:
        """Test subgraph extraction."""
        graph = KnowledgeGraph()

        # Create larger graph
        for i in range(10):
            graph.add_concept(Concept(name=f"Node_{i}", label=f"Node {i}"))

        # Connect linearly: 0 -> 1 -> 2 -> ... -> 9
        for i in range(9):
            graph.add_relation(
                Relation(subject=f"Node_{i}", predicate=RelationType.RELATED_TO, object=f"Node_{i+1}")
            )

        # Get subgraph around Node_5 with radius 2
        subgraph = graph.get_subgraph("Node_5", radius=2)

        # Should include nodes 3, 4, 5, 6, 7
        assert "Node_5" in subgraph
        assert "Node_3" in subgraph
        assert "Node_7" in subgraph
        assert "Node_0" not in subgraph  # Too far

    def test_get_centrality(self) -> None:
        """Test centrality calculation."""
        graph = KnowledgeGraph()

        # Create star graph with A at center
        graph.add_concept(Concept(name="Center", label="Center"))
        for i in range(5):
            graph.add_concept(Concept(name=f"Spoke_{i}", label=f"Spoke {i}"))
            graph.add_relation(
                Relation(subject="Center", predicate=RelationType.RELATED_TO, object=f"Spoke_{i}")
            )

        centrality = graph.get_centrality(method="degree", top_n=1)

        # Center should have highest centrality
        top_node = list(centrality.keys())[0]
        assert top_node == "Center"

    def test_search(self) -> None:
        """Test concept search."""
        graph = KnowledgeGraph()

        concepts = [
            Concept(name="Machine_Learning", label="Machine Learning", description="ML techniques"),
            Concept(name="Deep_Learning", label="Deep Learning", description="Neural networks"),
            Concept(name="Reinforcement_Learning", label="Reinforcement Learning"),
        ]

        for concept in concepts:
            graph.add_concept(concept)

        results = graph.search("Learning")

        assert len(results) == 3
        assert all("Learning" in r.concept.label for r in results)

    def test_search_with_type_filter(self) -> None:
        """Test search with concept type filter."""
        graph = KnowledgeGraph()

        graph.add_concept(Concept(name="Python", label="Python", concept_type=ConceptType.TECHNOLOGY))
        graph.add_concept(Concept(name="Guido", label="Guido van Rossum", concept_type=ConceptType.PERSON))

        results = graph.search("Python", concept_type=ConceptType.TECHNOLOGY)

        assert len(results) == 1
        assert results[0].concept.name == "Python"

    def test_get_stats(self) -> None:
        """Test statistics generation."""
        graph = KnowledgeGraph()

        graph.add_concept(Concept(name="A", label="A", concept_type=ConceptType.ENTITY))
        graph.add_concept(Concept(name="B", label="B", concept_type=ConceptType.TECHNOLOGY))
        graph.add_relation(Relation(subject="A", predicate=RelationType.RELATED_TO, object="B"))

        stats = graph.get_stats()

        assert stats.total_concepts == 2
        assert stats.total_relations == 1
        assert "entity" in stats.concepts_by_type
        assert "technology" in stats.concepts_by_type

    def test_to_dict(self) -> None:
        """Test dictionary export."""
        graph = KnowledgeGraph()

        graph.add_concept(Concept(name="A", label="A"))
        graph.add_concept(Concept(name="B", label="B"))
        graph.add_relation(Relation(subject="A", predicate=RelationType.RELATED_TO, object="B"))

        data = graph.to_dict()

        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1

    def test_iterate_concepts(self) -> None:
        """Test concept iteration."""
        graph = KnowledgeGraph()

        names = ["X", "Y", "Z"]
        for name in names:
            graph.add_concept(Concept(name=name, label=name))

        iterated_names = [c.name for c in graph.iterate_concepts()]

        assert set(iterated_names) == set(names)

    def test_iterate_relations(self) -> None:
        """Test relation iteration."""
        graph = KnowledgeGraph()

        graph.add_concept(Concept(name="A", label="A"))
        graph.add_concept(Concept(name="B", label="B"))
        graph.add_relation(Relation(subject="A", predicate=RelationType.RELATED_TO, object="B"))

        relations = list(graph.iterate_relations())

        assert len(relations) == 1
        assert relations[0][0] == "A"
        assert relations[0][1] == "B"
