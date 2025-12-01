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
        subject_uri = GROK[relation.subject]
        object_uri = GROK[relation.object]
        predicate_uri = GROK_PROP[relation.predicate.value]

        self.graph.add((subject_uri, predicate_uri, object_uri))

        # Add confidence as reification if not 1.0
        if relation.confidence < 1.0:
            stmt_uri = GROK[f"stmt_{relation.subject}_{relation.predicate.value}_{relation.object}"]
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

    def infer_relations(self) -> list[Relation]:
        """
        Infer additional relations using basic reasoning.

        Currently implements:
        - Transitive closure for IS_A relations
        - Inverse relations

        Returns:
            List of inferred relations
        """
        inferred: list[Relation] = []

        # Build IS_A hierarchy
        is_a_map: dict[str, set[str]] = {}
        for relation in self._relations:
            if relation.predicate == RelationType.IS_A:
                if relation.subject not in is_a_map:
                    is_a_map[relation.subject] = set()
                is_a_map[relation.subject].add(relation.object)

        # Compute transitive closure
        def get_ancestors(concept: str, visited: set[str] | None = None) -> set[str]:
            if visited is None:
                visited = set()
            if concept in visited:
                return set()
            visited.add(concept)

            ancestors = is_a_map.get(concept, set()).copy()
            for parent in list(ancestors):
                ancestors.update(get_ancestors(parent, visited))
            return ancestors

        # Add inferred IS_A relations
        for concept in is_a_map:
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

        return inferred
