"""Reset data stores (vector, graph, SQL) selectively or all at once."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console


def main():
    parser = argparse.ArgumentParser(description="Reset PostmortemIQ data stores")
    parser.add_argument("--all", action="store_true", help="Reset all stores")
    parser.add_argument("--vectors", action="store_true", help="Reset vector store (ChromaDB)")
    parser.add_argument("--graph", action="store_true", help="Reset knowledge graph")
    parser.add_argument("--sql", action="store_true", help="Reset SQLite database")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    console = Console()
    targets = []
    if args.all:
        targets = ["vectors", "graph", "sql"]
    else:
        if args.vectors:
            targets.append("vectors")
        if args.graph:
            targets.append("graph")
        if args.sql:
            targets.append("sql")

    if not targets:
        console.print("[yellow]No stores selected. Use --all or specify --vectors, --graph, --sql[/yellow]")
        sys.exit(0)

    console.print(f"[yellow]Will reset: {', '.join(targets)}[/yellow]")

    if not args.force:
        confirm = input("Are you sure? (y/N): ").strip().lower()
        if confirm != "y":
            console.print("[dim]Aborted.[/dim]")
            sys.exit(0)

    if "vectors" in targets:
        from src.storage.vector_store import VectorStore
        VectorStore().reset()
        console.print("[green]  ✓ Vector store reset[/green]")

    if "graph" in targets:
        from src.storage.graph_store import KnowledgeGraph
        KnowledgeGraph().reset()
        console.print("[green]  ✓ Knowledge graph reset[/green]")

    if "sql" in targets:
        from src.storage.sql_store import SQLStore
        SQLStore().reset()
        console.print("[green]  ✓ SQLite database reset[/green]")

    console.print("[bold green]Done.[/bold green]")


if __name__ == "__main__":
    main()
