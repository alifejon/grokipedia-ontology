"""Tests for the visualization module."""

import tempfile
from pathlib import Path

import pytest

from grokipedia_ontology.visualization import (
    GraphVisualizer,
    CONCEPT_TYPE_COLORS,
    RELATION_TYPE_COLORS,
)
from grokipedia_ontology.graph import KnowledgeGraph
from grokipedia_ontology.models import Concept, Relation, ConceptType, RelationType


class TestGraphVisualizer:
    """Tests for GraphVisualizer."""

    @pytest.fixture
    def sample_graph(self) -> KnowledgeGraph:
        """Create a sample knowledge graph for testing."""
        graph = KnowledgeGraph()

        # Add concepts
        graph.add_concept(Concept(
            name="Python",
            label="Python",
            description="A programming language",
            concept_type=ConceptType.TECHNOLOGY,
        ))
        graph.add_concept(Concept(
            name="Machine_Learning",
            label="Machine Learning",
            description="AI subset",
            concept_type=ConceptType.ABSTRACT,
        ))
        graph.add_concept(Concept(
            name="TensorFlow",
            label="TensorFlow",
            description="ML framework",
            concept_type=ConceptType.TECHNOLOGY,
        ))

        # Add relations
        graph.add_relation(Relation(
            subject="Python",
            predicate=RelationType.USED_FOR,
            object="Machine_Learning",
        ))
        graph.add_relation(Relation(
            subject="TensorFlow",
            predicate=RelationType.RELATED_TO,
            object="Machine_Learning",
        ))
        graph.add_relation(Relation(
            subject="TensorFlow",
            predicate=RelationType.PART_OF,
            object="Python",
        ))

        return graph

    def test_color_constants(self) -> None:
        """Test that color constants are defined."""
        # All concept types should have colors
        for ctype in ConceptType:
            assert ctype.value in CONCEPT_TYPE_COLORS

        # All relation types should have colors
        for rtype in RelationType:
            assert rtype.value in RELATION_TYPE_COLORS

    def test_visualizer_init(self) -> None:
        """Test visualizer initialization."""
        viz = GraphVisualizer()
        assert viz.width == "100%"
        assert viz.height == "800px"

        viz2 = GraphVisualizer(width="800px", height="600px", bgcolor="#000000")
        assert viz2.width == "800px"
        assert viz2.bgcolor == "#000000"

    def test_export_graphviz(self, sample_graph: KnowledgeGraph) -> None:
        """Test Graphviz DOT export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "graph.dot"
            viz = GraphVisualizer()

            result = viz.export_graphviz(sample_graph, output_path)

            assert result.exists()
            content = result.read_text()

            # Check DOT format
            assert "digraph KnowledgeGraph" in content
            assert "Python" in content
            assert "Machine_Learning" in content
            assert "->" in content  # Edges

    def test_export_graphviz_rankdir(self, sample_graph: KnowledgeGraph) -> None:
        """Test Graphviz export with different rank directions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = GraphVisualizer()

            # Left-to-right
            lr_path = Path(tmpdir) / "lr.dot"
            viz.export_graphviz(sample_graph, lr_path, rankdir="LR")
            assert "rankdir=LR" in lr_path.read_text()

            # Top-to-bottom
            tb_path = Path(tmpdir) / "tb.dot"
            viz.export_graphviz(sample_graph, tb_path, rankdir="TB")
            assert "rankdir=TB" in tb_path.read_text()

    @pytest.mark.skipif(
        True,  # Skip by default since pyvis is optional
        reason="PyVis is an optional dependency"
    )
    def test_visualize_html(self, sample_graph: KnowledgeGraph) -> None:
        """Test HTML visualization (requires pyvis)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "graph.html"
            viz = GraphVisualizer()

            try:
                result = viz.visualize(sample_graph, output_path)
                assert result.exists()
                content = result.read_text()
                assert "<html>" in content.lower()
            except ImportError:
                pytest.skip("PyVis not installed")

    @pytest.mark.skipif(
        True,  # Skip by default since matplotlib is optional
        reason="Matplotlib is an optional dependency"
    )
    def test_generate_stats_chart(self, sample_graph: KnowledgeGraph) -> None:
        """Test statistics chart generation (requires matplotlib)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "stats.png"
            viz = GraphVisualizer()

            try:
                result = viz.generate_stats_chart(sample_graph, output_path)
                if result:
                    assert result.exists()
            except ImportError:
                pytest.skip("Matplotlib not installed")


class TestVisualizerWithoutOptionalDeps:
    """Tests that work without optional dependencies."""

    def test_pyvis_check(self) -> None:
        """Test PyVis availability check."""
        viz = GraphVisualizer()
        # Should not raise, just set flag
        assert hasattr(viz, "_pyvis_available")

    def test_visualize_without_pyvis(self) -> None:
        """Test that visualize raises helpful error without pyvis."""
        viz = GraphVisualizer()
        viz._pyvis_available = False  # Force unavailable

        graph = KnowledgeGraph()
        graph.add_concept(Concept(name="Test", label="Test"))

        with pytest.raises(ImportError) as exc_info:
            viz.visualize(graph, "test.html")

        assert "pyvis" in str(exc_info.value).lower()
        assert "pip install" in str(exc_info.value).lower()
