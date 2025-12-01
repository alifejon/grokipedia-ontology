"""
MCP (Model Context Protocol) server for Grokipedia Ontology.

Exposes knowledge graph functionality as MCP tools that can be used
by AI assistants like Claude.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from grokipedia_ontology.models import Concept, Relation, ConceptType, RelationType
from grokipedia_ontology.graph import KnowledgeGraph
from grokipedia_ontology.ontology import GrokipediaOntology
from grokipedia_ontology.search import SearchIndex
from grokipedia_ontology.utils import get_logger

logger = get_logger(__name__)

# Check if MCP is available
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        TextContent,
        CallToolResult,
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

        self._register_tools()

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

        else:
            return {"error": f"Unknown tool: {name}"}

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
