"""Interactive CLI for querying the PostmortemIQ system."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel


def main():
    console = Console()

    try:
        from src.retrieval.hybrid_retriever import HybridRetriever
        from src.retrieval.generator import AnswerGenerator
        from src.retrieval.intent_classifier import classify_intent
    except ImportError as exc:
        console.print(f"[red]Retrieval modules not yet available: {exc}[/red]")
        console.print("[dim]Build the retrieval layer first.[/dim]")
        sys.exit(1)

    retriever = HybridRetriever()
    generator = AnswerGenerator()

    console.print(Panel(
        "[bold cyan]PostmortemIQ Query CLI[/bold cyan]\n"
        "Ask questions about past incidents.\n"
        "Type 'quit' or 'exit' to stop.",
        border_style="blue",
    ))

    try:
        while True:
            try:
                query = input("\n🔍 Query: ").strip()
            except EOFError:
                break

            if not query:
                continue
            if query.lower() in ("quit", "exit"):
                break

            intent = classify_intent(query)
            console.print(f"[dim]Intent: {intent}[/dim]")

            results = retriever.retrieve(query, intent=intent)
            answer = generator.generate(query, results, intent=intent)

            console.print(Panel(answer.answer, title="Answer", border_style="green"))

            if answer.sources:
                console.print("[bold]Sources:[/bold]")
                for src in answer.sources:
                    console.print(f"  • {src.get('title', src.get('source_file', 'unknown'))}")

            if answer.graph_context:
                console.print(f"\n[dim]Graph context: {answer.graph_context}[/dim]")

    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")

    console.print("[bold]Goodbye.[/bold]")


if __name__ == "__main__":
    main()
