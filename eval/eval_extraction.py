"""Evaluate extraction quality on ingested postmortems."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.table import Table

from src.storage.sql_store import SQLStore

RESULTS_PATH = Path("eval/extraction_results.json")


def score_incident(inc: dict) -> dict:
    """Score a single incident extraction on completeness."""
    scores = {}

    try:
        rc = json.loads(inc.get("root_cause_json", "{}"))
        scores["root_cause_category"] = 1 if rc.get("category") and rc["category"] != "unknown" else 0
    except (json.JSONDecodeError, TypeError):
        scores["root_cause_category"] = 0

    try:
        services = json.loads(inc.get("affected_services_json", "[]"))
        scores["affected_services"] = 1 if len(services) > 0 else 0
    except (json.JSONDecodeError, TypeError):
        scores["affected_services"] = 0

    try:
        chain = json.loads(inc.get("failure_chain_json", "[]"))
        scores["failure_chain"] = 1 if len(chain) > 0 else 0
    except (json.JSONDecodeError, TypeError):
        scores["failure_chain"] = 0

    try:
        deps = json.loads(inc.get("service_dependencies_json", "[]"))
        scores["service_dependencies"] = 1 if len(deps) > 0 else 0
    except (json.JSONDecodeError, TypeError):
        scores["service_dependencies"] = 0

    scores["has_title"] = 1 if inc.get("title") and inc["title"] != "EXTRACTION_FAILED" else 0
    scores["has_summary"] = 1 if inc.get("summary") else 0
    scores["has_severity"] = 1 if inc.get("severity") and inc["severity"] != "unknown" else 0

    total = sum(scores.values())
    scores["total"] = total
    scores["max"] = len(scores) - 1
    scores["pct"] = round(total / scores["max"] * 100, 1) if scores["max"] > 0 else 0

    return scores


def main():
    console = Console()
    sql = SQLStore()
    incidents = sql.get_all_incidents()

    if not incidents:
        console.print("[yellow]No incidents found in the database.[/yellow]")
        console.print("Run ingestion first:")
        console.print("  python scripts/seed_data.py")
        console.print("  python scripts/ingest_all.py --data-dir data/sample")
        return

    console.print(f"\n[bold]Evaluating {len(incidents)} extractions[/bold]\n")

    table = Table(title="Extraction Quality Scores")
    table.add_column("Incident", style="cyan", max_width=45)
    table.add_column("Title", style="white")
    table.add_column("RC Cat", justify="center")
    table.add_column("Services", justify="center")
    table.add_column("Chain", justify="center")
    table.add_column("Deps", justify="center")
    table.add_column("Score", style="bold", justify="center")

    all_results = []
    total_pct = 0

    for inc in incidents:
        scores = score_incident(inc)
        check = lambda v: "[green]✓[/green]" if v else "[red]✗[/red]"

        table.add_row(
            inc["id"][:12] + "...",
            (inc.get("title", "")[:35] + "...") if len(inc.get("title", "")) > 35 else inc.get("title", ""),
            check(scores["root_cause_category"]),
            check(scores["affected_services"]),
            check(scores["failure_chain"]),
            check(scores["service_dependencies"]),
            f"{scores['pct']}%",
        )

        total_pct += scores["pct"]
        all_results.append({
            "incident_id": inc["id"],
            "title": inc.get("title", ""),
            "scores": scores,
        })

    console.print(table)

    avg = round(total_pct / len(incidents), 1) if incidents else 0
    console.print(f"\n[bold]Average score: {avg}%[/bold] across {len(incidents)} incidents")

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps({
        "total_incidents": len(incidents),
        "average_score_pct": avg,
        "results": all_results,
    }, indent=2), encoding="utf-8")
    console.print(f"Results saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
