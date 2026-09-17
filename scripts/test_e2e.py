# Requires GROQ_API_KEY in .env and network access. Run on personal laptop.
"""End-to-end smoke test: ingest sample data, run queries, print summary."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table

console = Console()

TEST_QUERIES = [
    "Have we seen Redis memory issues before?",
    "What happens downstream if the payment service goes down?",
    "What is our most common root cause category?",
    "How did we fix the database connection pool exhaustion last time?",
    "We're seeing Kafka consumer lag, what should we watch for?",
]


def main():
    t_total = time.time()

    # --- Phase 1: Ingestion ---
    console.print("\n[bold cyan]Phase 1: Ingestion[/bold cyan]")
    from src.ingestion.pipeline import IngestionPipeline

    pipeline = IngestionPipeline()
    sample_dir = Path("data/sample")
    results = pipeline.ingest_directory(sample_dir)

    stats = pipeline.get_stats()
    stats_table = Table(title="Store Stats After Ingestion")
    stats_table.add_column("Store", style="cyan")
    stats_table.add_column("Metric", style="white")
    stats_table.add_column("Value", style="green")
    stats_table.add_row("Graph", "Total nodes", str(stats["graph"]["total_nodes"]))
    stats_table.add_row("Graph", "Total edges", str(stats["graph"]["total_edges"]))
    for ntype, count in stats["graph"]["node_types"].items():
        stats_table.add_row("Graph", f"  {ntype} nodes", str(count))
    stats_table.add_row("Vectors", "Total chunks", str(stats["vectors"]["total_chunks"]))
    stats_table.add_row("SQL", "Total incidents", str(stats["sql"]["total_incidents"]))
    console.print(stats_table)

    # --- Phase 2: Queries ---
    console.print("\n[bold cyan]Phase 2: Query Tests[/bold cyan]")
    from src.retrieval.hybrid_retriever import HybridRetriever
    from src.retrieval.generator import AnswerGenerator

    retriever = HybridRetriever()
    generator = AnswerGenerator()

    passed = 0
    failed = 0
    query_results = []

    for i, query in enumerate(TEST_QUERIES, 1):
        console.print(f"\n[bold]Query {i}/{len(TEST_QUERIES)}:[/bold] {query}")
        t_q = time.time()
        try:
            context = retriever.retrieve(query)
            answer = generator.generate(query, context)
            elapsed = time.time() - t_q

            console.print(f"  Intent: [yellow]{context['intent']}[/yellow]")
            console.print(f"  Vector results: {len(context['vector_results'])}")
            console.print(f"  Graph context: {bool(answer.graph_context)}")
            console.print(f"  Answer ({len(answer.answer)} chars): {answer.answer[:500]}")
            console.print(f"  Time: {elapsed:.2f}s")

            query_results.append({"query": query, "status": "PASS", "time": elapsed})
            passed += 1
        except Exception as exc:
            elapsed = time.time() - t_q
            console.print(f"  [red]FAILED: {exc}[/red]")
            query_results.append({"query": query, "status": "FAIL", "time": elapsed})
            failed += 1

    # --- Summary ---
    total_time = time.time() - t_total
    console.print("\n")
    summary = Table(title="E2E Test Summary")
    summary.add_column("#", style="dim")
    summary.add_column("Query", style="white", max_width=60)
    summary.add_column("Status", style="bold")
    summary.add_column("Time", style="dim")
    for i, r in enumerate(query_results, 1):
        status_style = "green" if r["status"] == "PASS" else "red"
        summary.add_row(str(i), r["query"], f"[{status_style}]{r['status']}[/{status_style}]",
                        f"{r['time']:.2f}s")
    console.print(summary)

    console.print(f"\n[bold]Results:[/bold] {passed} passed, {failed} failed")
    console.print(f"[bold]Total time:[/bold] {total_time:.1f}s")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
