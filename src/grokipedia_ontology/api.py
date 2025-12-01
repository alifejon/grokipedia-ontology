"""
Web API module for Grokipedia Ontology.

Provides a FastAPI-based REST API and web dashboard for
interacting with knowledge graphs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from grokipedia_ontology.models import (
    Concept,
    ConceptType,
    Relation,
    RelationType,
    OntologyStats,
)
from grokipedia_ontology.graph import KnowledgeGraph
from grokipedia_ontology.ontology import GrokipediaOntology
from grokipedia_ontology.search import SearchIndex, SearchHit
from grokipedia_ontology.utils import get_logger

logger = get_logger(__name__)

# Check if FastAPI is available
try:
    from fastapi import FastAPI, HTTPException, Query, UploadFile, File
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


# ============================================================================
# API Models
# ============================================================================

class ConceptCreate(BaseModel):
    """Model for creating a new concept."""
    name: str = Field(..., description="Unique concept name")
    label: str = Field(..., description="Human-readable label")
    description: str = Field(default="", description="Concept description")
    concept_type: str = Field(default="entity", description="Concept type")
    categories: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)


class RelationCreate(BaseModel):
    """Model for creating a new relation."""
    subject: str = Field(..., description="Subject concept name")
    predicate: str = Field(..., description="Relation type")
    object: str = Field(..., description="Object concept name")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ConceptResponse(BaseModel):
    """Response model for a concept."""
    name: str
    label: str
    description: str
    concept_type: str
    categories: list[str]
    aliases: list[str]
    source_url: str | None = None


class RelationResponse(BaseModel):
    """Response model for a relation."""
    subject: str
    predicate: str
    object: str
    confidence: float


class GraphDataResponse(BaseModel):
    """Response model for graph visualization data."""
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class SearchResponse(BaseModel):
    """Response model for search results."""
    results: list[dict[str, Any]]
    total: int
    query: str


class StatsResponse(BaseModel):
    """Response model for statistics."""
    total_concepts: int
    total_relations: int
    concepts_by_type: dict[str, int]
    relations_by_type: dict[str, int]
    top_connected: list[tuple[str, int]]


# ============================================================================
# Application State
# ============================================================================

class AppState:
    """Global application state."""

    def __init__(self) -> None:
        self.graph: KnowledgeGraph | None = None
        self.search_index: SearchIndex | None = None
        self.data_path: Path | None = None

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

    def ensure_loaded(self) -> KnowledgeGraph:
        """Ensure data is loaded."""
        if self.graph is None:
            raise HTTPException(status_code=400, detail="No data loaded")
        return self.graph


# Global state
state = AppState()


# ============================================================================
# FastAPI Application
# ============================================================================

def create_app(data_path: Path | None = None) -> Any:
    """
    Create and configure the FastAPI application.

    Args:
        data_path: Optional path to load data from

    Returns:
        FastAPI application instance
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI is required for the web interface. "
            "Install with: pip install grokipedia-ontology[web]"
        )

    app = FastAPI(
        title="Grokipedia Ontology API",
        description="REST API for knowledge graph exploration and management",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Load initial data if provided
    if data_path:
        state.load_data(data_path)

    # Mount static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # ========================================================================
    # Routes
    # ========================================================================

    @app.get("/", response_class=HTMLResponse)
    async def root() -> HTMLResponse:
        """Serve the main dashboard."""
        template_path = Path(__file__).parent / "static" / "index.html"
        if template_path.exists():
            return HTMLResponse(content=template_path.read_text())
        return HTMLResponse(content=get_default_html())

    @app.get("/api/health")
    async def health_check() -> dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "data_loaded": state.graph is not None,
            "concept_count": len(state.graph) if state.graph else 0,
        }

    # ------------------------------------------------------------------------
    # Data Management
    # ------------------------------------------------------------------------

    @app.post("/api/load")
    async def load_data(file: UploadFile = File(...)) -> dict[str, Any]:
        """Load data from uploaded file."""
        import tempfile

        # Save uploaded file
        suffix = Path(file.filename or "data").suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            state.load_data(tmp_path)
            return {
                "status": "success",
                "concepts": len(state.graph) if state.graph else 0,
                "filename": file.filename,
            }
        finally:
            tmp_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------------
    # Concepts
    # ------------------------------------------------------------------------

    @app.get("/api/concepts", response_model=list[ConceptResponse])
    async def list_concepts(
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        concept_type: str | None = Query(None),
    ) -> list[dict[str, Any]]:
        """List all concepts."""
        graph = state.ensure_loaded()

        concepts = list(graph.iterate_concepts())

        # Filter by type
        if concept_type:
            concepts = [c for c in concepts if c.concept_type.value == concept_type]

        # Paginate
        concepts = concepts[offset:offset + limit]

        return [
            {
                "name": c.name,
                "label": c.label,
                "description": c.description,
                "concept_type": c.concept_type.value,
                "categories": c.categories,
                "aliases": c.aliases,
                "source_url": str(c.source_url) if c.source_url else None,
            }
            for c in concepts
        ]

    @app.get("/api/concepts/{name}", response_model=ConceptResponse)
    async def get_concept(name: str) -> dict[str, Any]:
        """Get a specific concept."""
        graph = state.ensure_loaded()
        concept = graph.get_concept(name)

        if not concept:
            raise HTTPException(status_code=404, detail=f"Concept not found: {name}")

        return {
            "name": concept.name,
            "label": concept.label,
            "description": concept.description,
            "concept_type": concept.concept_type.value,
            "categories": concept.categories,
            "aliases": concept.aliases,
            "source_url": str(concept.source_url) if concept.source_url else None,
        }

    @app.post("/api/concepts", response_model=ConceptResponse)
    async def create_concept(data: ConceptCreate) -> dict[str, Any]:
        """Create a new concept."""
        graph = state.ensure_loaded()

        try:
            concept_type = ConceptType(data.concept_type)
        except ValueError:
            concept_type = ConceptType.ENTITY

        concept = Concept(
            name=data.name,
            label=data.label,
            description=data.description,
            concept_type=concept_type,
            categories=data.categories,
            aliases=data.aliases,
        )

        graph.add_concept(concept)

        # Update search index
        if state.search_index:
            state.search_index.index_concept(concept)

        return {
            "name": concept.name,
            "label": concept.label,
            "description": concept.description,
            "concept_type": concept.concept_type.value,
            "categories": concept.categories,
            "aliases": concept.aliases,
            "source_url": None,
        }

    @app.get("/api/concepts/{name}/neighbors")
    async def get_neighbors(
        name: str,
        direction: str = Query("both", regex="^(in|out|both)$"),
        relation_type: str | None = Query(None),
    ) -> list[str]:
        """Get neighboring concepts."""
        graph = state.ensure_loaded()

        rel_type = None
        if relation_type:
            try:
                rel_type = RelationType(relation_type)
            except ValueError:
                pass

        return graph.get_neighbors(name, relation_type=rel_type, direction=direction)

    # ------------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------------

    @app.get("/api/relations", response_model=list[RelationResponse])
    async def list_relations(
        subject: str | None = Query(None),
        predicate: str | None = Query(None),
        object: str | None = Query(None),
        limit: int = Query(100, ge=1, le=1000),
    ) -> list[dict[str, Any]]:
        """List relations with optional filters."""
        graph = state.ensure_loaded()

        relations = []
        for source, target, data in graph.iterate_relations():
            rel_type = data.get("relation_type", "related_to")

            # Apply filters
            if subject and source != subject:
                continue
            if predicate and rel_type != predicate:
                continue
            if object and target != object:
                continue

            relations.append({
                "subject": source,
                "predicate": rel_type,
                "object": target,
                "confidence": data.get("confidence", 1.0),
            })

            if len(relations) >= limit:
                break

        return relations

    @app.post("/api/relations", response_model=RelationResponse)
    async def create_relation(data: RelationCreate) -> dict[str, Any]:
        """Create a new relation."""
        graph = state.ensure_loaded()

        try:
            predicate = RelationType(data.predicate)
        except ValueError:
            predicate = RelationType.RELATED_TO

        relation = Relation(
            subject=data.subject,
            predicate=predicate,
            object=data.object,
            confidence=data.confidence,
        )

        graph.add_relation(relation)

        return {
            "subject": relation.subject,
            "predicate": relation.predicate.value,
            "object": relation.object,
            "confidence": relation.confidence,
        }

    # ------------------------------------------------------------------------
    # Graph Data (for visualization)
    # ------------------------------------------------------------------------

    @app.get("/api/graph", response_model=GraphDataResponse)
    async def get_graph_data(
        max_nodes: int = Query(200, ge=1, le=1000),
        center: str | None = Query(None),
        radius: int = Query(2, ge=1, le=5),
    ) -> dict[str, Any]:
        """Get graph data for visualization."""
        graph = state.ensure_loaded()

        # Get subgraph if center specified
        if center:
            if center not in graph:
                raise HTTPException(status_code=404, detail=f"Concept not found: {center}")
            work_graph = graph.get_subgraph(center, radius)
        else:
            work_graph = graph

        # Build node list
        nodes = []
        node_names = set()

        # Sort by degree and limit
        degrees = dict(work_graph.graph.degree())
        sorted_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)

        for name, degree in sorted_nodes[:max_nodes]:
            concept = work_graph.get_concept(name)
            if concept:
                nodes.append({
                    "id": name,
                    "label": concept.label,
                    "type": concept.concept_type.value,
                    "description": concept.description[:200] if concept.description else "",
                    "degree": degree,
                })
                node_names.add(name)

        # Build edge list
        edges = []
        for source, target, data in work_graph.iterate_relations():
            if source in node_names and target in node_names:
                edges.append({
                    "source": source,
                    "target": target,
                    "type": data.get("relation_type", "related_to"),
                    "confidence": data.get("confidence", 1.0),
                })

        return {"nodes": nodes, "edges": edges}

    # ------------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------------

    @app.get("/api/search", response_model=SearchResponse)
    async def search(
        q: str = Query(..., min_length=1),
        limit: int = Query(20, ge=1, le=100),
        concept_type: str | None = Query(None),
    ) -> dict[str, Any]:
        """Search for concepts."""
        state.ensure_loaded()

        if not state.search_index:
            raise HTTPException(status_code=500, detail="Search index not available")

        # Parse concept type filter
        ctype = None
        if concept_type:
            try:
                ctype = ConceptType(concept_type)
            except ValueError:
                pass

        hits = state.search_index.search(q, limit=limit, concept_type=ctype)

        return {
            "results": [
                {
                    "name": hit.concept_name,
                    "label": hit.label,
                    "description": hit.description[:200] if hit.description else "",
                    "type": hit.concept_type,
                    "score": hit.score,
                    "matched_terms": hit.matched_terms,
                }
                for hit in hits
            ],
            "total": len(hits),
            "query": q,
        }

    @app.get("/api/suggest")
    async def suggest(
        q: str = Query(..., min_length=1),
        limit: int = Query(10, ge=1, le=50),
    ) -> list[str]:
        """Get autocomplete suggestions."""
        state.ensure_loaded()

        if not state.search_index:
            return []

        return state.search_index.suggest(q, limit=limit)

    # ------------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------------

    @app.get("/api/path")
    async def find_path(
        source: str = Query(...),
        target: str = Query(...),
        max_length: int = Query(5, ge=1, le=10),
    ) -> dict[str, Any]:
        """Find shortest path between concepts."""
        graph = state.ensure_loaded()

        path = graph.find_path(source, target, max_length=max_length)

        if path is None:
            return {"found": False, "path": [], "length": 0}

        return {
            "found": True,
            "path": path,
            "length": len(path) - 1,
        }

    @app.get("/api/paths")
    async def find_all_paths(
        source: str = Query(...),
        target: str = Query(...),
        max_length: int = Query(4, ge=1, le=6),
    ) -> dict[str, Any]:
        """Find all paths between concepts."""
        graph = state.ensure_loaded()

        paths = graph.find_all_paths(source, target, max_length=max_length)

        return {
            "paths": paths,
            "count": len(paths),
        }

    # ------------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------------

    @app.get("/api/stats", response_model=StatsResponse)
    async def get_stats() -> dict[str, Any]:
        """Get ontology statistics."""
        graph = state.ensure_loaded()
        stats = graph.get_stats()

        return {
            "total_concepts": stats.total_concepts,
            "total_relations": stats.total_relations,
            "concepts_by_type": stats.concepts_by_type,
            "relations_by_type": stats.relations_by_type,
            "top_connected": stats.top_connected_concepts,
        }

    # ------------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------------

    @app.get("/api/types/concepts")
    async def list_concept_types() -> list[str]:
        """List available concept types."""
        return [t.value for t in ConceptType]

    @app.get("/api/types/relations")
    async def list_relation_types() -> list[str]:
        """List available relation types."""
        return [t.value for t in RelationType]

    return app


def get_default_html() -> str:
    """Get default HTML when static files are not available."""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Grokipedia Ontology</title>
    <meta charset="utf-8">
    <style>
        body { font-family: system-ui; padding: 2rem; max-width: 800px; margin: 0 auto; }
        h1 { color: #333; }
        a { color: #0066cc; }
        .card { background: #f5f5f5; padding: 1rem; border-radius: 8px; margin: 1rem 0; }
    </style>
</head>
<body>
    <h1>Grokipedia Ontology API</h1>
    <div class="card">
        <p>The API is running. Static files are not installed.</p>
        <p>API Documentation: <a href="/api/docs">/api/docs</a></p>
    </div>
</body>
</html>
"""


def run_server(
    data_path: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
) -> None:
    """
    Run the web server.

    Args:
        data_path: Path to data file to load
        host: Host to bind to
        port: Port to bind to
        reload: Enable auto-reload for development
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI and uvicorn are required. "
            "Install with: pip install grokipedia-ontology[web]"
        )

    import uvicorn

    # Create app with data
    app = create_app(data_path)

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
    )
