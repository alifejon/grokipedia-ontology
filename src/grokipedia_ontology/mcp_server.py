"""
MCP (Model Context Protocol) server for Grokipedia Ontology.

Exposes knowledge graph functionality as MCP tools that can be used
by AI assistants like Claude.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from grokipedia_ontology.models import Concept, Relation, ConceptType, RelationType
from grokipedia_ontology.graph import KnowledgeGraph
from grokipedia_ontology.ontology import GrokipediaOntology
from grokipedia_ontology.search import SearchIndex
from grokipedia_ontology.fetcher import GrokipediaFetcher
from grokipedia_ontology.utils import get_logger

logger = get_logger(__name__)

# Check if MCP is available
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        TextContent,
        Resource,
        ResourceTemplate,
        Prompt,
        PromptArgument,
        PromptMessage,
        GetPromptResult,
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


class OntologyMCPServer:
    """
    MCP Server for Grokipedia Ontology.

    Provides tools for:
    - Searching concepts
    - Getting concept details
    - Finding neighbors and paths
    - Adding concepts and relations
    - Querying statistics
    """

    def __init__(self, data_path: Path | None = None) -> None:
        """
        Initialize the MCP server.

        Args:
            data_path: Path to data file to load (JSON or TTL)
        """
        if not MCP_AVAILABLE:
            raise ImportError(
                "MCP is required for the MCP server. "
                "Install with: pip install grokipedia-ontology[mcp]"
            )

        self.graph: KnowledgeGraph | None = None
        self.search_index: SearchIndex | None = None
        self.data_path = data_path
        self.server = Server("grokipedia-ontology")

        if data_path:
            self.load_data(data_path)

        self._register_handlers()

    def load_data(self, path: Path) -> None:
        """Load data from file."""
        self.data_path = path

        if path.suffix == ".json":
            data = json.loads(path.read_text())
            self.graph = KnowledgeGraph()

            for concept_data in data.get("concepts", []):
                concept = Concept(**concept_data)
                self.graph.add_concept(concept)

            for rel_data in data.get("relations", []):
                relation = Relation(**rel_data)
                self.graph.add_relation(relation)
        else:
            ontology = GrokipediaOntology()
            ontology.load(path)
            self.graph = KnowledgeGraph(ontology)

        # Build search index
        self.search_index = SearchIndex()
        if self.graph:
            self.search_index.index_graph(self.graph)

        logger.info(f"Loaded {len(self.graph) if self.graph else 0} concepts from {path}")

    def _register_handlers(self) -> None:
        """Register MCP tools, resources, and prompts."""
        self._register_tools()
        self._register_resources()
        self._register_prompts()

    def _register_tools(self) -> None:
        """Register MCP tools."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="search_concepts",
                    description="Search for concepts in the knowledge graph by keyword. Returns matching concepts with relevance scores.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (e.g., 'machine learning', 'Python')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 10)",
                                "default": 10
                            },
                            "concept_type": {
                                "type": "string",
                                "description": "Filter by concept type (e.g., 'technology', 'person', 'organization')",
                                "enum": [t.value for t in ConceptType]
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_concept",
                    description="Get detailed information about a specific concept by name.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Concept name (e.g., 'Machine_Learning', 'Python')"
                            }
                        },
                        "required": ["name"]
                    }
                ),
                Tool(
                    name="get_neighbors",
                    description="Get concepts that are directly connected to a given concept.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Concept name to find neighbors for"
                            },
                            "direction": {
                                "type": "string",
                                "description": "Direction of relations: 'in', 'out', or 'both'",
                                "enum": ["in", "out", "both"],
                                "default": "both"
                            },
                            "relation_type": {
                                "type": "string",
                                "description": "Filter by relation type",
                                "enum": [t.value for t in RelationType]
                            }
                        },
                        "required": ["name"]
                    }
                ),
                Tool(
                    name="find_path",
                    description="Find the shortest path between two concepts in the knowledge graph.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "source": {
                                "type": "string",
                                "description": "Starting concept name"
                            },
                            "target": {
                                "type": "string",
                                "description": "Target concept name"
                            },
                            "max_length": {
                                "type": "integer",
                                "description": "Maximum path length (default: 5)",
                                "default": 5
                            }
                        },
                        "required": ["source", "target"]
                    }
                ),
                Tool(
                    name="get_relations",
                    description="Get relations involving a concept or between two concepts.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "subject": {
                                "type": "string",
                                "description": "Subject concept name (optional)"
                            },
                            "object": {
                                "type": "string",
                                "description": "Object concept name (optional)"
                            },
                            "predicate": {
                                "type": "string",
                                "description": "Relation type filter",
                                "enum": [t.value for t in RelationType]
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results (default: 20)",
                                "default": 20
                            }
                        }
                    }
                ),
                Tool(
                    name="get_stats",
                    description="Get statistics about the knowledge graph (concept counts, relation counts, top connected concepts).",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="add_concept",
                    description="Add a new concept to the knowledge graph.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Unique concept name (use underscores for spaces)"
                            },
                            "label": {
                                "type": "string",
                                "description": "Human-readable label"
                            },
                            "description": {
                                "type": "string",
                                "description": "Concept description"
                            },
                            "concept_type": {
                                "type": "string",
                                "description": "Type of concept",
                                "enum": [t.value for t in ConceptType],
                                "default": "entity"
                            },
                            "categories": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Categories this concept belongs to"
                            }
                        },
                        "required": ["name", "label"]
                    }
                ),
                Tool(
                    name="add_relation",
                    description="Add a new relation between two concepts.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "subject": {
                                "type": "string",
                                "description": "Subject concept name"
                            },
                            "predicate": {
                                "type": "string",
                                "description": "Relation type",
                                "enum": [t.value for t in RelationType]
                            },
                            "object": {
                                "type": "string",
                                "description": "Object concept name"
                            },
                            "confidence": {
                                "type": "number",
                                "description": "Confidence score (0.0-1.0)",
                                "default": 1.0
                            }
                        },
                        "required": ["subject", "predicate", "object"]
                    }
                ),
                Tool(
                    name="list_concept_types",
                    description="List all available concept types.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="list_relation_types",
                    description="List all available relation types.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                # Real-time Grokipedia tools
                Tool(
                    name="fetch_grokipedia_article",
                    description="Fetch an article from Grokipedia in real-time. Use this to get the latest information about any topic directly from grokipedia.com.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "Topic name to fetch (e.g., 'Machine Learning', 'Python'). Spaces will be converted to underscores."
                            },
                            "add_to_graph": {
                                "type": "boolean",
                                "description": "Whether to add the fetched article to the local knowledge graph (default: true)",
                                "default": True
                            }
                        },
                        "required": ["topic"]
                    }
                ),
                Tool(
                    name="discover_grokipedia_articles",
                    description="Discover related articles from Grokipedia starting from a topic. Crawls links to find connected articles.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start_topic": {
                                "type": "string",
                                "description": "Starting topic for discovery"
                            },
                            "max_depth": {
                                "type": "integer",
                                "description": "Maximum link depth to follow (default: 1)",
                                "default": 1
                            },
                            "max_articles": {
                                "type": "integer",
                                "description": "Maximum number of articles to fetch (default: 5)",
                                "default": 5
                            },
                            "add_to_graph": {
                                "type": "boolean",
                                "description": "Whether to add fetched articles to the local knowledge graph (default: true)",
                                "default": True
                            }
                        },
                        "required": ["start_topic"]
                    }
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            try:
                result = await self._handle_tool(name, arguments)
                return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
            except Exception as e:
                logger.error(f"Tool error: {e}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async def _handle_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle a tool call."""

        if name == "search_concepts":
            return self._search_concepts(
                query=arguments["query"],
                limit=arguments.get("limit", 10),
                concept_type=arguments.get("concept_type"),
            )

        elif name == "get_concept":
            return self._get_concept(arguments["name"])

        elif name == "get_neighbors":
            return self._get_neighbors(
                name=arguments["name"],
                direction=arguments.get("direction", "both"),
                relation_type=arguments.get("relation_type"),
            )

        elif name == "find_path":
            return self._find_path(
                source=arguments["source"],
                target=arguments["target"],
                max_length=arguments.get("max_length", 5),
            )

        elif name == "get_relations":
            return self._get_relations(
                subject=arguments.get("subject"),
                object=arguments.get("object"),
                predicate=arguments.get("predicate"),
                limit=arguments.get("limit", 20),
            )

        elif name == "get_stats":
            return self._get_stats()

        elif name == "add_concept":
            return self._add_concept(
                name=arguments["name"],
                label=arguments["label"],
                description=arguments.get("description", ""),
                concept_type=arguments.get("concept_type", "entity"),
                categories=arguments.get("categories", []),
            )

        elif name == "add_relation":
            return self._add_relation(
                subject=arguments["subject"],
                predicate=arguments["predicate"],
                object=arguments["object"],
                confidence=arguments.get("confidence", 1.0),
            )

        elif name == "list_concept_types":
            return {"types": [t.value for t in ConceptType]}

        elif name == "list_relation_types":
            return {"types": [t.value for t in RelationType]}

        # Real-time Grokipedia tools
        elif name == "fetch_grokipedia_article":
            return await self._fetch_grokipedia_article(
                topic=arguments["topic"],
                add_to_graph=arguments.get("add_to_graph", True),
            )

        elif name == "discover_grokipedia_articles":
            return await self._discover_grokipedia_articles(
                start_topic=arguments["start_topic"],
                max_depth=arguments.get("max_depth", 1),
                max_articles=arguments.get("max_articles", 5),
                add_to_graph=arguments.get("add_to_graph", True),
            )

        else:
            return {"error": f"Unknown tool: {name}"}

    def _register_resources(self) -> None:
        """Register MCP resources."""

        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """List available resources."""
            resources = [
                Resource(
                    uri="ontology://stats",
                    name="Knowledge Graph Statistics",
                    description="Overall statistics about the knowledge graph",
                    mimeType="application/json",
                ),
                Resource(
                    uri="ontology://concepts",
                    name="All Concepts",
                    description="List of all concepts in the knowledge graph",
                    mimeType="application/json",
                ),
                Resource(
                    uri="ontology://relations",
                    name="All Relations",
                    description="List of all relations in the knowledge graph",
                    mimeType="application/json",
                ),
                Resource(
                    uri="ontology://types",
                    name="Available Types",
                    description="List of available concept and relation types",
                    mimeType="application/json",
                ),
            ]

            # Add dynamic concept resources if data is loaded
            if self.graph:
                for concept in list(self.graph.iterate_concepts())[:50]:
                    resources.append(Resource(
                        uri=f"ontology://concepts/{concept.name}",
                        name=concept.label,
                        description=f"{concept.concept_type.value}: {concept.description[:100] if concept.description else 'No description'}",
                        mimeType="application/json",
                    ))

            return resources

        @self.server.list_resource_templates()
        async def list_resource_templates() -> list[ResourceTemplate]:
            """List resource templates for dynamic resources."""
            return [
                ResourceTemplate(
                    uriTemplate="ontology://concepts/{name}",
                    name="Concept Details",
                    description="Get detailed information about a specific concept",
                    mimeType="application/json",
                ),
                ResourceTemplate(
                    uriTemplate="ontology://neighbors/{name}",
                    name="Concept Neighbors",
                    description="Get concepts connected to a specific concept",
                    mimeType="application/json",
                ),
                ResourceTemplate(
                    uriTemplate="ontology://search/{query}",
                    name="Search Results",
                    description="Search for concepts matching a query",
                    mimeType="application/json",
                ),
            ]

        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read a resource by URI."""
            try:
                result = self._handle_resource(uri)
                return json.dumps(result, indent=2, default=str)
            except Exception as e:
                logger.error(f"Resource error: {e}")
                return json.dumps({"error": str(e)})

    def _handle_resource(self, uri: str) -> dict[str, Any]:
        """Handle a resource read request."""
        # Parse URI
        if not uri.startswith("ontology://"):
            return {"error": f"Invalid URI scheme: {uri}"}

        path = uri[len("ontology://"):]
        parts = path.split("/")

        if path == "stats":
            return self._get_stats()

        elif path == "concepts":
            graph = self._ensure_loaded()
            concepts = []
            for concept in graph.iterate_concepts():
                concepts.append({
                    "name": concept.name,
                    "label": concept.label,
                    "type": concept.concept_type.value,
                })
            return {"total": len(concepts), "concepts": concepts}

        elif path == "relations":
            graph = self._ensure_loaded()
            relations = []
            for source, target, data in graph.iterate_relations():
                relations.append({
                    "subject": source,
                    "predicate": data.get("relation_type", "related_to"),
                    "object": target,
                })
            return {"total": len(relations), "relations": relations}

        elif path == "types":
            return {
                "concept_types": [t.value for t in ConceptType],
                "relation_types": [t.value for t in RelationType],
            }

        elif parts[0] == "concepts" and len(parts) == 2:
            return self._get_concept(parts[1])

        elif parts[0] == "neighbors" and len(parts) == 2:
            return self._get_neighbors(parts[1])

        elif parts[0] == "search" and len(parts) == 2:
            return self._search_concepts(parts[1])

        else:
            return {"error": f"Unknown resource: {uri}"}

    def _register_prompts(self) -> None:
        """Register MCP prompts."""

        @self.server.list_prompts()
        async def list_prompts() -> list[Prompt]:
            """List available prompts."""
            return [
                Prompt(
                    name="explore_concept",
                    description="Explore and explain a concept from the knowledge graph in detail",
                    arguments=[
                        PromptArgument(
                            name="concept_name",
                            description="Name of the concept to explore (e.g., 'Machine_Learning')",
                            required=True,
                        ),
                    ],
                ),
                Prompt(
                    name="find_connections",
                    description="Find and explain connections between two concepts",
                    arguments=[
                        PromptArgument(
                            name="concept_a",
                            description="First concept name",
                            required=True,
                        ),
                        PromptArgument(
                            name="concept_b",
                            description="Second concept name",
                            required=True,
                        ),
                    ],
                ),
                Prompt(
                    name="summarize_domain",
                    description="Summarize concepts in a specific domain or category",
                    arguments=[
                        PromptArgument(
                            name="domain",
                            description="Domain or category to summarize (e.g., 'AI', 'technology')",
                            required=True,
                        ),
                    ],
                ),
                Prompt(
                    name="compare_concepts",
                    description="Compare and contrast two or more concepts",
                    arguments=[
                        PromptArgument(
                            name="concepts",
                            description="Comma-separated list of concept names to compare",
                            required=True,
                        ),
                    ],
                ),
                Prompt(
                    name="knowledge_qa",
                    description="Answer a question using the knowledge graph",
                    arguments=[
                        PromptArgument(
                            name="question",
                            description="Question to answer",
                            required=True,
                        ),
                    ],
                ),
            ]

        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
            """Get a prompt by name with arguments."""
            args = arguments or {}

            if name == "explore_concept":
                concept_name = args.get("concept_name", "")
                concept_data = self._get_concept(concept_name)
                neighbors_data = self._get_neighbors(concept_name)

                return GetPromptResult(
                    description=f"Explore the concept: {concept_name}",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"""Please explore and explain the following concept from the knowledge graph:

**Concept:** {concept_name}

**Details:**
```json
{json.dumps(concept_data, indent=2)}
```

**Connected Concepts:**
```json
{json.dumps(neighbors_data, indent=2)}
```

Please provide:
1. A clear explanation of what this concept is
2. Its significance and relationships to other concepts
3. Key insights from the knowledge graph data
"""
                            ),
                        ),
                    ],
                )

            elif name == "find_connections":
                concept_a = args.get("concept_a", "")
                concept_b = args.get("concept_b", "")
                path_data = self._find_path(concept_a, concept_b)
                concept_a_data = self._get_concept(concept_a)
                concept_b_data = self._get_concept(concept_b)

                return GetPromptResult(
                    description=f"Find connections between {concept_a} and {concept_b}",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"""Find and explain the connections between these two concepts:

**Concept A:** {concept_a}
```json
{json.dumps(concept_a_data, indent=2)}
```

**Concept B:** {concept_b}
```json
{json.dumps(concept_b_data, indent=2)}
```

**Path Between Them:**
```json
{json.dumps(path_data, indent=2)}
```

Please explain:
1. How these concepts are related
2. The significance of their connection
3. Any interesting patterns or insights
"""
                            ),
                        ),
                    ],
                )

            elif name == "summarize_domain":
                domain = args.get("domain", "")
                search_data = self._search_concepts(domain, limit=20)
                stats_data = self._get_stats()

                return GetPromptResult(
                    description=f"Summarize the domain: {domain}",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"""Summarize the following domain from the knowledge graph:

**Domain:** {domain}

**Related Concepts:**
```json
{json.dumps(search_data, indent=2)}
```

**Knowledge Graph Stats:**
```json
{json.dumps(stats_data, indent=2)}
```

Please provide:
1. An overview of this domain
2. Key concepts and their relationships
3. Important patterns or hierarchies
4. Suggestions for further exploration
"""
                            ),
                        ),
                    ],
                )

            elif name == "compare_concepts":
                concepts_str = args.get("concepts", "")
                concept_names = [c.strip() for c in concepts_str.split(",")]
                concepts_data = [self._get_concept(name) for name in concept_names]

                return GetPromptResult(
                    description=f"Compare concepts: {concepts_str}",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"""Compare and contrast the following concepts:

**Concepts to Compare:** {', '.join(concept_names)}

**Concept Details:**
```json
{json.dumps(concepts_data, indent=2)}
```

Please provide:
1. Key similarities between these concepts
2. Important differences
3. How they relate to each other
4. When to use or consider each one
"""
                            ),
                        ),
                    ],
                )

            elif name == "knowledge_qa":
                question = args.get("question", "")
                # Extract keywords and search
                search_data = self._search_concepts(question, limit=10)
                stats_data = self._get_stats()

                return GetPromptResult(
                    description=f"Answer: {question}",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"""Answer the following question using the knowledge graph:

**Question:** {question}

**Relevant Concepts Found:**
```json
{json.dumps(search_data, indent=2)}
```

**Knowledge Graph Overview:**
- Total Concepts: {stats_data.get('total_concepts', 0)}
- Total Relations: {stats_data.get('total_relations', 0)}

Please answer the question based on the knowledge graph data. If more information is needed, suggest which tools to use (search_concepts, get_concept, find_path, etc.).
"""
                            ),
                        ),
                    ],
                )

            else:
                return GetPromptResult(
                    description="Unknown prompt",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"Unknown prompt: {name}",
                            ),
                        ),
                    ],
                )

    def _ensure_loaded(self) -> KnowledgeGraph:
        """Ensure data is loaded."""
        if self.graph is None:
            raise ValueError("No data loaded. Please load a data file first.")
        return self.graph

    def _search_concepts(
        self,
        query: str,
        limit: int = 10,
        concept_type: str | None = None,
    ) -> dict[str, Any]:
        """Search for concepts."""
        self._ensure_loaded()

        if not self.search_index:
            return {"error": "Search index not available"}

        ctype = None
        if concept_type:
            try:
                ctype = ConceptType(concept_type)
            except ValueError:
                pass

        hits = self.search_index.search(query, limit=limit, concept_type=ctype)

        return {
            "query": query,
            "total": len(hits),
            "results": [
                {
                    "name": hit.concept_name,
                    "label": hit.label,
                    "type": hit.concept_type,
                    "description": hit.description[:200] if hit.description else "",
                    "score": round(hit.score, 3),
                }
                for hit in hits
            ]
        }

    def _get_concept(self, name: str) -> dict[str, Any]:
        """Get concept details."""
        graph = self._ensure_loaded()

        concept = graph.get_concept(name)
        if not concept:
            return {"error": f"Concept not found: {name}"}

        # Get relations
        out_relations = []
        in_relations = []

        for source, target, data in graph.iterate_relations():
            if source == name:
                out_relations.append({
                    "predicate": data.get("relation_type", "related_to"),
                    "target": target,
                })
            elif target == name:
                in_relations.append({
                    "predicate": data.get("relation_type", "related_to"),
                    "source": source,
                })

        return {
            "name": concept.name,
            "label": concept.label,
            "type": concept.concept_type.value,
            "description": concept.description,
            "categories": concept.categories,
            "aliases": concept.aliases,
            "source_url": str(concept.source_url) if concept.source_url else None,
            "outgoing_relations": out_relations[:20],
            "incoming_relations": in_relations[:20],
        }

    def _get_neighbors(
        self,
        name: str,
        direction: str = "both",
        relation_type: str | None = None,
    ) -> dict[str, Any]:
        """Get neighboring concepts."""
        graph = self._ensure_loaded()

        rel_type = None
        if relation_type:
            try:
                rel_type = RelationType(relation_type)
            except ValueError:
                pass

        neighbors = graph.get_neighbors(name, relation_type=rel_type, direction=direction)

        # Get details for each neighbor
        neighbor_details = []
        for n in neighbors[:30]:
            concept = graph.get_concept(n)
            if concept:
                neighbor_details.append({
                    "name": n,
                    "label": concept.label,
                    "type": concept.concept_type.value,
                })

        return {
            "concept": name,
            "direction": direction,
            "filter": relation_type,
            "count": len(neighbors),
            "neighbors": neighbor_details,
        }

    def _find_path(
        self,
        source: str,
        target: str,
        max_length: int = 5,
    ) -> dict[str, Any]:
        """Find path between concepts."""
        graph = self._ensure_loaded()

        path = graph.find_path(source, target, max_length=max_length)

        if path is None:
            return {
                "found": False,
                "source": source,
                "target": target,
                "message": f"No path found within {max_length} hops",
            }

        # Build detailed path
        path_details = []
        for i, node in enumerate(path):
            concept = graph.get_concept(node)
            detail = {
                "step": i,
                "name": node,
                "label": concept.label if concept else node,
            }
            if i < len(path) - 1:
                # Find relation to next node
                next_node = path[i + 1]
                for _, t, data in graph.graph.out_edges(node, data=True):
                    if t == next_node:
                        detail["relation_to_next"] = data.get("relation_type", "related_to")
                        break
            path_details.append(detail)

        return {
            "found": True,
            "source": source,
            "target": target,
            "length": len(path) - 1,
            "path": path_details,
        }

    def _get_relations(
        self,
        subject: str | None = None,
        object: str | None = None,
        predicate: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Get relations."""
        graph = self._ensure_loaded()

        relations = []
        for source, target, data in graph.iterate_relations():
            rel_type = data.get("relation_type", "related_to")

            if subject and source != subject:
                continue
            if object and target != object:
                continue
            if predicate and rel_type != predicate:
                continue

            relations.append({
                "subject": source,
                "predicate": rel_type,
                "object": target,
                "confidence": data.get("confidence", 1.0),
            })

            if len(relations) >= limit:
                break

        return {
            "filters": {
                "subject": subject,
                "object": object,
                "predicate": predicate,
            },
            "count": len(relations),
            "relations": relations,
        }

    def _get_stats(self) -> dict[str, Any]:
        """Get statistics."""
        graph = self._ensure_loaded()
        stats = graph.get_stats()

        return {
            "total_concepts": stats.total_concepts,
            "total_relations": stats.total_relations,
            "average_relations_per_concept": round(stats.average_relations_per_concept, 2),
            "concepts_by_type": stats.concepts_by_type,
            "relations_by_type": stats.relations_by_type,
            "top_connected_concepts": [
                {"name": name, "connections": count}
                for name, count in stats.top_connected_concepts[:10]
            ],
        }

    def _add_concept(
        self,
        name: str,
        label: str,
        description: str = "",
        concept_type: str = "entity",
        categories: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add a concept."""
        graph = self._ensure_loaded()

        try:
            ctype = ConceptType(concept_type)
        except ValueError:
            ctype = ConceptType.ENTITY

        concept = Concept(
            name=name,
            label=label,
            description=description,
            concept_type=ctype,
            categories=categories or [],
        )

        graph.add_concept(concept)

        # Update search index
        if self.search_index:
            self.search_index.index_concept(concept)

        return {
            "success": True,
            "message": f"Added concept: {name}",
            "concept": {
                "name": name,
                "label": label,
                "type": concept_type,
            }
        }

    def _add_relation(
        self,
        subject: str,
        predicate: str,
        object: str,
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        """Add a relation."""
        graph = self._ensure_loaded()

        try:
            pred = RelationType(predicate)
        except ValueError:
            pred = RelationType.RELATED_TO

        relation = Relation(
            subject=subject,
            predicate=pred,
            object=object,
            confidence=confidence,
        )

        graph.add_relation(relation)

        return {
            "success": True,
            "message": f"Added relation: {subject} --{predicate}--> {object}",
            "relation": {
                "subject": subject,
                "predicate": predicate,
                "object": object,
                "confidence": confidence,
            }
        }

    async def _fetch_grokipedia_article(
        self,
        topic: str,
        add_to_graph: bool = True,
    ) -> dict[str, Any]:
        """Fetch an article from Grokipedia in real-time."""
        try:
            async with GrokipediaFetcher(timeout=30.0, max_retries=2) as fetcher:
                article = await fetcher.fetch_article(topic)

            if article is None:
                return {
                    "success": False,
                    "error": f"Article not found: {topic}",
                    "url": GrokipediaFetcher.build_url(topic),
                }

            # Convert article to concept if add_to_graph is True
            if add_to_graph and self.graph:
                concept = Concept(
                    name=article.slug,
                    label=article.title,
                    description=article.summary or article.content[:500],
                    concept_type=ConceptType.ENTITY,
                    categories=article.categories,
                    source_url=article.url,
                )
                self.graph.add_concept(concept)

                # Index the new concept
                if self.search_index:
                    self.search_index.index_concept(concept)

                # Add relations to linked articles
                for link in article.links[:10]:
                    link_slug = link.replace(" ", "_")
                    relation = Relation(
                        subject=article.slug,
                        predicate=RelationType.RELATED_TO,
                        object=link_slug,
                        confidence=0.8,
                    )
                    try:
                        self.graph.add_relation(relation)
                    except Exception:
                        pass  # Ignore if target doesn't exist

                logger.info(f"Added article '{article.title}' to knowledge graph")

            return {
                "success": True,
                "article": {
                    "title": article.title,
                    "url": str(article.url),
                    "slug": article.slug,
                    "summary": article.summary[:500] if article.summary else "",
                    "categories": article.categories,
                    "links": article.links[:20],
                    "sections": [s["title"] for s in article.sections],
                    "infobox": article.infobox,
                },
                "added_to_graph": add_to_graph and self.graph is not None,
            }

        except Exception as e:
            logger.error(f"Error fetching article '{topic}': {e}")
            return {
                "success": False,
                "error": str(e),
                "topic": topic,
            }

    async def _discover_grokipedia_articles(
        self,
        start_topic: str,
        max_depth: int = 1,
        max_articles: int = 5,
        add_to_graph: bool = True,
    ) -> dict[str, Any]:
        """Discover related articles from Grokipedia."""
        try:
            async with GrokipediaFetcher(
                timeout=30.0,
                max_retries=2,
                delay_between_requests=0.5,
            ) as fetcher:
                articles = await fetcher.discover_related(
                    start_topic,
                    max_depth=max_depth,
                    max_articles=max_articles,
                )

            if not articles:
                return {
                    "success": False,
                    "error": f"No articles found starting from: {start_topic}",
                }

            results = []
            added_count = 0

            for article in articles:
                article_info = {
                    "title": article.title,
                    "url": str(article.url),
                    "slug": article.slug,
                    "summary": article.summary[:200] if article.summary else "",
                    "categories": article.categories,
                    "link_count": len(article.links),
                }
                results.append(article_info)

                # Add to graph if requested
                if add_to_graph and self.graph:
                    concept = Concept(
                        name=article.slug,
                        label=article.title,
                        description=article.summary or article.content[:500],
                        concept_type=ConceptType.ENTITY,
                        categories=article.categories,
                        source_url=article.url,
                    )

                    # Check if concept already exists
                    if not self.graph.get_concept(article.slug):
                        self.graph.add_concept(concept)
                        if self.search_index:
                            self.search_index.index_concept(concept)
                        added_count += 1

            # Add relations between discovered articles
            if add_to_graph and self.graph:
                for article in articles:
                    for link in article.links[:10]:
                        link_slug = link.replace(" ", "_")
                        # Only add relation if target exists in graph
                        if self.graph.get_concept(link_slug):
                            relation = Relation(
                                subject=article.slug,
                                predicate=RelationType.RELATED_TO,
                                object=link_slug,
                                confidence=0.8,
                            )
                            try:
                                self.graph.add_relation(relation)
                            except Exception:
                                pass

            logger.info(f"Discovered {len(articles)} articles, added {added_count} to graph")

            return {
                "success": True,
                "start_topic": start_topic,
                "total_found": len(articles),
                "added_to_graph": added_count,
                "articles": results,
            }

        except Exception as e:
            logger.error(f"Error discovering articles from '{start_topic}': {e}")
            return {
                "success": False,
                "error": str(e),
                "start_topic": start_topic,
            }

    async def run(self) -> None:
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def create_mcp_server(data_path: Path | None = None) -> OntologyMCPServer:
    """Create an MCP server instance."""
    return OntologyMCPServer(data_path)


async def run_mcp_server(data_path: Path) -> None:
    """Run the MCP server."""
    if not MCP_AVAILABLE:
        raise ImportError(
            "MCP is required. Install with: pip install grokipedia-ontology[mcp]"
        )

    server = create_mcp_server(data_path)
    await server.run()
