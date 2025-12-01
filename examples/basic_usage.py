#!/usr/bin/env python3
"""
Basic usage example for Grokipedia Ontology.

This example demonstrates how to:
1. Create concepts and relations programmatically
2. Build a knowledge graph
3. Query the ontology
4. Export to different formats
"""

import asyncio
from pathlib import Path

from grokipedia_ontology import (
    GrokipediaFetcher,
    GrokipediaOntology,
    KnowledgeGraph,
    Concept,
    Relation,
)
from grokipedia_ontology.models import ConceptType, RelationType


def create_manual_ontology() -> GrokipediaOntology:
    """Create an ontology with manually defined concepts."""
    print("Creating ontology with manual concepts...")

    ontology = GrokipediaOntology()

    # Add concepts
    ai_concept = Concept(
        name="Artificial_Intelligence",
        label="Artificial Intelligence",
        description="The simulation of human intelligence by machines.",
        concept_type=ConceptType.TECHNOLOGY,
        categories=["Computer Science", "Technology"],
    )

    ml_concept = Concept(
        name="Machine_Learning",
        label="Machine Learning",
        description="A subset of AI that enables systems to learn from data.",
        concept_type=ConceptType.TECHNOLOGY,
        categories=["Computer Science", "AI"],
        parent_concepts=["Artificial_Intelligence"],
    )

    dl_concept = Concept(
        name="Deep_Learning",
        label="Deep Learning",
        description="Neural networks with multiple layers for complex pattern recognition.",
        concept_type=ConceptType.TECHNOLOGY,
        categories=["Machine Learning", "Neural Networks"],
        parent_concepts=["Machine_Learning"],
    )

    nlp_concept = Concept(
        name="Natural_Language_Processing",
        label="Natural Language Processing",
        description="AI techniques for understanding human language.",
        concept_type=ConceptType.TECHNOLOGY,
        categories=["AI", "Linguistics"],
    )

    llm_concept = Concept(
        name="Large_Language_Model",
        label="Large Language Model",
        description="Neural network models trained on vast text data for language tasks.",
        concept_type=ConceptType.TECHNOLOGY,
        categories=["NLP", "Deep Learning"],
    )

    # Add concepts to ontology
    for concept in [ai_concept, ml_concept, dl_concept, nlp_concept, llm_concept]:
        ontology.add_concept(concept)
        print(f"  Added: {concept.label}")

    # Add relations
    relations = [
        Relation(
            subject="Machine_Learning",
            predicate=RelationType.IS_A,
            object="Artificial_Intelligence",
        ),
        Relation(
            subject="Deep_Learning",
            predicate=RelationType.IS_A,
            object="Machine_Learning",
        ),
        Relation(
            subject="Natural_Language_Processing",
            predicate=RelationType.PART_OF,
            object="Artificial_Intelligence",
        ),
        Relation(
            subject="Large_Language_Model",
            predicate=RelationType.IS_A,
            object="Deep_Learning",
        ),
        Relation(
            subject="Large_Language_Model",
            predicate=RelationType.USED_FOR,
            object="Natural_Language_Processing",
        ),
    ]

    for relation in relations:
        ontology.add_relation(relation)
        print(f"  Relation: {relation.subject} --{relation.predicate.value}--> {relation.object}")

    return ontology


def demonstrate_knowledge_graph() -> KnowledgeGraph:
    """Demonstrate knowledge graph features."""
    print("\nBuilding knowledge graph...")

    graph = KnowledgeGraph()

    # Add concepts
    concepts = [
        Concept(name="Grok", label="Grok", description="AI assistant by xAI", concept_type=ConceptType.TECHNOLOGY),
        Concept(name="xAI", label="xAI", description="AI company founded by Elon Musk", concept_type=ConceptType.ORGANIZATION),
        Concept(name="Grokipedia", label="Grokipedia", description="AI-generated encyclopedia", concept_type=ConceptType.WORK),
        Concept(name="Encyclopedia", label="Encyclopedia", description="Comprehensive reference work", concept_type=ConceptType.ABSTRACT),
        Concept(name="Wikipedia", label="Wikipedia", description="Free online encyclopedia", concept_type=ConceptType.WORK),
    ]

    for concept in concepts:
        graph.add_concept(concept)

    # Add relations
    relations = [
        Relation(subject="Grok", predicate=RelationType.DERIVED_FROM, object="xAI"),
        Relation(subject="Grokipedia", predicate=RelationType.DERIVED_FROM, object="Grok"),
        Relation(subject="Grokipedia", predicate=RelationType.IS_A, object="Encyclopedia"),
        Relation(subject="Wikipedia", predicate=RelationType.IS_A, object="Encyclopedia"),
        Relation(subject="Grokipedia", predicate=RelationType.RELATED_TO, object="Wikipedia"),
    ]

    for relation in relations:
        graph.add_relation(relation)

    # Demonstrate graph operations
    print("\nGraph operations:")

    # Get neighbors
    neighbors = graph.get_neighbors("Grokipedia")
    print(f"  Neighbors of Grokipedia: {neighbors}")

    # Find path
    path = graph.find_path("xAI", "Encyclopedia")
    print(f"  Path from xAI to Encyclopedia: {path}")

    # Get centrality
    centrality = graph.get_centrality(method="degree", top_n=3)
    print(f"  Top 3 central concepts: {centrality}")

    # Get stats
    stats = graph.get_stats()
    print(f"  Total concepts: {stats.total_concepts}")
    print(f"  Total relations: {stats.total_relations}")

    return graph


def query_ontology(ontology: GrokipediaOntology) -> None:
    """Demonstrate SPARQL querying."""
    print("\nSPARQL Queries:")

    # Query all concepts
    query = """
    PREFIX grok: <http://grokipedia.org/ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?concept ?label WHERE {
        ?concept rdfs:label ?label .
    }
    LIMIT 10
    """

    results = ontology.query(query)
    print("  All concepts:")
    for row in results:
        print(f"    - {row.get('label', 'N/A')}")


def export_ontology(ontology: GrokipediaOntology, output_dir: Path) -> None:
    """Export ontology to various formats."""
    print("\nExporting ontology:")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Export to Turtle
    turtle_path = output_dir / "ontology.ttl"
    ontology.save(turtle_path, format="turtle")
    print(f"  Saved Turtle: {turtle_path}")

    # Export to RDF/XML
    xml_path = output_dir / "ontology.rdf"
    ontology.save(xml_path, format="xml")
    print(f"  Saved RDF/XML: {xml_path}")

    # Export to JSON-LD
    jsonld_path = output_dir / "ontology.jsonld"
    ontology.save(jsonld_path, format="json-ld")
    print(f"  Saved JSON-LD: {jsonld_path}")


async def fetch_from_grokipedia() -> None:
    """Demonstrate fetching from Grokipedia (may not work due to access restrictions)."""
    print("\nAttempting to fetch from Grokipedia...")

    async with GrokipediaFetcher() as fetcher:
        # Try fetching a topic
        article = await fetcher.fetch_article("Artificial_intelligence")

        if article:
            print(f"  Fetched: {article.title}")
            print(f"  Summary: {article.summary[:200]}...")

            # Convert to ontology
            ontology = GrokipediaOntology()
            ontology.add_article(article)
            print(f"  Added to ontology with {len(article.links)} related links")
        else:
            print("  Could not fetch article (access may be restricted)")


def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("Grokipedia Ontology - Basic Usage Examples")
    print("=" * 60)

    # Create manual ontology
    ontology = create_manual_ontology()

    # Run inference
    print("\nRunning inference...")
    inferred = ontology.infer_relations()
    print(f"  Inferred {len(inferred)} new relations")

    # Demonstrate knowledge graph
    graph = demonstrate_knowledge_graph()

    # Query ontology
    query_ontology(ontology)

    # Export
    output_dir = Path("output")
    export_ontology(ontology, output_dir)

    # Try fetching from Grokipedia
    try:
        asyncio.run(fetch_from_grokipedia())
    except Exception as e:
        print(f"  Fetch failed: {e}")

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
