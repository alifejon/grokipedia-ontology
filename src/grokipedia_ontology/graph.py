"""
Knowledge graph module.

Provides a high-level interface for building and querying knowledge graphs
using NetworkX, with integration to the RDF-based ontology.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterator

import networkx as nx

from grokipedia_ontology.models import (
    Article,
    Concept,
    ConceptType,
    Relation,
    RelationType,
    SearchResult,
    OntologyStats,
)
from grokipedia_ontology.ontology import GrokipediaOntology


class KnowledgeGraph:
    """
    A knowledge graph built on top of NetworkX.

    Provides:
    - Graph-based navigation and querying
    - Path finding between concepts
    - Community detection
    - Centrality analysis
    - Integration with OWL/RDF ontology
    """

    def __init__(self, ontology: GrokipediaOntology | None = None) -> None:
        """
        Initialize the knowledge graph.

        Args:
            ontology: Optional ontology to integrate with
        """
        self.graph = nx.DiGraph()
        self.ontology = ontology or GrokipediaOntology()
        self._concepts: dict[str, Concept] = {}

    def add_concept(self, concept: Concept) -> None:
        """
        Add a concept as a node in the graph.

        Args:
            concept: Concept to add
        """
        self.graph.add_node(
            concept.name,
            label=concept.label,
            description=concept.description,
            concept_type=concept.concept_type.value,
            source_url=str(concept.source_url) if concept.source_url else None,
            properties=concept.properties,
            categories=concept.categories,
        )
        self._concepts[concept.name] = concept
        self.ontology.add_concept(concept)

    def add_relation(self, relation: Relation) -> None:
        """
        Add a relation as an edge in the graph.

        Args:
            relation: Relation to add
        """
        # Ensure nodes exist
        if relation.subject not in self.graph:
            self.graph.add_node(relation.subject)
        if relation.object not in self.graph:
            self.graph.add_node(relation.object)

        self.graph.add_edge(
            relation.subject,
            relation.object,
            relation_type=relation.predicate.value,
            confidence=relation.confidence,
            source=relation.source,
            properties=relation.properties,
        )
        self.ontology.add_relation(relation)

    def add_article(self, article: Article) -> None:
        """
        Add an article and its relations to the graph.

        Args:
            article: Article to add
        """
        concept = article.to_concept()
        self.add_concept(concept)

        # Add edges to linked articles
        for link in article.links:
            link_name = link.replace(" ", "_")
            relation = Relation(
                subject=concept.name,
                predicate=RelationType.RELATED_TO,
                object=link_name,
                source=str(article.url),
            )
            self.add_relation(relation)

    def get_concept(self, name: str) -> Concept | None:
        """Get a concept by name."""
        return self._concepts.get(name)

    def get_neighbors(
        self,
        concept_name: str,
        relation_type: RelationType | None = None,
        direction: str = "both",
    ) -> list[str]:
        """
        Get neighboring concepts.

        Args:
            concept_name: Name of the concept
            relation_type: Optional filter by relation type
            direction: "in", "out", or "both"

        Returns:
            List of neighbor concept names
        """
        neighbors: set[str] = set()

        if direction in ("out", "both"):
            for _, target, data in self.graph.out_edges(concept_name, data=True):
                if relation_type is None or data.get("relation_type") == relation_type.value:
                    neighbors.add(target)

        if direction in ("in", "both"):
            for source, _, data in self.graph.in_edges(concept_name, data=True):
                if relation_type is None or data.get("relation_type") == relation_type.value:
                    neighbors.add(source)

        return list(neighbors)

    def find_path(
        self,
        source: str,
        target: str,
        max_length: int | None = None,
    ) -> list[str] | None:
        """
        Find shortest path between two concepts.

        Args:
            source: Source concept name
            target: Target concept name
            max_length: Maximum path length

        Returns:
            List of concept names in the path, or None if no path exists
        """
        try:
            path = nx.shortest_path(self.graph, source, target)
            if max_length and len(path) > max_length + 1:
                return None
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def find_all_paths(
        self,
        source: str,
        target: str,
        max_length: int = 5,
    ) -> list[list[str]]:
        """
        Find all simple paths between two concepts.

        Args:
            source: Source concept name
            target: Target concept name
            max_length: Maximum path length

        Returns:
            List of paths (each path is a list of concept names)
        """
        try:
            return list(nx.all_simple_paths(self.graph, source, target, cutoff=max_length))
        except nx.NodeNotFound:
            return []

    def get_subgraph(
        self,
        center: str,
        radius: int = 2,
    ) -> KnowledgeGraph:
        """
        Extract a subgraph around a central concept.

        Args:
            center: Central concept name
            radius: Number of hops from center

        Returns:
            New KnowledgeGraph containing the subgraph
        """
        # Get nodes within radius using BFS
        nodes = {center}
        frontier = {center}

        for _ in range(radius):
            new_frontier: set[str] = set()
            for node in frontier:
                new_frontier.update(self.graph.successors(node))
                new_frontier.update(self.graph.predecessors(node))
            new_frontier -= nodes
            nodes.update(new_frontier)
            frontier = new_frontier

        # Create subgraph
        subgraph = KnowledgeGraph()
        subgraph.graph = self.graph.subgraph(nodes).copy()

        for name in nodes:
            if name in self._concepts:
                subgraph._concepts[name] = self._concepts[name]

        return subgraph

    def get_centrality(
        self,
        method: str = "degree",
        top_n: int | None = None,
    ) -> dict[str, float]:
        """
        Calculate centrality scores for concepts.

        Args:
            method: Centrality method (degree, betweenness, pagerank, eigenvector)
            top_n: Return only top N concepts

        Returns:
            Dictionary mapping concept names to centrality scores
        """
        if method == "degree":
            centrality = nx.degree_centrality(self.graph)
        elif method == "betweenness":
            centrality = nx.betweenness_centrality(self.graph)
        elif method == "pagerank":
            centrality = nx.pagerank(self.graph)
        elif method == "eigenvector":
            try:
                centrality = nx.eigenvector_centrality(self.graph, max_iter=1000)
            except nx.PowerIterationFailedConvergence:
                centrality = nx.degree_centrality(self.graph)
        else:
            raise ValueError(f"Unknown centrality method: {method}")

        if top_n:
            sorted_items = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
            return dict(sorted_items[:top_n])

        return centrality

    def detect_communities(self) -> list[set[str]]:
        """
        Detect communities in the graph.

        Returns:
            List of communities (each community is a set of concept names)
        """
        # Convert to undirected for community detection
        undirected = self.graph.to_undirected()

        try:
            from networkx.algorithms.community import louvain_communities
            communities = louvain_communities(undirected)
        except ImportError:
            # Fallback to connected components
            communities = list(nx.connected_components(undirected))

        return [set(c) for c in communities]

    def search(
        self,
        query: str,
        limit: int = 10,
        concept_type: ConceptType | None = None,
    ) -> list[SearchResult]:
        """
        Search for concepts matching a query.

        Args:
            query: Search query string
            limit: Maximum results to return
            concept_type: Optional filter by concept type

        Returns:
            List of search results with scores
        """
        query_lower = query.lower()
        results: list[tuple[Concept, float, list[str]]] = []

        for name, concept in self._concepts.items():
            if concept_type and concept.concept_type != concept_type:
                continue

            score = 0.0
            matched_fields: list[str] = []

            # Check name
            if query_lower in name.lower():
                score += 1.0
                matched_fields.append("name")

            # Check label
            if query_lower in concept.label.lower():
                score += 0.9
                matched_fields.append("label")

            # Check description
            if concept.description and query_lower in concept.description.lower():
                score += 0.5
                matched_fields.append("description")

            # Check aliases
            for alias in concept.aliases:
                if query_lower in alias.lower():
                    score += 0.7
                    matched_fields.append("alias")
                    break

            # Check categories
            for category in concept.categories:
                if query_lower in category.lower():
                    score += 0.3
                    matched_fields.append("category")
                    break

            if score > 0:
                results.append((concept, score, matched_fields))

        # Sort by score and limit
        results.sort(key=lambda x: x[1], reverse=True)
        results = results[:limit]

        return [
            SearchResult(
                concept=concept,
                score=min(score, 1.0),
                matched_fields=matched_fields,
                related_concepts=self.get_neighbors(concept.name)[:5],
            )
            for concept, score, matched_fields in results
        ]

    def get_stats(self) -> OntologyStats:
        """Get statistics about the knowledge graph."""
        # Count concepts by type
        concepts_by_type: dict[str, int] = defaultdict(int)
        for concept in self._concepts.values():
            concepts_by_type[concept.concept_type.value] += 1

        # Count relations by type
        relations_by_type: dict[str, int] = defaultdict(int)
        for _, _, data in self.graph.edges(data=True):
            rel_type = data.get("relation_type", "unknown")
            relations_by_type[rel_type] += 1

        # Find top connected concepts
        degree_dict = dict(self.graph.degree())
        top_connected = sorted(degree_dict.items(), key=lambda x: x[1], reverse=True)[:10]

        avg_relations = (
            self.graph.number_of_edges() / self.graph.number_of_nodes()
            if self.graph.number_of_nodes() > 0
            else 0.0
        )

        return OntologyStats(
            total_concepts=len(self._concepts),
            total_relations=self.graph.number_of_edges(),
            concepts_by_type=dict(concepts_by_type),
            relations_by_type=dict(relations_by_type),
            top_connected_concepts=top_connected,
            average_relations_per_concept=avg_relations,
        )

    def to_dict(self) -> dict[str, Any]:
        """Export graph to a dictionary representation."""
        return {
            "nodes": [
                {
                    "id": node,
                    **self.graph.nodes[node],
                }
                for node in self.graph.nodes()
            ],
            "edges": [
                {
                    "source": source,
                    "target": target,
                    **data,
                }
                for source, target, data in self.graph.edges(data=True)
            ],
        }

    def export_graphml(self, path: str) -> None:
        """Export graph to GraphML format."""
        nx.write_graphml(self.graph, path)

    def export_gexf(self, path: str) -> None:
        """Export graph to GEXF format (for Gephi)."""
        nx.write_gexf(self.graph, path)

    def iterate_concepts(self) -> Iterator[Concept]:
        """Iterate over all concepts."""
        yield from self._concepts.values()

    def iterate_relations(self) -> Iterator[tuple[str, str, dict[str, Any]]]:
        """Iterate over all relations as (source, target, data) tuples."""
        yield from self.graph.edges(data=True)

    def __len__(self) -> int:
        """Return number of concepts."""
        return len(self._concepts)

    def __contains__(self, name: str) -> bool:
        """Check if a concept exists."""
        return name in self._concepts
