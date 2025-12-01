"""
Ontology management module.

Provides functionality for creating, managing, and querying OWL/RDF ontologies
based on Grokipedia content.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, XSD
from rdflib.term import URIRef

from grokipedia_ontology.models import (
    Article,
    Concept,
    ConceptType,
    Relation,
    RelationType,
    OntologyStats,
)
from grokipedia_ontology.utils import (
    get_logger,
    sanitize_uri_component,
    OntologyError,
    CyclicReferenceError,
)

logger = get_logger(__name__)


# Define namespaces
GROK = Namespace("http://grokipedia.org/ontology#")
GROK_PROP = Namespace("http://grokipedia.org/property#")
GROK_CLASS = Namespace("http://grokipedia.org/class#")


class GrokipediaOntology:
    """
    Manages an OWL/RDF ontology built from Grokipedia content.

    Provides functionality to:
    - Define ontology schema and classes
    - Add concepts and relations
    - Serialize to various formats (RDF/XML, Turtle, JSON-LD)
    - Query using SPARQL
    - Perform reasoning and inference
    """

    def __init__(self, base_uri: str = "http://grokipedia.org/ontology") -> None:
        """
        Initialize the ontology.

        Args:
            base_uri: Base URI for the ontology
        """
        self.base_uri = base_uri
        self.graph = Graph()
        self._setup_namespaces()
        self._setup_base_ontology()
        self._concepts: dict[str, Concept] = {}
        self._relations: list[Relation] = []

    def _setup_namespaces(self) -> None:
        """Bind common namespaces to the graph."""
        self.graph.bind("grok", GROK)
        self.graph.bind("grok_prop", GROK_PROP)
        self.graph.bind("grok_class", GROK_CLASS)
        self.graph.bind("owl", OWL)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("xsd", XSD)

    def _setup_base_ontology(self) -> None:
        """Define base ontology structure with core classes and properties."""
        # Ontology metadata
        ontology_uri = URIRef(self.base_uri)
        self.graph.add((ontology_uri, RDF.type, OWL.Ontology))
        self.graph.add((ontology_uri, RDFS.label, Literal("Grokipedia Ontology")))
        self.graph.add((
            ontology_uri,
            RDFS.comment,
            Literal("An ontology derived from Grokipedia knowledge base"),
        ))

        # Define base classes for each ConceptType
        for concept_type in ConceptType:
            class_uri = GROK_CLASS[concept_type.value]
            self.graph.add((class_uri, RDF.type, OWL.Class))
            self.graph.add((class_uri, RDFS.label, Literal(concept_type.value.replace("_", " ").title())))
            self.graph.add((class_uri, RDFS.subClassOf, OWL.Thing))

        # Define properties for each RelationType
        for rel_type in RelationType:
            prop_uri = GROK_PROP[rel_type.value]
            self.graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
            self.graph.add((prop_uri, RDFS.label, Literal(rel_type.value.replace("_", " "))))
            self.graph.add((prop_uri, RDFS.domain, OWL.Thing))
            self.graph.add((prop_uri, RDFS.range, OWL.Thing))

        # Define common data properties
        self._define_data_property("hasDescription", XSD.string, "Description of the concept")
        self._define_data_property("hasLabel", XSD.string, "Human-readable label")
        self._define_data_property("hasSourceURL", XSD.anyURI, "Source URL from Grokipedia")
        self._define_data_property("hasConfidence", XSD.float, "Confidence score")
        self._define_data_property("createdAt", XSD.dateTime, "Creation timestamp")

    def _define_data_property(
        self,
        name: str,
        datatype: URIRef,
        description: str,
    ) -> None:
        """Define a data property in the ontology."""
        prop_uri = GROK_PROP[name]
        self.graph.add((prop_uri, RDF.type, OWL.DatatypeProperty))
        self.graph.add((prop_uri, RDFS.label, Literal(name)))
        self.graph.add((prop_uri, RDFS.comment, Literal(description)))
        self.graph.add((prop_uri, RDFS.range, datatype))

    def add_concept(self, concept: Concept) -> URIRef:
        """
        Add a concept to the ontology.

        Args:
            concept: Concept to add

        Returns:
            URI of the added concept
        """
        concept_uri = GROK[concept.name]

        # Add as instance of appropriate class
        class_uri = GROK_CLASS[concept.concept_type.value]
        self.graph.add((concept_uri, RDF.type, class_uri))

        # Add labels and descriptions
        self.graph.add((concept_uri, RDFS.label, Literal(concept.label)))
        if concept.description:
            self.graph.add((concept_uri, RDFS.comment, Literal(concept.description)))
            self.graph.add((
                concept_uri,
                GROK_PROP.hasDescription,
                Literal(concept.description),
            ))

        # Add source URL
        if concept.source_url:
            self.graph.add((
                concept_uri,
                GROK_PROP.hasSourceURL,
                Literal(str(concept.source_url), datatype=XSD.anyURI),
            ))

        # Add aliases
        for alias in concept.aliases:
            self.graph.add((concept_uri, RDFS.label, Literal(alias)))

        # Add categories
        for category in concept.categories:
            cat_uri = GROK[category.replace(" ", "_")]
            self.graph.add((concept_uri, GROK_PROP.hasCategory, cat_uri))

        # Add properties as custom annotations
        for key, value in concept.properties.items():
            prop_uri = GROK_PROP[key.replace(" ", "_")]
            self.graph.add((prop_uri, RDF.type, OWL.AnnotationProperty))
            self.graph.add((concept_uri, prop_uri, Literal(str(value))))

        # Add parent class relationships
        for parent_name in concept.parent_concepts:
            parent_uri = GROK[parent_name]
            self.graph.add((concept_uri, RDFS.subClassOf, parent_uri))

        self._concepts[concept.name] = concept
        return concept_uri

    def add_relation(self, relation: Relation) -> None:
        """
        Add a relation between concepts.

        Args:
            relation: Relation to add
        """
        # Sanitize URI components to prevent invalid URIs
        subject_safe = sanitize_uri_component(relation.subject)
        object_safe = sanitize_uri_component(relation.object)

        subject_uri = GROK[subject_safe]
        object_uri = GROK[object_safe]
        predicate_uri = GROK_PROP[relation.predicate.value]

        self.graph.add((subject_uri, predicate_uri, object_uri))
        logger.debug(f"Added relation: {relation.subject} --{relation.predicate.value}--> {relation.object}")

        # Add confidence as reification if not 1.0
        if relation.confidence < 1.0:
            # Create a safe statement URI
            stmt_id = sanitize_uri_component(
                f"stmt_{relation.subject}_{relation.predicate.value}_{relation.object}"
            )
            stmt_uri = GROK[stmt_id]
            self.graph.add((stmt_uri, RDF.type, RDF.Statement))
            self.graph.add((stmt_uri, RDF.subject, subject_uri))
            self.graph.add((stmt_uri, RDF.predicate, predicate_uri))
            self.graph.add((stmt_uri, RDF.object, object_uri))
            self.graph.add((stmt_uri, GROK_PROP.hasConfidence, Literal(relation.confidence)))

        self._relations.append(relation)

    def add_article(self, article: Article) -> URIRef:
        """
        Add an article to the ontology, converting it to a concept.

        Args:
            article: Article to add

        Returns:
            URI of the created concept
        """
        concept = article.to_concept()
        concept_uri = self.add_concept(concept)

        # Add relations to linked articles
        for link in article.links:
            link_name = link.replace(" ", "_")
            relation = Relation(
                subject=concept.name,
                predicate=RelationType.RELATED_TO,
                object=link_name,
                source=str(article.url),
            )
            self.add_relation(relation)

        return concept_uri

    def get_concept(self, name: str) -> Concept | None:
        """Get a concept by name."""
        return self._concepts.get(name)

    def get_relations(
        self,
        subject: str | None = None,
        predicate: RelationType | None = None,
        obj: str | None = None,
    ) -> list[Relation]:
        """
        Get relations matching the given criteria.

        Args:
            subject: Filter by subject concept name
            predicate: Filter by relation type
            obj: Filter by object concept name

        Returns:
            List of matching relations
        """
        results = []
        for relation in self._relations:
            if subject and relation.subject != subject:
                continue
            if predicate and relation.predicate != predicate:
                continue
            if obj and relation.object != obj:
                continue
            results.append(relation)
        return results

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """
        Execute a SPARQL query on the ontology.

        Args:
            sparql: SPARQL query string

        Returns:
            List of result bindings as dictionaries
        """
        results = self.graph.query(sparql)
        return [
            {str(var): str(value) for var, value in row.asdict().items()}
            for row in results
        ]

    def get_stats(self) -> OntologyStats:
        """Get statistics about the ontology."""
        # Count concepts by type
        concepts_by_type: dict[str, int] = {}
        for concept in self._concepts.values():
            type_name = concept.concept_type.value
            concepts_by_type[type_name] = concepts_by_type.get(type_name, 0) + 1

        # Count relations by type
        relations_by_type: dict[str, int] = {}
        for relation in self._relations:
            type_name = relation.predicate.value
            relations_by_type[type_name] = relations_by_type.get(type_name, 0) + 1

        # Find top connected concepts
        connection_count: dict[str, int] = {}
        for relation in self._relations:
            connection_count[relation.subject] = connection_count.get(relation.subject, 0) + 1
            connection_count[relation.object] = connection_count.get(relation.object, 0) + 1

        top_connected = sorted(connection_count.items(), key=lambda x: x[1], reverse=True)[:10]

        avg_relations = (
            len(self._relations) / len(self._concepts) if self._concepts else 0.0
        )

        return OntologyStats(
            total_concepts=len(self._concepts),
            total_relations=len(self._relations),
            concepts_by_type=concepts_by_type,
            relations_by_type=relations_by_type,
            top_connected_concepts=top_connected,
            average_relations_per_concept=avg_relations,
        )

    def serialize(self, format: str = "turtle") -> str:
        """
        Serialize the ontology to a string.

        Args:
            format: Serialization format (turtle, xml, json-ld, n3, nt)

        Returns:
            Serialized ontology string
        """
        return self.graph.serialize(format=format)

    def save(self, path: str | Path, format: str = "turtle") -> None:
        """
        Save the ontology to a file.

        Args:
            path: File path to save to
            format: Serialization format
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self.serialize(format=format)
        path.write_text(content)

    def load(self, path: str | Path, format: str | None = None) -> None:
        """
        Load an ontology from a file.

        Args:
            path: File path to load from
            format: Format (auto-detected if None)
        """
        path = Path(path)
        if format is None:
            suffix_map = {
                ".ttl": "turtle",
                ".rdf": "xml",
                ".xml": "xml",
                ".jsonld": "json-ld",
                ".json": "json-ld",
                ".n3": "n3",
                ".nt": "nt",
            }
            format = suffix_map.get(path.suffix, "turtle")

        self.graph.parse(path, format=format)

    def merge(self, other: GrokipediaOntology) -> None:
        """
        Merge another ontology into this one.

        Args:
            other: Ontology to merge
        """
        self.graph += other.graph
        self._concepts.update(other._concepts)
        self._relations.extend(other._relations)

    def infer_relations(self, detect_cycles: bool = True) -> list[Relation]:
        """
        Infer additional relations using basic reasoning.

        Currently implements:
        - Transitive closure for IS_A relations
        - Inverse relations

        Args:
            detect_cycles: If True, detect and log cyclic references

        Returns:
            List of inferred relations

        Raises:
            CyclicReferenceError: If detect_cycles is True and a cycle is found
        """
        inferred: list[Relation] = []
        detected_cycles: list[list[str]] = []

        logger.info("Starting relation inference...")

        # Build IS_A hierarchy
        is_a_map: dict[str, set[str]] = {}
        for relation in self._relations:
            if relation.predicate == RelationType.IS_A:
                if relation.subject not in is_a_map:
                    is_a_map[relation.subject] = set()
                is_a_map[relation.subject].add(relation.object)

        # Detect cycles using DFS
        def detect_cycle(start: str) -> list[str] | None:
            """Detect cycle starting from a concept, return cycle path if found."""
            path: list[str] = []
            visited: set[str] = set()

            def dfs(node: str) -> list[str] | None:
                if node in path:
                    # Found cycle - return the cycle portion
                    cycle_start = path.index(node)
                    return path[cycle_start:] + [node]

                if node in visited:
                    return None

                visited.add(node)
                path.append(node)

                for parent in is_a_map.get(node, set()):
                    cycle = dfs(parent)
                    if cycle:
                        return cycle

                path.pop()
                return None

            return dfs(start)

        # Check for cycles
        if detect_cycles:
            for concept in is_a_map:
                cycle = detect_cycle(concept)
                if cycle and cycle not in detected_cycles:
                    detected_cycles.append(cycle)
                    logger.warning(f"Detected cyclic IS_A reference: {' -> '.join(cycle)}")

            if detected_cycles:
                logger.warning(f"Found {len(detected_cycles)} cyclic reference(s). Skipping affected concepts.")

        # Get concepts involved in cycles
        cyclic_concepts: set[str] = set()
        for cycle in detected_cycles:
            cyclic_concepts.update(cycle)

        # Compute transitive closure with cycle protection
        def get_ancestors(
            concept: str,
            visited: set[str] | None = None,
            depth: int = 0,
            max_depth: int = 100,
        ) -> set[str]:
            """Get all ancestors with depth limit and cycle protection."""
            if visited is None:
                visited = set()

            # Depth limit to prevent runaway recursion
            if depth > max_depth:
                logger.warning(f"Max depth reached for concept '{concept}'")
                return set()

            if concept in visited:
                return set()

            visited.add(concept)

            ancestors = is_a_map.get(concept, set()).copy()
            for parent in list(ancestors):
                # Skip if parent is involved in a cycle we're already processing
                if parent not in cyclic_concepts or parent not in visited:
                    ancestors.update(get_ancestors(parent, visited, depth + 1, max_depth))

            return ancestors

        # Add inferred IS_A relations
        for concept in is_a_map:
            # Skip concepts involved in cycles
            if concept in cyclic_concepts:
                continue

            all_ancestors = get_ancestors(concept)
            direct_parents = is_a_map[concept]

            for ancestor in all_ancestors - direct_parents:
                relation = Relation(
                    subject=concept,
                    predicate=RelationType.IS_A,
                    object=ancestor,
                    confidence=0.9,
                    source="inference:transitive_closure",
                )
                inferred.append(relation)
                self.add_relation(relation)

        logger.info(f"Inference complete: {len(inferred)} new relations inferred")
        return inferred
