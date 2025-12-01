#!/usr/bin/env python3
"""
Generate sample ontology data for CLI demonstration.

This script creates a sample knowledge graph about AI technologies
that can be used to demonstrate CLI commands.
"""

from pathlib import Path

from grokipedia_ontology import KnowledgeGraph, Concept, Relation
from grokipedia_ontology.models import ConceptType, RelationType


def create_ai_knowledge_graph() -> KnowledgeGraph:
    """Create a sample knowledge graph about AI technologies."""
    graph = KnowledgeGraph()

    # === CORE AI CONCEPTS ===
    concepts = [
        # Technology concepts
        Concept(
            name="Artificial_Intelligence",
            label="Artificial Intelligence",
            description="The simulation of human intelligence processes by machines, especially computer systems. These processes include learning, reasoning, and self-correction.",
            concept_type=ConceptType.TECHNOLOGY,
            categories=["Computer Science", "Technology", "Cognitive Science"],
            aliases=["AI", "Machine Intelligence"],
        ),
        Concept(
            name="Machine_Learning",
            label="Machine Learning",
            description="A subset of AI that provides systems the ability to automatically learn and improve from experience without being explicitly programmed.",
            concept_type=ConceptType.TECHNOLOGY,
            categories=["AI", "Computer Science", "Statistics"],
            aliases=["ML"],
        ),
        Concept(
            name="Deep_Learning",
            label="Deep Learning",
            description="A subset of machine learning based on artificial neural networks with representation learning. It can be supervised, semi-supervised or unsupervised.",
            concept_type=ConceptType.TECHNOLOGY,
            categories=["Machine Learning", "Neural Networks"],
            aliases=["DL", "Deep Neural Networks"],
        ),
        Concept(
            name="Natural_Language_Processing",
            label="Natural Language Processing",
            description="A subfield of AI focused on the interaction between computers and humans through natural language. The goal is to enable computers to understand, interpret, and generate human language.",
            concept_type=ConceptType.TECHNOLOGY,
            categories=["AI", "Linguistics", "Computer Science"],
            aliases=["NLP"],
        ),
        Concept(
            name="Computer_Vision",
            label="Computer Vision",
            description="A field of AI that trains computers to interpret and understand the visual world. Using digital images and deep learning models, machines can accurately identify and classify objects.",
            concept_type=ConceptType.TECHNOLOGY,
            categories=["AI", "Image Processing"],
            aliases=["CV"],
        ),
        Concept(
            name="Large_Language_Model",
            label="Large Language Model",
            description="A type of AI model trained on vast amounts of text data to understand and generate human-like text. LLMs are the foundation of modern chatbots and AI assistants.",
            concept_type=ConceptType.TECHNOLOGY,
            categories=["NLP", "Deep Learning", "Generative AI"],
            aliases=["LLM"],
        ),
        Concept(
            name="Neural_Network",
            label="Neural Network",
            description="A computing system inspired by biological neural networks. It consists of interconnected nodes (neurons) that process information using connectionist approaches.",
            concept_type=ConceptType.TECHNOLOGY,
            categories=["Machine Learning", "Computer Science"],
            aliases=["ANN", "Artificial Neural Network"],
        ),
        Concept(
            name="Transformer",
            label="Transformer",
            description="A deep learning architecture that uses self-attention mechanisms. Transformers are the basis for models like GPT, BERT, and other modern language models.",
            concept_type=ConceptType.TECHNOLOGY,
            categories=["Deep Learning", "NLP"],
        ),
        Concept(
            name="Reinforcement_Learning",
            label="Reinforcement Learning",
            description="An area of machine learning where an agent learns to make decisions by performing actions and receiving rewards or penalties.",
            concept_type=ConceptType.TECHNOLOGY,
            categories=["Machine Learning", "AI"],
            aliases=["RL"],
        ),
        Concept(
            name="Generative_AI",
            label="Generative AI",
            description="AI systems capable of generating new content including text, images, audio, and video based on patterns learned from training data.",
            concept_type=ConceptType.TECHNOLOGY,
            categories=["AI", "Deep Learning", "Creative AI"],
            aliases=["GenAI"],
        ),
        # Organizations
        Concept(
            name="OpenAI",
            label="OpenAI",
            description="An American artificial intelligence research laboratory. OpenAI created ChatGPT and the GPT series of language models.",
            concept_type=ConceptType.ORGANIZATION,
            categories=["AI Companies", "Research Labs"],
            properties={"founded": "2015", "headquarters": "San Francisco"},
        ),
        Concept(
            name="xAI",
            label="xAI",
            description="An artificial intelligence company founded by Elon Musk. xAI developed Grok, an AI assistant, and operates Grokipedia.",
            concept_type=ConceptType.ORGANIZATION,
            categories=["AI Companies", "Technology"],
            properties={"founded": "2023", "founder": "Elon Musk"},
        ),
        Concept(
            name="Anthropic",
            label="Anthropic",
            description="An AI safety company that develops Claude, a large language model designed to be helpful, harmless, and honest.",
            concept_type=ConceptType.ORGANIZATION,
            categories=["AI Companies", "AI Safety"],
            properties={"founded": "2021"},
        ),
        Concept(
            name="Google_DeepMind",
            label="Google DeepMind",
            description="An AI research laboratory that created AlphaGo, AlphaFold, and Gemini. Known for breakthrough research in deep learning and reinforcement learning.",
            concept_type=ConceptType.ORGANIZATION,
            categories=["AI Companies", "Research Labs"],
        ),
        # AI Systems/Products
        Concept(
            name="ChatGPT",
            label="ChatGPT",
            description="An AI chatbot developed by OpenAI based on the GPT architecture. It can engage in conversational dialogue and assist with various tasks.",
            concept_type=ConceptType.TECHNOLOGY,
            categories=["Chatbots", "LLM Applications"],
            properties={"developer": "OpenAI", "released": "2022"},
        ),
        Concept(
            name="Claude",
            label="Claude",
            description="An AI assistant developed by Anthropic. Claude is designed to be helpful, harmless, and honest, with a focus on safety and reliability.",
            concept_type=ConceptType.TECHNOLOGY,
            categories=["Chatbots", "LLM Applications"],
            properties={"developer": "Anthropic"},
        ),
        Concept(
            name="Grok",
            label="Grok",
            description="An AI assistant developed by xAI. Grok is known for its wit and willingness to answer provocative questions.",
            concept_type=ConceptType.TECHNOLOGY,
            categories=["Chatbots", "LLM Applications"],
            properties={"developer": "xAI"},
        ),
        Concept(
            name="Grokipedia",
            label="Grokipedia",
            description="An AI-generated online encyclopedia operated by xAI. Articles are generated by Grok, making it the first major AI-generated encyclopedia.",
            concept_type=ConceptType.WORK,
            categories=["Encyclopedia", "AI Content"],
            properties={"launched": "2025", "operator": "xAI"},
        ),
        # People
        Concept(
            name="Alan_Turing",
            label="Alan Turing",
            description="British mathematician and computer scientist, considered the father of theoretical computer science and AI. Created the Turing Test.",
            concept_type=ConceptType.PERSON,
            categories=["Scientists", "Computer Science Pioneers"],
            properties={"birth_year": "1912", "death_year": "1954"},
        ),
        Concept(
            name="Geoffrey_Hinton",
            label="Geoffrey Hinton",
            description="British-Canadian cognitive psychologist and computer scientist, known as a 'Godfather of AI'. Pioneer in deep learning and neural networks.",
            concept_type=ConceptType.PERSON,
            categories=["Scientists", "AI Researchers"],
            properties={"birth_year": "1947"},
        ),
        # Abstract concepts
        Concept(
            name="Turing_Test",
            label="Turing Test",
            description="A test of a machine's ability to exhibit intelligent behavior indistinguishable from a human. Proposed by Alan Turing in 1950.",
            concept_type=ConceptType.ABSTRACT,
            categories=["AI Theory", "Philosophy of Mind"],
        ),
        Concept(
            name="AI_Safety",
            label="AI Safety",
            description="A research field focused on making AI systems safe, beneficial, and aligned with human values. Addresses risks from advanced AI systems.",
            concept_type=ConceptType.ABSTRACT,
            categories=["AI Research", "Ethics"],
        ),
    ]

    # Add all concepts
    for concept in concepts:
        graph.add_concept(concept)

    # === RELATIONS ===
    relations = [
        # IS_A (taxonomy)
        Relation(subject="Machine_Learning", predicate=RelationType.IS_A, object="Artificial_Intelligence"),
        Relation(subject="Deep_Learning", predicate=RelationType.IS_A, object="Machine_Learning"),
        Relation(subject="Natural_Language_Processing", predicate=RelationType.IS_A, object="Artificial_Intelligence"),
        Relation(subject="Computer_Vision", predicate=RelationType.IS_A, object="Artificial_Intelligence"),
        Relation(subject="Reinforcement_Learning", predicate=RelationType.IS_A, object="Machine_Learning"),
        Relation(subject="Large_Language_Model", predicate=RelationType.IS_A, object="Deep_Learning"),
        Relation(subject="Generative_AI", predicate=RelationType.IS_A, object="Artificial_Intelligence"),
        Relation(subject="Transformer", predicate=RelationType.IS_A, object="Neural_Network"),
        Relation(subject="ChatGPT", predicate=RelationType.IS_A, object="Large_Language_Model"),
        Relation(subject="Claude", predicate=RelationType.IS_A, object="Large_Language_Model"),
        Relation(subject="Grok", predicate=RelationType.IS_A, object="Large_Language_Model"),

        # PART_OF
        Relation(subject="Neural_Network", predicate=RelationType.PART_OF, object="Deep_Learning"),
        Relation(subject="Transformer", predicate=RelationType.PART_OF, object="Large_Language_Model"),

        # DERIVED_FROM (created by)
        Relation(subject="ChatGPT", predicate=RelationType.DERIVED_FROM, object="OpenAI"),
        Relation(subject="Claude", predicate=RelationType.DERIVED_FROM, object="Anthropic"),
        Relation(subject="Grok", predicate=RelationType.DERIVED_FROM, object="xAI"),
        Relation(subject="Grokipedia", predicate=RelationType.DERIVED_FROM, object="Grok"),
        Relation(subject="Grokipedia", predicate=RelationType.DERIVED_FROM, object="xAI"),
        Relation(subject="Turing_Test", predicate=RelationType.DERIVED_FROM, object="Alan_Turing"),

        # USED_FOR
        Relation(subject="Large_Language_Model", predicate=RelationType.USED_FOR, object="Natural_Language_Processing"),
        Relation(subject="Deep_Learning", predicate=RelationType.USED_FOR, object="Computer_Vision"),
        Relation(subject="Transformer", predicate=RelationType.USED_FOR, object="Natural_Language_Processing"),
        Relation(subject="Neural_Network", predicate=RelationType.USED_FOR, object="Machine_Learning"),
        Relation(subject="Turing_Test", predicate=RelationType.USED_FOR, object="Artificial_Intelligence"),

        # RELATED_TO
        Relation(subject="OpenAI", predicate=RelationType.RELATED_TO, object="Anthropic"),
        Relation(subject="OpenAI", predicate=RelationType.RELATED_TO, object="xAI"),
        Relation(subject="Geoffrey_Hinton", predicate=RelationType.RELATED_TO, object="Deep_Learning"),
        Relation(subject="Geoffrey_Hinton", predicate=RelationType.RELATED_TO, object="Google_DeepMind"),
        Relation(subject="Alan_Turing", predicate=RelationType.RELATED_TO, object="Artificial_Intelligence"),
        Relation(subject="AI_Safety", predicate=RelationType.RELATED_TO, object="Anthropic"),
        Relation(subject="Generative_AI", predicate=RelationType.RELATED_TO, object="Large_Language_Model"),

        # SUPPORTS
        Relation(subject="AI_Safety", predicate=RelationType.SUPPORTS, object="Artificial_Intelligence"),
    ]

    # Add all relations
    for relation in relations:
        graph.add_relation(relation)

    return graph


def main() -> None:
    """Generate sample data files."""
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("Generating Sample AI Knowledge Graph")
    print("=" * 60)

    # Create knowledge graph
    graph = create_ai_knowledge_graph()

    # Run inference
    print("\nRunning inference on relations...")
    inferred = graph.ontology.infer_relations()
    print(f"  Inferred {len(inferred)} additional relations")

    # Get stats
    stats = graph.get_stats()
    print(f"\nKnowledge Graph Statistics:")
    print(f"  Total Concepts: {stats.total_concepts}")
    print(f"  Total Relations: {stats.total_relations}")
    print(f"  Avg Relations/Concept: {stats.average_relations_per_concept:.2f}")

    # Save in different formats
    print("\nSaving ontology in multiple formats...")

    # Turtle format
    turtle_path = output_dir / "ai_knowledge_graph.ttl"
    graph.ontology.save(turtle_path, format="turtle")
    print(f"  Saved: {turtle_path}")

    # RDF/XML format
    xml_path = output_dir / "ai_knowledge_graph.rdf"
    graph.ontology.save(xml_path, format="xml")
    print(f"  Saved: {xml_path}")

    # JSON-LD format
    jsonld_path = output_dir / "ai_knowledge_graph.jsonld"
    graph.ontology.save(jsonld_path, format="json-ld")
    print(f"  Saved: {jsonld_path}")

    # GraphML for visualization tools (requires cleaning None values)
    try:
        graphml_path = output_dir / "ai_knowledge_graph.graphml"
        graph.export_graphml(str(graphml_path))
        print(f"  Saved: {graphml_path}")
    except Exception as e:
        print(f"  Skipped GraphML (optional): {e}")

    # Save graph data as JSON
    import json
    json_path = output_dir / "ai_knowledge_graph_data.json"
    json_path.write_text(json.dumps(graph.to_dict(), indent=2, default=str))
    print(f"  Saved: {json_path}")

    print("\n" + "=" * 60)
    print("Sample data generation complete!")
    print("=" * 60)
    print(f"\nOutput files are in: {output_dir.absolute()}")
    print("\nYou can now use CLI commands on these files:")
    print(f"  grokipedia-ontology stats {turtle_path}")
    print(f"  grokipedia-ontology search {turtle_path} 'learning'")
    print(f"  grokipedia-ontology query {turtle_path} --list")


if __name__ == "__main__":
    main()
