"""
Data models for Grokipedia Ontology.

Defines the core entities used throughout the package including
articles, concepts, relations, and their properties.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class RelationType(str, Enum):
    """Types of semantic relations between concepts."""

    IS_A = "is_a"  # Taxonomic/subclass relation
    PART_OF = "part_of"  # Mereological relation
    RELATED_TO = "related_to"  # General association
    INSTANCE_OF = "instance_of"  # Class instantiation
    HAS_PROPERTY = "has_property"  # Property attribution
    CAUSED_BY = "caused_by"  # Causal relation
    RESULTS_IN = "results_in"  # Effect relation
    USED_FOR = "used_for"  # Functional relation
    LOCATED_IN = "located_in"  # Spatial relation
    OCCURS_IN = "occurs_in"  # Temporal/contextual relation
    CONTRADICTS = "contradicts"  # Logical opposition
    SUPPORTS = "supports"  # Evidential support
    DERIVED_FROM = "derived_from"  # Derivation/origin
    EQUIVALENT_TO = "equivalent_to"  # Semantic equivalence
    SEE_ALSO = "see_also"  # Cross-reference


class ConceptType(str, Enum):
    """Categories of concepts in the ontology."""

    ENTITY = "entity"  # Physical or abstract thing
    EVENT = "event"  # Occurrence in time
    PROCESS = "process"  # Ongoing activity
    PROPERTY = "property"  # Attribute or characteristic
    RELATION = "relation"  # Connection between entities
    ABSTRACT = "abstract"  # Abstract concept
    PERSON = "person"  # Individual human
    ORGANIZATION = "organization"  # Group or institution
    LOCATION = "location"  # Geographic place
    TIME_PERIOD = "time_period"  # Historical era or duration
    WORK = "work"  # Creative or intellectual work
    TECHNOLOGY = "technology"  # Technical system or tool


class Article(BaseModel):
    """Represents a Grokipedia article."""

    title: str = Field(..., description="Article title")
    url: HttpUrl = Field(..., description="Full URL to the article")
    slug: str = Field(..., description="URL slug (page identifier)")
    content: str = Field(default="", description="Full article content")
    summary: str = Field(default="", description="Article summary/abstract")
    categories: list[str] = Field(default_factory=list, description="Article categories")
    links: list[str] = Field(default_factory=list, description="Internal links to other articles")
    external_links: list[str] = Field(default_factory=list, description="External reference links")
    infobox: dict[str, Any] = Field(default_factory=dict, description="Structured infobox data")
    sections: list[dict[str, str]] = Field(
        default_factory=list, description="Article sections with titles and content"
    )
    fetched_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp of data retrieval"
    )
    language: str = Field(default="en", description="Article language code")

    @property
    def concept_name(self) -> str:
        """Convert article title to a valid concept name."""
        return self.title.replace(" ", "_").replace("(", "").replace(")", "")

    def to_concept(self) -> Concept:
        """Convert article to a concept for ontology integration."""
        return Concept(
            name=self.concept_name,
            label=self.title,
            description=self.summary or self.content[:500] if self.content else "",
            source_url=self.url,
            properties=self.infobox,
            categories=self.categories,
        )


class Concept(BaseModel):
    """Represents a concept/class in the ontology."""

    name: str = Field(..., description="Unique concept identifier (URI-safe)")
    label: str = Field(..., description="Human-readable label")
    description: str = Field(default="", description="Concept description/definition")
    concept_type: ConceptType = Field(default=ConceptType.ENTITY, description="Type of concept")
    source_url: HttpUrl | None = Field(default=None, description="Source URL if from Grokipedia")
    properties: dict[str, Any] = Field(default_factory=dict, description="Concept properties")
    categories: list[str] = Field(default_factory=list, description="Concept categories")
    aliases: list[str] = Field(default_factory=list, description="Alternative names/synonyms")
    parent_concepts: list[str] = Field(default_factory=list, description="Parent concept names")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def uri(self) -> str:
        """Generate URI for this concept."""
        return f"http://grokipedia.org/ontology#{self.name}"


class Relation(BaseModel):
    """Represents a relation/property between concepts."""

    subject: str = Field(..., description="Subject concept name")
    predicate: RelationType = Field(..., description="Relation type")
    object: str = Field(..., description="Object concept name")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score of the relation"
    )
    source: str = Field(default="", description="Source of this relation")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional properties")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def triple(self) -> tuple[str, str, str]:
        """Return as RDF-like triple."""
        return (self.subject, self.predicate.value, self.object)


class OntologyStats(BaseModel):
    """Statistics about the ontology."""

    total_concepts: int = 0
    total_relations: int = 0
    concepts_by_type: dict[str, int] = Field(default_factory=dict)
    relations_by_type: dict[str, int] = Field(default_factory=dict)
    top_connected_concepts: list[tuple[str, int]] = Field(default_factory=list)
    average_relations_per_concept: float = 0.0


class SearchResult(BaseModel):
    """Result from searching the knowledge graph."""

    concept: Concept
    score: float = Field(ge=0.0, le=1.0)
    matched_fields: list[str] = Field(default_factory=list)
    related_concepts: list[str] = Field(default_factory=list)
