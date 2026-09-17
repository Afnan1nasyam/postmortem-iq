"""Batch ingest all postmortem files from a directory."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console

from src.ingestion.pipeline import IngestionPipeline
from src.storage.graph_store import KnowledgeGraph
from src.storage.sql_store import SQLStore
from src.storage.vector_store import VectorStore


def main():
    parser = argparse.ArgumentParser(description="Ingest postmortem files into all stores")
    parser.add_argument("--data-dir", default="data/raw", help="Directory containing postmortems")
    parser.add_argument("--reset", action="store_true", help="Reset all stores before ingesting")
    args = parser.parse_args()

    console = Console()
    data_dir = Path(args.data_dir)

    if not data_dir.exists():
        console.print(f"[red]Directory not found: {data_dir}[/red]")
        sys.exit(1)

    if args.reset:
        console.print("[yellow]Resetting all stores...[/yellow]")
        VectorStore().reset()
        KnowledgeGraph().reset()
        SQLStore().reset()
        console.print("[green]All stores reset.[/green]")

    pipeline = IngestionPipeline()
    results = pipeline.ingest_directory(data_dir)

    console.print(f"\n[bold green]Done.[/bold green] Ingested {len(results)} postmortems.")
    stats = pipeline.get_stats()
    console.print(f"  Graph: {stats['graph']['total_nodes']} nodes, {stats['graph']['total_edges']} edges")
    console.print(f"  Vectors: {stats['vectors']['total_chunks']} chunks")
    console.print(f"  SQL: {stats['sql']['total_incidents']} incidents")


if __name__ == "__main__":
    main()
