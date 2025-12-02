"""
Command-line interface for Grokipedia Ontology.

Provides commands for fetching articles, building ontologies,
and querying the knowledge graph.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree
from rich.panel import Panel

from grokipedia_ontology.fetcher import GrokipediaFetcher
from grokipedia_ontology.ontology import GrokipediaOntology
from grokipedia_ontology.graph import KnowledgeGraph
from grokipedia_ontology.models import RelationType, ConceptType
from grokipedia_ontology.visualization import GraphVisualizer

app = typer.Typer(
    name="grokipedia-ontology",
    help="Build and query knowledge graphs from Grokipedia",
    add_completion=False,
)
console = Console()


@app.command()
def fetch(
    topic: str = typer.Argument(..., help="Topic to fetch from Grokipedia"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output file path"),
    format: str = typer.Option("json", "-f", "--format", help="Output format (json, turtle, xml)"),
) -> None:
    """Fetch a single article from Grokipedia."""

    async def _fetch() -> None:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(f"Fetching '{topic}'...", total=None)

            async with GrokipediaFetcher() as fetcher:
                article = await fetcher.fetch_article(topic)

        if article is None:
            console.print(f"[red]Article not found: {topic}[/red]")
            raise typer.Exit(1)

        console.print(f"[green]Successfully fetched: {article.title}[/green]")

        if format == "json":
            data = article.model_dump(mode="json")
            content = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            ontology = GrokipediaOntology()
            ontology.add_article(article)
            content = ontology.serialize(format=format)

        if output:
            output.write_text(content)
            console.print(f"[blue]Saved to: {output}[/blue]")
        else:
            console.print(content)

    asyncio.run(_fetch())


@app.command()
def crawl(
    start_topic: str = typer.Argument(..., help="Starting topic for crawling"),
    max_depth: int = typer.Option(2, "-d", "--depth", help="Maximum crawl depth"),
    max_articles: int = typer.Option(50, "-n", "--max", help="Maximum articles to fetch"),
    output: Path = typer.Option(
        Path("knowledge_graph.ttl"), "-o", "--output", help="Output file path"
    ),
    format: str = typer.Option("turtle", "-f", "--format", help="Output format"),
) -> None:
    """Crawl Grokipedia starting from a topic and build a knowledge graph."""

    async def _crawl() -> None:
        console.print(f"[bold]Starting crawl from: {start_topic}[/bold]")
        console.print(f"Max depth: {max_depth}, Max articles: {max_articles}")

        async with GrokipediaFetcher(delay_between_requests=1.5) as fetcher:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Discovering articles...", total=None)

                articles = await fetcher.discover_related(
                    start_topic,
                    max_depth=max_depth,
                    max_articles=max_articles,
                )

                progress.update(task, description=f"Found {len(articles)} articles")

        if not articles:
            console.print("[red]No articles found[/red]")
            raise typer.Exit(1)

        # Build knowledge graph
        graph = KnowledgeGraph()
        for article in articles:
            graph.add_article(article)

        # Save ontology
        graph.ontology.save(output, format=format)

        # Display stats
        stats = graph.get_stats()
        table = Table(title="Knowledge Graph Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total Concepts", str(stats.total_concepts))
        table.add_row("Total Relations", str(stats.total_relations))
        table.add_row("Avg Relations/Concept", f"{stats.average_relations_per_concept:.2f}")

        console.print(table)
        console.print(f"\n[blue]Saved ontology to: {output}[/blue]")

    asyncio.run(_crawl())


@app.command()
def query(
    ontology_path: Path = typer.Argument(..., help="Path to ontology file"),
    sparql: str = typer.Option(None, "-q", "--query", help="SPARQL query to execute"),
    list_concepts: bool = typer.Option(False, "--list", help="List all concepts"),
) -> None:
    """Query an existing ontology."""
    ontology = GrokipediaOntology()
    ontology.load(ontology_path)

    if list_concepts:
        # Query all concepts
        sparql_query = """
        SELECT ?concept ?label WHERE {
            ?concept rdfs:label ?label .
        }
        LIMIT 100
        """
        results = ontology.query(sparql_query)

        table = Table(title="Concepts")
        table.add_column("URI", style="cyan")
        table.add_column("Label", style="green")

        for row in results:
            table.add_row(row.get("concept", ""), row.get("label", ""))

        console.print(table)

    elif sparql:
        results = ontology.query(sparql)
        console.print(json.dumps(results, indent=2))
    else:
        # Show stats
        stats = ontology.get_stats()
        console.print(Panel(
            f"Concepts: {stats.total_concepts}\n"
            f"Relations: {stats.total_relations}",
            title="Ontology Statistics",
        ))


@app.command()
def stats(
    ontology_path: Path = typer.Argument(..., help="Path to ontology file"),
) -> None:
    """Display statistics about an ontology."""
    ontology = GrokipediaOntology()
    ontology.load(ontology_path)

    stats = ontology.get_stats()

    console.print(Panel.fit(
        f"[bold]Total Concepts:[/bold] {stats.total_concepts}\n"
        f"[bold]Total Relations:[/bold] {stats.total_relations}\n"
        f"[bold]Avg Relations/Concept:[/bold] {stats.average_relations_per_concept:.2f}",
        title="[bold blue]Ontology Statistics[/bold blue]",
    ))

    if stats.concepts_by_type:
        table = Table(title="Concepts by Type")
        table.add_column("Type", style="cyan")
        table.add_column("Count", style="green")
        for ctype, count in sorted(stats.concepts_by_type.items(), key=lambda x: -x[1]):
            table.add_row(ctype, str(count))
        console.print(table)

    if stats.relations_by_type:
        table = Table(title="Relations by Type")
        table.add_column("Type", style="cyan")
        table.add_column("Count", style="green")
        for rtype, count in sorted(stats.relations_by_type.items(), key=lambda x: -x[1]):
            table.add_row(rtype, str(count))
        console.print(table)

    if stats.top_connected_concepts:
        table = Table(title="Most Connected Concepts")
        table.add_column("Concept", style="cyan")
        table.add_column("Connections", style="green")
        for concept, count in stats.top_connected_concepts:
            table.add_row(concept, str(count))
        console.print(table)


@app.command()
def convert(
    input_path: Path = typer.Argument(..., help="Input ontology file"),
    output_path: Path = typer.Argument(..., help="Output file path"),
    output_format: str = typer.Option("turtle", "-f", "--format", help="Output format"),
) -> None:
    """Convert ontology between formats."""
    ontology = GrokipediaOntology()
    ontology.load(input_path)
    ontology.save(output_path, format=output_format)
    console.print(f"[green]Converted to {output_format}: {output_path}[/green]")


@app.command()
def search(
    ontology_path: Path = typer.Argument(..., help="Path to ontology file"),
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "-n", "--limit", help="Maximum results"),
) -> None:
    """Search for concepts in the knowledge graph."""
    ontology = GrokipediaOntology()
    ontology.load(ontology_path)

    # Build a knowledge graph for searching
    graph = KnowledgeGraph(ontology)

    # Note: This requires rebuilding concepts from the graph
    # For a full implementation, we'd need to persist concepts separately
    console.print(f"[yellow]Searching for: {query}[/yellow]")

    sparql_query = f"""
    SELECT ?concept ?label ?description WHERE {{
        ?concept rdfs:label ?label .
        OPTIONAL {{ ?concept rdfs:comment ?description }}
        FILTER(CONTAINS(LCASE(?label), LCASE("{query}")))
    }}
    LIMIT {limit}
    """

    results = ontology.query(sparql_query)

    if not results:
        console.print("[red]No results found[/red]")
        return

    table = Table(title=f"Search Results for '{query}'")
    table.add_column("Concept", style="cyan")
    table.add_column("Label", style="green")
    table.add_column("Description", style="white", max_width=50)

    for row in results:
        table.add_row(
            row.get("concept", "")[-50:],  # Truncate URI
            row.get("label", ""),
            row.get("description", "")[:50] + "..." if row.get("description", "") else "",
        )

    console.print(table)


@app.command()
def init(
    output_dir: Path = typer.Option(Path("."), "-o", "--output", help="Output directory"),
) -> None:
    """Initialize a new ontology project with base schema."""
    schema_path = output_dir / "ontology" / "grokipedia.ttl"
    schema_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy base schema
    base_schema = Path(__file__).parent.parent.parent / "ontology" / "grokipedia.ttl"
    if base_schema.exists():
        schema_path.write_text(base_schema.read_text())
    else:
        # Create a minimal schema
        ontology = GrokipediaOntology()
        ontology.save(schema_path)

    console.print(f"[green]Initialized ontology project at: {output_dir}[/green]")
    console.print(f"  Schema: {schema_path}")


@app.command()
def visualize(
    input_path: Path = typer.Argument(..., help="Input ontology or JSON file"),
    output_path: Path = typer.Option(
        Path("knowledge_graph.html"), "-o", "--output", help="Output HTML file"
    ),
    title: str = typer.Option("Knowledge Graph", "-t", "--title", help="Visualization title"),
    center: Optional[str] = typer.Option(None, "-c", "--center", help="Center node for subgraph"),
    radius: int = typer.Option(2, "-r", "--radius", help="Radius for subgraph (if center specified)"),
    max_nodes: Optional[int] = typer.Option(None, "-n", "--max-nodes", help="Maximum nodes to display"),
    no_physics: bool = typer.Option(False, "--no-physics", help="Disable physics simulation"),
    format: str = typer.Option("html", "-f", "--format", help="Output format (html, dot, png)"),
    concept_types: Optional[str] = typer.Option(
        None, "--types", help="Filter by concept types (comma-separated)"
    ),
    relation_types: Optional[str] = typer.Option(
        None, "--relations", help="Filter by relation types (comma-separated)"
    ),
) -> None:
    """Generate interactive visualization of the knowledge graph."""
    # Load data
    if input_path.suffix == ".json":
        # Load from JSON (sample data format)
        import json
        data = json.loads(input_path.read_text())
        graph = KnowledgeGraph()

        # Import concepts
        from grokipedia_ontology.models import Concept, Relation
        for concept_data in data.get("concepts", []):
            concept = Concept(**concept_data)
            graph.add_concept(concept)

        # Import relations
        for rel_data in data.get("relations", []):
            relation = Relation(**rel_data)
            graph.add_relation(relation)

        console.print(f"[blue]Loaded {len(graph)} concepts from JSON[/blue]")
    else:
        # Load from ontology file
        ontology = GrokipediaOntology()
        ontology.load(input_path)
        graph = KnowledgeGraph(ontology)

        # Rebuild concepts from SPARQL query
        results = ontology.query("""
            SELECT ?concept ?label ?type ?description WHERE {
                ?concept a ?type .
                ?concept rdfs:label ?label .
                OPTIONAL { ?concept rdfs:comment ?description }
                FILTER(STRSTARTS(STR(?type), "http://grokipedia.org/class#"))
            }
        """)

        from grokipedia_ontology.models import Concept
        for row in results:
            concept_uri = row.get("concept", "")
            name = concept_uri.split("#")[-1] if "#" in concept_uri else concept_uri.split("/")[-1]
            type_uri = row.get("type", "")
            concept_type_str = type_uri.split("#")[-1] if "#" in type_uri else "entity"

            try:
                concept_type = ConceptType(concept_type_str)
            except ValueError:
                concept_type = ConceptType.ENTITY

            concept = Concept(
                name=name,
                label=row.get("label", name),
                description=row.get("description", ""),
                concept_type=concept_type,
            )
            graph._concepts[name] = concept
            graph.graph.add_node(
                name,
                label=concept.label,
                description=concept.description,
                concept_type=concept.concept_type.value,
            )

        # Rebuild edges from SPARQL
        edge_results = ontology.query("""
            SELECT ?s ?p ?o WHERE {
                ?s ?p ?o .
                FILTER(STRSTARTS(STR(?p), "http://grokipedia.org/property#"))
                FILTER(STRSTARTS(STR(?o), "http://grokipedia.org/ontology#"))
            }
        """)

        for row in edge_results:
            subject = row.get("s", "").split("#")[-1]
            predicate = row.get("p", "").split("#")[-1]
            obj = row.get("o", "").split("#")[-1]
            if subject and obj:
                graph.graph.add_edge(subject, obj, relation_type=predicate)

        console.print(f"[blue]Loaded ontology with {len(graph._concepts)} concepts[/blue]")

    if len(graph) == 0:
        console.print("[red]No concepts found in the input file[/red]")
        raise typer.Exit(1)

    # Parse filters
    filter_types = concept_types.split(",") if concept_types else None
    filter_rels = relation_types.split(",") if relation_types else None

    # Create visualizer
    visualizer = GraphVisualizer()

    try:
        if format == "html":
            if center:
                result_path = visualizer.visualize_subgraph(
                    graph,
                    center=center,
                    radius=radius,
                    output_path=output_path,
                    physics=not no_physics,
                    filter_concept_types=filter_types,
                    filter_relation_types=filter_rels,
                    max_nodes=max_nodes,
                )
            else:
                result_path = visualizer.visualize(
                    graph,
                    output_path=output_path,
                    title=title,
                    physics=not no_physics,
                    filter_concept_types=filter_types,
                    filter_relation_types=filter_rels,
                    max_nodes=max_nodes,
                )
            console.print(f"[green]Visualization saved to: {result_path}[/green]")
            console.print(f"[blue]Open in browser to view interactive graph[/blue]")

        elif format == "dot":
            output_path = output_path.with_suffix(".dot")
            result_path = visualizer.export_graphviz(graph, output_path)
            console.print(f"[green]Graphviz DOT file saved to: {result_path}[/green]")
            console.print("[blue]Convert to image with: dot -Tpng graph.dot -o graph.png[/blue]")

        elif format == "png":
            output_path = output_path.with_suffix(".png")
            result_path = visualizer.generate_stats_chart(graph, output_path)
            if result_path:
                console.print(f"[green]Statistics chart saved to: {result_path}[/green]")
            else:
                console.print("[red]Failed to generate chart (matplotlib not installed)[/red]")
                raise typer.Exit(1)

        else:
            console.print(f"[red]Unknown format: {format}[/red]")
            raise typer.Exit(1)

    except ImportError as e:
        console.print(f"[red]{e}[/red]")
        console.print("[yellow]Install visualization dependencies:[/yellow]")
        console.print("  pip install grokipedia-ontology[visualization]")
        raise typer.Exit(1)


@app.command()
def export(
    input_path: Path = typer.Argument(..., help="Input ontology file"),
    output_path: Path = typer.Argument(..., help="Output file path"),
    format: str = typer.Option("graphml", "-f", "--format", help="Export format (graphml, gexf, json)"),
) -> None:
    """Export knowledge graph to various formats."""
    ontology = GrokipediaOntology()
    ontology.load(input_path)

    graph = KnowledgeGraph(ontology)

    if format == "graphml":
        graph.export_graphml(str(output_path))
        console.print(f"[green]Exported to GraphML: {output_path}[/green]")
    elif format == "gexf":
        graph.export_gexf(str(output_path))
        console.print(f"[green]Exported to GEXF (Gephi): {output_path}[/green]")
    elif format == "json":
        data = graph.to_dict()
        output_path.write_text(json.dumps(data, indent=2, default=str))
        console.print(f"[green]Exported to JSON: {output_path}[/green]")
    else:
        console.print(f"[red]Unknown format: {format}[/red]")
        raise typer.Exit(1)


@app.command()
def serve(
    data_path: Path = typer.Argument(..., help="Path to data file (JSON or TTL)"),
    host: str = typer.Option("127.0.0.1", "-h", "--host", help="Host to bind to"),
    port: int = typer.Option(8000, "-p", "--port", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload (dev mode)"),
) -> None:
    """Start the web dashboard server."""
    try:
        from grokipedia_ontology.api import run_server
    except ImportError:
        console.print("[red]Web dependencies not installed[/red]")
        console.print("[yellow]Install with: pip install grokipedia-ontology[web][/yellow]")
        raise typer.Exit(1)

    if not data_path.exists():
        console.print(f"[red]Data file not found: {data_path}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold blue]Starting Grokipedia Ontology Dashboard[/bold blue]")
    console.print(f"  Data: {data_path}")
    console.print(f"  URL: http://{host}:{port}")
    console.print(f"  API Docs: http://{host}:{port}/api/docs")
    console.print()
    console.print("[dim]Press Ctrl+C to stop[/dim]")

    run_server(data_path=data_path, host=host, port=port, reload=reload)


@app.command(name="mcp-serve")
def mcp_serve(
    data_path: Path = typer.Argument(..., help="Path to data file (JSON or TTL)"),
) -> None:
    """Start the MCP (Model Context Protocol) server for AI assistants."""
    import asyncio
    import sys
    from rich.console import Console

    # MCP uses stdout for JSON-RPC, so all messages must go to stderr
    stderr_console = Console(stderr=True)

    try:
        from grokipedia_ontology.mcp_server import run_mcp_server
    except ImportError:
        stderr_console.print("[red]MCP dependencies not installed[/red]")
        stderr_console.print("[yellow]Install with: pip install grokipedia-ontology[mcp][/yellow]")
        raise typer.Exit(1)

    if not data_path.exists():
        stderr_console.print(f"[red]Data file not found: {data_path}[/red]")
        raise typer.Exit(1)

    stderr_console.print(f"[bold blue]Starting Grokipedia Ontology MCP Server[/bold blue]")
    stderr_console.print(f"  Data: {data_path}")
    stderr_console.print()
    stderr_console.print("[dim]Waiting for MCP client connection...[/dim]")

    asyncio.run(run_mcp_server(data_path))


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
