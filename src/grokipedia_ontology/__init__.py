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

__version__ = "0.1.0"
__all__ = [
    "Article",
    "Concept",
    "Relation",
    "GrokipediaFetcher",
    "GrokipediaOntology",
    "KnowledgeGraph",
]
