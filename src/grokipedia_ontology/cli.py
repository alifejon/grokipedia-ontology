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


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
