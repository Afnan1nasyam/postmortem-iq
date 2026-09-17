"""Evaluate retrieval quality against test queries."""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table

QUERIES_PATH = Path("eval/test_queries.json")
RESULTS_PATH = Path("eval/retrieval_results.json")


def main():
    console = Console()

    from src.retrieval.generator import AnswerGenerator
    from src.retrieval.hybrid_retriever import HybridRetriever

    queries = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    console.print(f"\n[bold]Evaluating {len(queries)} test queries[/bold]\n")

    retriever = HybridRetriever()
    generator = AnswerGenerator()

    table = Table(title="Retrieval Evaluation")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Query", style="cyan", max_width=50)
    table.add_column("Difficulty", style="white")
    table.add_column("Intent", justify="center")
    table.add_column("Services", justify="center")
    table.add_column("Keywords", justify="center")
    table.add_column("Score", style="bold", justify="center")

    all_results = []
    total_score = 0
    total_max = 0

    for i, tq in enumerate(queries, 1):
        query = tq["query"]
        expected_intent = tq["expected_intent"]
        expected_services = tq["expected_services"]
        expected_keywords = tq["expected_incident_keywords"]
        difficulty = tq["difficulty"]

        t0 = time.time()
        try:
            context = retriever.retrieve(query)
            answer = generator.generate(query, context)
            elapsed = time.time() - t0

            actual_intent = str(context["intent"]).upper()
            if "." in actual_intent:
                actual_intent = actual_intent.split(".")[-1]

            intent_correct = actual_intent == expected_intent
            intent_score = 1 if intent_correct else 0

            services_found = [s.lower() for s in context.get("services_found", [])]
            services_correct = all(
                any(es.lower() in sf for sf in services_found)
                for es in expected_services
            ) if expected_services else True
            services_score = 1 if services_correct else 0

            answer_text = answer.answer.lower()
            keywords_found = all(
                kw.lower() in answer_text
                for kw in expected_keywords
            ) if expected_keywords else True
            keywords_score = 1 if keywords_found else 0

            max_points = 1 + (1 if expected_services else 0) + (1 if expected_keywords else 0)
            points = intent_score + services_score + keywords_score
            actual_max = max_points

            check = lambda v: "[green]✓[/green]" if v else "[red]✗[/red]"
            table.add_row(
                str(i),
                query[:50],
                difficulty,
                check(intent_correct),
                check(services_correct) if expected_services else "[dim]—[/dim]",
                check(keywords_found) if expected_keywords else "[dim]—[/dim]",
                f"{points}/{actual_max}",
            )

            all_results.append({
                "query": query,
                "difficulty": difficulty,
                "expected_intent": expected_intent,
                "actual_intent": actual_intent,
                "intent_correct": intent_correct,
                "services_correct": services_correct,
                "keywords_found": keywords_found,
                "points": points,
                "max_points": actual_max,
                "latency_s": round(elapsed, 2),
            })
            total_score += points
            total_max += actual_max

        except Exception as exc:
            console.print(f"  [red]Query {i} failed: {exc}[/red]")
            all_results.append({
                "query": query,
                "difficulty": difficulty,
                "error": str(exc),
                "points": 0,
                "max_points": 3,
            })
            total_max += 3

    console.print(table)

    pct = round(total_score / total_max * 100, 1) if total_max > 0 else 0
    console.print(f"\n[bold]Total score: {total_score}/{total_max} ({pct}%)[/bold]")

    by_difficulty = {}
    for r in all_results:
        d = r["difficulty"]
        if d not in by_difficulty:
            by_difficulty[d] = {"points": 0, "max": 0}
        by_difficulty[d]["points"] += r["points"]
        by_difficulty[d]["max"] += r["max_points"]

    for d, s in sorted(by_difficulty.items()):
        dp = round(s["points"] / s["max"] * 100, 1) if s["max"] > 0 else 0
        console.print(f"  {d}: {s['points']}/{s['max']} ({dp}%)")

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps({
        "total_score": total_score,
        "total_max": total_max,
        "pct": pct,
        "by_difficulty": by_difficulty,
        "results": all_results,
    }, indent=2), encoding="utf-8")
    console.print(f"\nResults saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
