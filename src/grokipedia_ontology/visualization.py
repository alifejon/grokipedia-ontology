"""
Visualization module for Grokipedia Ontology.

Provides interactive graph visualization using PyVis and static
visualization options using matplotlib.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from grokipedia_ontology.models import ConceptType, RelationType
from grokipedia_ontology.utils import get_logger

if TYPE_CHECKING:
    from grokipedia_ontology.graph import KnowledgeGraph

logger = get_logger(__name__)

# Color schemes for visualization
CONCEPT_TYPE_COLORS: dict[str, str] = {
    ConceptType.ENTITY.value: "#4A90D9",  # Blue
    ConceptType.EVENT.value: "#E74C3C",  # Red
    ConceptType.PROCESS.value: "#27AE60",  # Green
    ConceptType.PROPERTY.value: "#9B59B6",  # Purple
    ConceptType.RELATION.value: "#F39C12",  # Orange
    ConceptType.ABSTRACT.value: "#95A5A6",  # Gray
    ConceptType.PERSON.value: "#E91E63",  # Pink
    ConceptType.ORGANIZATION.value: "#00BCD4",  # Cyan
    ConceptType.LOCATION.value: "#8BC34A",  # Light Green
    ConceptType.TIME_PERIOD.value: "#FF9800",  # Deep Orange
    ConceptType.WORK.value: "#673AB7",  # Deep Purple
    ConceptType.TECHNOLOGY.value: "#2196F3",  # Light Blue
}

RELATION_TYPE_COLORS: dict[str, str] = {
    RelationType.IS_A.value: "#2C3E50",  # Dark Blue
    RelationType.PART_OF.value: "#16A085",  # Teal
    RelationType.RELATED_TO.value: "#7F8C8D",  # Gray
    RelationType.INSTANCE_OF.value: "#8E44AD",  # Purple
    RelationType.HAS_PROPERTY.value: "#D35400",  # Orange
    RelationType.CAUSED_BY.value: "#C0392B",  # Dark Red
    RelationType.RESULTS_IN.value: "#E74C3C",  # Red
    RelationType.USED_FOR.value: "#27AE60",  # Green
    RelationType.LOCATED_IN.value: "#3498DB",  # Blue
    RelationType.OCCURS_IN.value: "#9B59B6",  # Purple
    RelationType.CONTRADICTS.value: "#E91E63",  # Pink
    RelationType.SUPPORTS.value: "#4CAF50",  # Green
    RelationType.DERIVED_FROM.value: "#FF5722",  # Deep Orange
    RelationType.EQUIVALENT_TO.value: "#00BCD4",  # Cyan
    RelationType.SEE_ALSO.value: "#607D8B",  # Blue Gray
}


class GraphVisualizer:
    """
    Visualizes knowledge graphs using PyVis for interactive HTML output.

    Provides:
    - Interactive node/edge visualization
    - Color coding by concept type
    - Filtering and highlighting
    - Export to HTML for web viewing
    """

    def __init__(
        self,
        width: str = "100%",
        height: str = "800px",
        bgcolor: str = "#ffffff",
        font_color: str = "#333333",
    ) -> None:
        """
        Initialize the visualizer.

        Args:
            width: Width of the visualization
            height: Height of the visualization
            bgcolor: Background color
            font_color: Font color for labels
        """
        self.width = width
        self.height = height
        self.bgcolor = bgcolor
        self.font_color = font_color
        self._check_pyvis()

    def _check_pyvis(self) -> None:
        """Check if PyVis is available."""
        try:
            import pyvis  # noqa: F401
            self._pyvis_available = True
        except ImportError:
            self._pyvis_available = False
            logger.warning(
                "PyVis not installed. Install with: pip install grokipedia-ontology[visualization]"
            )

    def visualize(
        self,
        graph: KnowledgeGraph,
        output_path: str | Path = "knowledge_graph.html",
        title: str = "Grokipedia Knowledge Graph",
        physics: bool = True,
        notebook: bool = False,
        filter_concept_types: list[str] | None = None,
        filter_relation_types: list[str] | None = None,
        max_nodes: int | None = None,
        highlight_concepts: list[str] | None = None,
    ) -> Path:
        """
        Create an interactive visualization of the knowledge graph.

        Args:
            graph: KnowledgeGraph to visualize
            output_path: Path for the output HTML file
            title: Title for the visualization
            physics: Enable physics simulation for node positioning
            notebook: Enable notebook mode for Jupyter
            filter_concept_types: Only show concepts of these types
            filter_relation_types: Only show relations of these types
            max_nodes: Maximum number of nodes to display
            highlight_concepts: List of concept names to highlight

        Returns:
            Path to the generated HTML file

        Raises:
            ImportError: If PyVis is not installed
        """
        if not self._pyvis_available:
            raise ImportError(
                "PyVis is required for visualization. "
                "Install with: pip install grokipedia-ontology[visualization]"
            )

        from pyvis.network import Network

        output_path = Path(output_path)

        # Create network
        net = Network(
            width=self.width,
            height=self.height,
            bgcolor=self.bgcolor,
            font_color=self.font_color,
            notebook=notebook,
            directed=True,
            heading=title,
        )

        # Configure physics
        if physics:
            net.barnes_hut(
                gravity=-3000,
                central_gravity=0.3,
                spring_length=150,
                spring_strength=0.05,
                damping=0.09,
            )
        else:
            net.toggle_physics(False)

        # Collect nodes and edges with filtering
        nodes_to_add: list[tuple[str, dict[str, Any]]] = []
        highlight_set = set(highlight_concepts or [])

        for name, concept in graph._concepts.items():
            # Apply concept type filter
            if filter_concept_types and concept.concept_type.value not in filter_concept_types:
                continue

            color = CONCEPT_TYPE_COLORS.get(concept.concept_type.value, "#95A5A6")

            # Highlight selected concepts
            border_width = 3 if name in highlight_set else 1
            border_color = "#FFD700" if name in highlight_set else color

            nodes_to_add.append((name, {
                "label": concept.label,
                "title": self._build_node_tooltip(concept),
                "color": {
                    "background": color,
                    "border": border_color,
                    "highlight": {"background": "#FFD700", "border": "#FF8C00"},
                },
                "borderWidth": border_width,
                "size": 25 if name in highlight_set else 15,
                "shape": "dot",
                "font": {"size": 12},
            }))

        # Apply max_nodes limit
        if max_nodes and len(nodes_to_add) > max_nodes:
            # Sort by degree centrality to keep most connected nodes
            node_degrees = dict(graph.graph.degree())
            nodes_to_add.sort(key=lambda x: node_degrees.get(x[0], 0), reverse=True)
            nodes_to_add = nodes_to_add[:max_nodes]

        # Add nodes to network
        node_names = {name for name, _ in nodes_to_add}
        for name, attrs in nodes_to_add:
            net.add_node(name, **attrs)

        # Add edges
        for source, target, data in graph.graph.edges(data=True):
            # Only add edge if both nodes are in the filtered set
            if source not in node_names or target not in node_names:
                continue

            rel_type = data.get("relation_type", "related_to")

            # Apply relation type filter
            if filter_relation_types and rel_type not in filter_relation_types:
                continue

            color = RELATION_TYPE_COLORS.get(rel_type, "#7F8C8D")
            confidence = data.get("confidence", 1.0)

            net.add_edge(
                source,
                target,
                title=f"{rel_type} (confidence: {confidence:.2f})",
                color=color,
                width=1 + confidence * 2,
                arrows="to",
                arrowStrikethrough=False,
            )

        # Add legend
        self._add_legend(net, nodes_to_add, graph)

        # Save visualization
        output_path.parent.mkdir(parents=True, exist_ok=True)
        net.save_graph(str(output_path))

        logger.info(f"Visualization saved to: {output_path}")
        return output_path

    def _build_node_tooltip(self, concept: Any) -> str:
        """Build HTML tooltip for a node."""
        tooltip_parts = [
            f"<b>{concept.label}</b>",
            f"<br><i>Type:</i> {concept.concept_type.value}",
        ]

        if concept.description:
            desc = concept.description[:200]
            if len(concept.description) > 200:
                desc += "..."
            tooltip_parts.append(f"<br><i>Description:</i> {desc}")

        if concept.categories:
            cats = ", ".join(concept.categories[:5])
            tooltip_parts.append(f"<br><i>Categories:</i> {cats}")

        if concept.source_url:
            tooltip_parts.append(f"<br><a href='{concept.source_url}'>Source</a>")

        return "".join(tooltip_parts)

    def _add_legend(
        self,
        net: Any,
        nodes: list[tuple[str, dict[str, Any]]],
        graph: KnowledgeGraph,
    ) -> None:
        """Add a legend to the visualization."""
        # Get unique concept types in the graph
        concept_types_used = set()
        for name, _ in nodes:
            concept = graph._concepts.get(name)
            if concept:
                concept_types_used.add(concept.concept_type.value)

        # Add legend nodes (positioned far from main graph)
        x_offset = -500
        y_offset = -400

        for i, ctype in enumerate(sorted(concept_types_used)):
            color = CONCEPT_TYPE_COLORS.get(ctype, "#95A5A6")
            legend_id = f"_legend_{ctype}"
            net.add_node(
                legend_id,
                label=ctype.replace("_", " ").title(),
                color=color,
                size=10,
                x=x_offset,
                y=y_offset + i * 30,
                physics=False,
                shape="dot",
                font={"size": 10},
            )

    def visualize_subgraph(
        self,
        graph: KnowledgeGraph,
        center: str,
        radius: int = 2,
        output_path: str | Path = "subgraph.html",
        **kwargs: Any,
    ) -> Path:
        """
        Visualize a subgraph centered around a concept.

        Args:
            graph: KnowledgeGraph to extract subgraph from
            center: Central concept name
            radius: Number of hops from center
            output_path: Path for the output HTML file
            **kwargs: Additional arguments passed to visualize()

        Returns:
            Path to the generated HTML file
        """
        subgraph = graph.get_subgraph(center, radius)
        return self.visualize(
            subgraph,
            output_path=output_path,
            title=f"Knowledge Graph: {center} (radius={radius})",
            highlight_concepts=[center],
            **kwargs,
        )

    def export_graphviz(
        self,
        graph: KnowledgeGraph,
        output_path: str | Path = "knowledge_graph.dot",
        rankdir: str = "TB",
    ) -> Path:
        """
        Export graph to Graphviz DOT format.

        Args:
            graph: KnowledgeGraph to export
            output_path: Path for the output DOT file
            rankdir: Graph direction (TB=top-bottom, LR=left-right)

        Returns:
            Path to the generated DOT file
        """
        output_path = Path(output_path)

        lines = [
            f'digraph KnowledgeGraph {{',
            f'    rankdir={rankdir};',
            f'    node [shape=ellipse, style=filled];',
            f'    edge [fontsize=10];',
            '',
        ]

        # Add nodes
        for name, concept in graph._concepts.items():
            color = CONCEPT_TYPE_COLORS.get(concept.concept_type.value, "#95A5A6")
            label = concept.label.replace('"', '\\"')
            lines.append(
                f'    "{name}" [label="{label}", fillcolor="{color}"];'
            )

        lines.append('')

        # Add edges
        for source, target, data in graph.graph.edges(data=True):
            rel_type = data.get("relation_type", "related_to")
            color = RELATION_TYPE_COLORS.get(rel_type, "#7F8C8D")
            lines.append(
                f'    "{source}" -> "{target}" [label="{rel_type}", color="{color}"];'
            )

        lines.append('}')

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text('\n'.join(lines))

        logger.info(f"Graphviz DOT file saved to: {output_path}")
        return output_path

    def generate_stats_chart(
        self,
        graph: KnowledgeGraph,
        output_path: str | Path = "stats_chart.png",
    ) -> Path | None:
        """
        Generate a statistics chart using matplotlib.

        Args:
            graph: KnowledgeGraph to analyze
            output_path: Path for the output image file

        Returns:
            Path to the generated image, or None if matplotlib unavailable
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.warning(
                "Matplotlib not installed. Install with: pip install grokipedia-ontology[visualization]"
            )
            return None

        output_path = Path(output_path)
        stats = graph.get_stats()

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle("Knowledge Graph Statistics", fontsize=16, fontweight="bold")

        # 1. Concepts by Type (Pie Chart)
        if stats.concepts_by_type:
            ax1 = axes[0, 0]
            labels = list(stats.concepts_by_type.keys())
            sizes = list(stats.concepts_by_type.values())
            colors = [CONCEPT_TYPE_COLORS.get(t, "#95A5A6") for t in labels]
            ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax1.set_title("Concepts by Type")

        # 2. Relations by Type (Bar Chart)
        if stats.relations_by_type:
            ax2 = axes[0, 1]
            types = list(stats.relations_by_type.keys())
            counts = list(stats.relations_by_type.values())
            colors = [RELATION_TYPE_COLORS.get(t, "#7F8C8D") for t in types]
            bars = ax2.barh(types, counts, color=colors)
            ax2.set_xlabel("Count")
            ax2.set_title("Relations by Type")
            ax2.bar_label(bars)

        # 3. Top Connected Concepts (Bar Chart)
        if stats.top_connected_concepts:
            ax3 = axes[1, 0]
            concepts = [c[0][:20] for c in stats.top_connected_concepts[:10]]
            connections = [c[1] for c in stats.top_connected_concepts[:10]]
            ax3.barh(concepts, connections, color="#4A90D9")
            ax3.set_xlabel("Connections")
            ax3.set_title("Top 10 Connected Concepts")
            ax3.invert_yaxis()

        # 4. Summary Stats (Text)
        ax4 = axes[1, 1]
        ax4.axis('off')
        summary_text = (
            f"Total Concepts: {stats.total_concepts}\n"
            f"Total Relations: {stats.total_relations}\n"
            f"Avg Relations/Concept: {stats.average_relations_per_concept:.2f}\n"
            f"Concept Types: {len(stats.concepts_by_type)}\n"
            f"Relation Types: {len(stats.relations_by_type)}"
        )
        ax4.text(
            0.5, 0.5, summary_text,
            ha='center', va='center',
            fontsize=14,
            transform=ax4.transAxes,
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5)
        )
        ax4.set_title("Summary")

        plt.tight_layout()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        logger.info(f"Stats chart saved to: {output_path}")
        return output_path
