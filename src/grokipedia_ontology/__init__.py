"""
Grokipedia Ontology - A knowledge graph and ontology framework using Grokipedia as a data source.

This package provides tools for:
- Fetching and parsing content from Grokipedia
- Building ontologies using OWL/RDF standards
- Constructing and querying knowledge graphs
- Semantic reasoning and inference
"""

from grokipedia_ontology.models import Article, Concept, Relation
from grokipedia_ontology.fetcher import GrokipediaFetcher
from grokipedia_ontology.ontology import GrokipediaOntology
from grokipedia_ontology.graph import KnowledgeGraph
from grokipedia_ontology.visualization import GraphVisualizer
from grokipedia_ontology.cache import ArticleCache, CachedFetcher, MemoryCache, DiskCache
from grokipedia_ontology.search import SearchIndex, SearchHit
from grokipedia_ontology.utils import (
    GrokipediaError,
    FetchError,
    OntologyError,
    ValidationError,
    CyclicReferenceError,
    sanitize_uri_component,
)

__version__ = "0.1.0"
__all__ = [
    # Core classes
    "Article",
    "Concept",
    "Relation",
    "GrokipediaFetcher",
    "GrokipediaOntology",
    "KnowledgeGraph",
    "GraphVisualizer",
    # Caching
    "ArticleCache",
    "CachedFetcher",
    "MemoryCache",
    "DiskCache",
    # Search
    "SearchIndex",
    "SearchHit",
    # Exceptions
    "GrokipediaError",
    "FetchError",
    "OntologyError",
    "ValidationError",
    "CyclicReferenceError",
    # Utilities
    "sanitize_uri_component",
]
