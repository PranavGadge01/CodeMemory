"""Command Line Interface (CLI) for CodeMemory."""

import argparse
from pathlib import Path
import sys

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from codememory.core.service import CodeMemoryService
from codememory.domain.exceptions import CodeMemoryError

console = Console()


def build_parser() -> argparse.ArgumentParser:
    """Build command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="codememory",
        description="CodeMemory - Local-first Personal DSA Knowledge Engine",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 1. Import command
    import_parser = subparsers.add_parser("import", help="Import coding problems and submissions from JSON, CSV, or JSONL file/dir")
    import_parser.add_argument("path", type=str, help="Path to JSON, CSV, JSONL file or directory")
    import_parser.add_argument("--preview", action="store_true", help="Preview import records without saving")

    # 2. Problem command
    prob_parser = subparsers.add_parser("problem", help="View problem details and attempts")
    prob_parser.add_argument("identifier", type=str, help="Problem title, slug, or ID")

    # 3. History command
    hist_parser = subparsers.add_parser("history", help="Show chronological evolution history of a problem")
    hist_parser.add_argument("identifier", type=str, help="Problem title, slug, or ID")

    # 4. Export command
    subparsers.add_parser("export", help="Generate Git-friendly knowledge base Markdown files")

    # 5. Stats command
    subparsers.add_parser("stats", help="Display system-wide problem solving statistics and analytics")

    # 6. List command
    list_parser = subparsers.add_parser("list", help="List all tracked problems")
    list_parser.add_argument("--topic", type=str, help="Filter by topic")
    list_parser.add_argument("--difficulty", type=str, help="Filter by difficulty (Easy, Medium, Hard)")

    # 7. Seed command
    subparsers.add_parser("seed", help="Seed database with sample fictional/classic DSA problems")

    # 8. Search command
    search_parser = subparsers.add_parser("search", help="Multi-criteria search across problems, topics, and text")
    search_parser.add_argument("query", type=str, nargs="?", default=None, help="Text query or phrase")
    search_parser.add_argument("--topic", type=str, help="Filter by topic")
    search_parser.add_argument("--difficulty", type=str, help="Filter by difficulty")
    search_parser.add_argument("--status", type=str, help="Filter by status (Accepted, TLE, WA)")
    search_parser.add_argument("--solved", action="store_true", help="Only solved problems")
    search_parser.add_argument("--unsolved", action="store_true", help="Only unsolved problems")

    # 9. Revise command
    revise_parser = subparsers.add_parser("revise", help="Prioritized problem revision engine")
    revise_parser.add_argument("--limit", type=int, default=10, help="Number of queue items to display")
    revise_parser.add_argument("--topic", type=str, help="Filter revision queue by topic")
    revise_parser.add_argument("--due", action="store_true", help="Show only problems due for review (>7 days)")
    revise_parser.add_argument("--mark", type=str, help="Mark problem as reviewed by slug or ID")

    # 10. Insights command
    subparsers.add_parser("insights", help="Display personal learning insights and study recommendations")

    # 11. Patterns command
    subparsers.add_parser("patterns", help="Display 'My Patterns' personal DSA memory summary")

    # 12. Graph command
    subparsers.add_parser("graph", help="Display lightweight DSA relationship knowledge graph summary")

    # 13. Evolution command
    evo_parser = subparsers.add_parser("evolution", help="Display solution evolution narrative across attempts")
    evo_parser.add_argument("identifier", type=str, help="Problem title, slug, or ID")

    # 14. Semantic command
    sem_parser = subparsers.add_parser("semantic", help="Perform TF-IDF local semantic search")
    sem_parser.add_argument("query", type=str, help="Natural language query")

    # 15. UI command
    subparsers.add_parser("ui", help="Launch local interactive Streamlit web dashboard")

    # 16. LeetCode command
    lc_parser = subparsers.add_parser("leetcode", help="LeetCode connector commands (import, preview, validate)")
    lc_parser.add_argument("action", choices=["import", "preview", "validate"], help="Action: import, preview, or validate")
    lc_parser.add_argument("path", type=str, help="Path to LeetCode exported JSON or CSV dataset file")

    # 17. Memory command (Phase 7)
    mem_parser = subparsers.add_parser("memory", help="Personal memory engine commands (index, rebuild, search, similar, mistakes, stats)")
    mem_parser.add_argument("action", choices=["index", "rebuild", "search", "similar", "mistakes", "stats"], help="Memory action")
    mem_parser.add_argument("target", type=str, nargs="?", default=None, help="Query phrase or Problem ID/slug")

    # 18. Health command (Phase 8)
    subparsers.add_parser("health", help="Run per-component health check and show system status")

    return parser


def main(args: list[str] | None = None) -> None:
    """Main CLI execution entrypoint."""
    parser = build_parser()
    parsed = parser.parse_args(args)

    if not parsed.command:
        parser.print_help()
        sys.exit(0)

    service = CodeMemoryService()

    try:
        if parsed.command == "import":
            target_path = Path(parsed.path)
            if parsed.preview:
                console.print(f"[bold blue]Previewing import from '{target_path}'...[/bold blue]")
                prev = service.import_service.preview_import(target_path)
                console.print(f"Total records read: [yellow]{prev['total_read']}[/yellow]")
                console.print(f"Valid records: [green]{prev['valid_count']}[/green]")
                console.print(f"Duplicates detected: [bold red]{prev['duplicate_count']}[/bold red]")
                if prev["errors"]:
                    console.print("[bold red]Validation Errors:[/bold red]")
                    for err in prev["errors"][:5]:
                        console.print(f" - {err}")
            else:
                console.print(f"[bold cyan]Importing data from '{target_path}'...[/bold cyan]")
                summary = service.import_data(target_path)
                console.print(f"[bold green]Import Complete![/bold green]")
                console.print(f"  • Total Records Read: [cyan]{summary.total_read}[/cyan]")
                console.print(f"  • Valid Records: [cyan]{summary.valid_count}[/cyan]")
                console.print(f"  • Imported Submissions: [bold green]{summary.imported_count}[/bold green]")
                console.print(f"  • Duplicate Skipped: [bold yellow]{summary.duplicate_count}[/bold yellow]")
                console.print(f"  • Error Count: [bold red]{summary.error_count}[/bold red]")
                if summary.imported_problems:
                    console.print(f"  • Affected Problems ({len(summary.imported_problems)}): {', '.join(summary.imported_problems)}")

        elif parsed.command == "problem":
            prob = service.get_problem(parsed.identifier)
            console.print(Panel.fit(f"[bold magenta]{prob.title}[/bold magenta]\n[dim]Slug: {prob.slug} | ID: {prob.id}[/dim]", title="Problem Details"))

            table = Table(show_header=True, header_style="bold blue")
            table.add_column("Property", style="bold")
            table.add_column("Value")
            table.add_row("Difficulty", f"[green]{prob.difficulty.value}[/green]")
            table.add_row("Platform", str(prob.platform.value if hasattr(prob.platform, "value") else prob.platform))
            table.add_row("Topics", ", ".join(prob.topics) if prob.topics else "None")
            table.add_row("URL", prob.url or "N/A")
            table.add_row("Total Attempts", str(len(prob.attempts)))
            table.add_row("Created At", prob.created_at.strftime("%Y-%m-%d %H:%M:%S"))
            console.print(table)

            if prob.statement:
                console.print(Panel(prob.statement, title="Problem Statement", border_style="dim"))

            if prob.latest_accepted_submission:
                sub = prob.latest_accepted_submission
                console.print(f"\n[bold green]Latest Accepted Solution ({sub.language}):[/bold green]")
                syntax = Syntax(sub.code, sub.language, theme="monokai", line_numbers=True)
                console.print(syntax)

        elif parsed.command == "history":
            hist = service.get_problem_history(parsed.identifier)
            console.print(Panel(f"[bold cyan]Evolution History: {hist['title']}[/bold cyan] ({hist['difficulty']})"))
            console.print(f"Attempts: [yellow]{hist['total_attempts']}[/yellow] | Submissions: [yellow]{hist['total_submissions']}[/yellow] | Accepted: [green]{hist['accepted_submissions']}[/green]")
            if hist['best_runtime_ms'] is not None:
                console.print(f"Best Runtime: [bold green]{hist['best_runtime_ms']:.1f} ms[/bold green] | Best Memory: [bold green]{hist['best_memory_mb']:.1f} MB[/bold green]")

            table = Table(show_header=True, header_style="bold yellow", title="Submission Timeline")
            table.add_column("#", justify="right")
            table.add_column("Attempt")
            table.add_column("Timestamp")
            table.add_column("Lang")
            table.add_column("Status")
            table.add_column("Runtime")
            table.add_column("Memory")

            for event in hist["timeline"]:
                st_color = "green" if event["status"] == "Accepted" else "red"
                rt = f"{event['runtime_ms']:.1f} ms" if event['runtime_ms'] is not None else "-"
                mem = f"{event['memory_mb']:.1f} MB" if event['memory_mb'] is not None else "-"
                table.add_row(
                    str(event["step"]),
                    f"#{event['attempt_number']} ({event['attempt_approach']})",
                    event["submitted_at"][:19].replace("T", " "),
                    event["language"],
                    f"[{st_color}]{event['status']}[/{st_color}]",
                    rt,
                    mem,
                )
            console.print(table)

        elif parsed.command == "export":
            console.print("[bold cyan]Exporting knowledge base files to knowledge/...[/bold cyan]")
            exported = service.export_knowledge()
            console.print(f"[bold green]Export Complete![/bold green] Exported [yellow]{len(exported)}[/yellow] problem directories to knowledge/.")

        elif parsed.command == "stats":
            stats = service.get_analytics_summary()
            console.print(Panel.fit("[bold magenta]CodeMemory Analytics & Practice Statistics[/bold magenta]"))

            table = Table(show_header=True, header_style="bold green")
            table.add_column("Metric")
            table.add_column("Value", justify="right")

            table.add_row("Total Problems Tracked", str(stats["total_problems"]))
            table.add_row("Total Attempts", str(stats["total_attempts"]))
            table.add_row("Total Submissions", str(stats["total_submissions"]))
            table.add_row("Accepted Submissions", str(stats["accepted_submissions"]))
            table.add_row("Overall Acceptance Rate", f"{stats['overall_acceptance_rate_pct']}%")

            diff_str = ", ".join(f"{k}: {v}" for k, v in stats["difficulty_breakdown"].items() if v > 0)
            table.add_row("Difficulty Breakdown", diff_str or "None")

            console.print(table)

        elif parsed.command == "list":
            problems = service.list_problems()
            if parsed.topic:
                t_lower = parsed.topic.lower()
                problems = [p for p in problems if any(t_lower in t.lower() for t in p.topics)]
            if parsed.difficulty:
                d_lower = parsed.difficulty.lower()
                problems = [p for p in problems if p.difficulty.value.lower() == d_lower]

            if not problems:
                console.print("[yellow]No problems found matching criteria.[/yellow]")
                return

            table = Table(show_header=True, header_style="bold blue", title=f"Tracked Problems ({len(problems)})")
            table.add_column("Slug", style="cyan")
            table.add_column("Title", style="bold")
            table.add_column("Difficulty")
            table.add_column("Topics")
            table.add_column("Attempts", justify="right")
            table.add_column("Status")

            for p in problems:
                accepted = "Accepted" if p.latest_accepted_submission else "In Progress"
                st_color = "green" if accepted == "Accepted" else "yellow"
                table.add_row(
                    p.slug,
                    p.title,
                    p.difficulty.value,
                    ", ".join(p.topics) if p.topics else "-",
                    str(len(p.attempts)),
                    f"[{st_color}]{accepted}[/{st_color}]",
                )
            console.print(table)

        elif parsed.command == "search":
            is_solved_filter = True if parsed.solved else (False if parsed.unsolved else None)
            if parsed.query and not parsed.topic and not parsed.difficulty and not parsed.status and is_solved_filter is None:
                results = service.search_service.search_by_query_string(parsed.query)
            else:
                results = service.search(
                    query=parsed.query,
                    topics=parsed.topic,
                    difficulty=parsed.difficulty,
                    status=parsed.status,
                    solved=is_solved_filter,
                )

            if not results:
                console.print("[yellow]No problems found matching search criteria.[/yellow]")
                return

            table = Table(show_header=True, header_style="bold cyan", title=f"Search Results ({len(results)})")
            table.add_column("Slug", style="cyan")
            table.add_column("Title", style="bold")
            table.add_column("Difficulty")
            table.add_column("Topics")
            table.add_column("Status")

            for p in results:
                st = "Accepted" if p.latest_accepted_submission else "Unsolved"
                color = "green" if st == "Accepted" else "yellow"
                table.add_row(
                    p.slug,
                    p.title,
                    p.difficulty.value,
                    ", ".join(p.topics) if p.topics else "-",
                    f"[{color}]{st}[/{color}]",
                )
            console.print(table)

        elif parsed.command == "revise":
            if parsed.mark:
                prob = service.mark_reviewed(parsed.mark)
                console.print(f"[bold green]Marked '{prob.title}' as reviewed![/bold green]")
                return

            if parsed.due:
                queue = service.get_due_problems(limit=parsed.limit)
                title_str = "Due Revision Queue (>7 days unreviewed)"
            else:
                queue = service.get_revision_queue(limit=parsed.limit, topic=parsed.topic)
                title_str = f"Prioritized Revision Queue ({'Topic: ' + parsed.topic if parsed.topic else 'All Topics'})"

            if not queue:
                console.print("[green]No problems currently in revision queue.[/green]")
                return

            table = Table(show_header=True, header_style="bold yellow", title=title_str)
            table.add_column("#", justify="right")
            table.add_column("Slug", style="cyan")
            table.add_column("Title", style="bold")
            table.add_column("Difficulty")
            table.add_column("Score", justify="right", style="bold yellow")
            table.add_column("Days Inactive", justify="right")

            for idx, item in enumerate(queue, 1):
                table.add_row(
                    str(idx),
                    item.slug,
                    item.title,
                    item.difficulty,
                    f"{item.priority_score:.1f}",
                    f"{item.breakdown.days_since_last_activity} days",
                )
            console.print(table)

        elif parsed.command == "insights":
            insights = service.generate_insights()
            console.print(Panel.fit("[bold magenta]Personal Learning Insights & Revision Patterns[/bold magenta]"))
            for ins in insights:
                console.print(f" • {ins}")

        elif parsed.command == "patterns":
            pat = service.get_personal_patterns()
            console.print(Panel.fit("[bold magenta]My Patterns — Personal DSA Memory[/bold magenta]"))
            console.print(f"• [bold green]Strengths:[/bold green] {', '.join(pat.strengths)}")
            console.print(f"• [bold red]Weaknesses / Struggles:[/bold red] {', '.join(pat.weaknesses)}")
            console.print(f"• [bold cyan]Frequent Approaches:[/bold cyan] {', '.join(pat.frequent_approaches)}")
            console.print(f"• [bold yellow]Frequent Mistakes:[/bold yellow] {', '.join(pat.frequent_mistakes)}")
            console.print(f"• [bold orange3]Neglected Topics:[/bold orange3] {', '.join(pat.neglected_topics) if pat.neglected_topics else 'None'}")
            console.print(f"• [bold blue]Avg Attempts to Solve:[/bold blue] {pat.avg_attempts_to_solve}")

        elif parsed.command == "graph":
            graph = service.get_knowledge_graph()
            console.print(Panel.fit("[bold cyan]Lightweight Knowledge Graph Summary[/bold cyan]"))
            console.print(f"• Total Graph Nodes: [green]{len(graph.nodes)}[/green]")
            console.print(f"• Total Graph Edges: [yellow]{len(graph.edges)}[/yellow]")
            node_types = {}
            for n in graph.nodes:
                node_types[n.type] = node_types.get(n.type, 0) + 1
            console.print(f"• Node Type Breakdown: {node_types}")

        elif parsed.command == "evolution":
            evo = service.get_solution_evolution(parsed.identifier)
            console.print(Panel.fit(f"[bold cyan]Solution Evolution: {evo.problem_title}[/bold cyan]", title="Evolution Narrative"))
            console.print(f"[bold green]Narrative:[/bold green] {evo.evolution_narrative}")
            if evo.key_breakthrough:
                console.print(f"[bold yellow]Breakthrough:[/bold yellow] {evo.key_breakthrough}")
            table = Table(show_header=True, header_style="bold yellow", title="Attempt Sequence")
            table.add_column("#", justify="right")
            table.add_column("Status")
            table.add_column("Inferred Approach")
            table.add_column("Time Complexity")
            table.add_column("Space Complexity")
            for step in evo.steps:
                c = "green" if step.status == "Accepted" else "red"
                table.add_row(str(step.attempt_number), f"[{c}]{step.status}[/{c}]", step.approach, step.time_complexity, step.space_complexity)
            console.print(table)

        elif parsed.command == "semantic":
            sem_results = service.semantic_search(parsed.query)
            console.print(Panel.fit(f"[bold cyan]Semantic Search Query: '{parsed.query}'[/bold cyan]"))
            if not sem_results:
                console.print("[yellow]No relevant semantic matches found.[/yellow]")
                return
            for res in sem_results:
                console.print(f"• [bold green]{res.problem.title}[/bold green] (Relevance: {res.relevance_score})")
                console.print(f"  Snippet: [dim]{res.matched_snippet}[/dim]\n")

        elif parsed.command == "seed":
            console.print("[bold cyan]Seeding sample DSA problems and attempt evolution histories...[/bold cyan]")
            from scripts.seed_data import seed_sample_data
            seed_sample_data(service)
            console.print("[bold green]Seeding complete![/bold green]")

        elif parsed.command == "ui":
            import subprocess
            app_script = Path(__file__).parent.parent / "app" / "app.py"
            # Use the venv-local streamlit to ensure correct environment
            venv_streamlit = Path(sys.executable).parent / "streamlit"
            if not venv_streamlit.exists():
                venv_streamlit = Path(sys.executable).parent / "streamlit.exe"
            if venv_streamlit.exists():
                cmd = [str(venv_streamlit), "run", str(app_script)]
            else:
                cmd = [sys.executable, "-m", "streamlit", "run", str(app_script)]
            console.print(f"[bold cyan]Launching Streamlit UI: {app_script}...[/bold cyan]")
            subprocess.run(cmd)

        elif parsed.command == "leetcode":
            from codememory.connectors.leetcode.importer import LeetCodeImporter
            lc_importer = LeetCodeImporter(storage=service.storage)
            target_path = Path(parsed.path)

            if parsed.action == "validate":
                console.print(f"[bold blue]Validating LeetCode dataset '{target_path}'...[/bold blue]")
                val = lc_importer.validate(target_path)
                console.print(f"Total records read: [yellow]{val['total_records']}[/yellow]")
                console.print(f"Valid records: [green]{val['valid_records']}[/green]")
                console.print(f"Error count: [bold red]{val['error_count']}[/bold red]")
                if val["errors"]:
                    console.print("[bold red]Validation Errors:[/bold red]")
                    for err in val["errors"][:5]:
                        console.print(f" - {err}")

            elif parsed.action == "preview":
                console.print(f"[bold blue]Previewing LeetCode dataset import from '{target_path}'...[/bold blue]")
                prev = lc_importer.preview_import(target_path)
                console.print(f"Total read: [yellow]{prev['total_read']}[/yellow]")
                console.print(f"Valid records: [green]{prev['valid_count']}[/green]")
                console.print(f"Problems discovered: [cyan]{prev['problems_discovered']}[/cyan]")
                console.print(f"Duplicates (skipped): [bold yellow]{prev['duplicate_count']}[/bold yellow]")
                console.print(f"Errors found: [bold red]{prev['error_count']}[/bold red]")

            elif parsed.action == "import":
                console.print(f"[bold cyan]Importing LeetCode dataset from '{target_path}'...[/bold cyan]")
                summary = lc_importer.import_file(target_path)
                console.print(f"[bold green]LeetCode Import Complete![/bold green]")
                console.print(f"  • Total Read: [cyan]{summary.total_read}[/cyan]")
                console.print(f"  • Valid Records: [cyan]{summary.valid_count}[/cyan]")
                console.print(f"  • Imported Submissions: [bold green]{summary.imported_count}[/bold green]")
                console.print(f"  • Duplicates Skipped: [bold yellow]{summary.duplicate_count}[/bold yellow]")
                console.print(f"  • Error Count: [bold red]{summary.error_count}[/bold red]")
                if summary.imported_problems:
                    console.print(f"  • Affected Problems ({len(summary.imported_problems)}): {', '.join(summary.imported_problems)}")

        elif parsed.command == "memory":
            act = parsed.action
            target = parsed.target

            if act == "index":
                console.print("[bold cyan]Indexing CodeMemory documents...[/bold cyan]")
                res = service.memory_engine.index_all(force_rebuild=False)
                console.print(f"[bold green]Indexing Complete![/bold green] Total docs: {res['total_documents']}, Newly indexed: [green]{res['indexed']}[/green], Skipped: [yellow]{res['skipped']}[/yellow], Vector index size: [cyan]{res['vector_count']}[/cyan]")

            elif act == "rebuild":
                console.print("[bold yellow]Rebuilding Memory Vector Index from scratch...[/bold yellow]")
                res = service.memory_engine.index_all(force_rebuild=True)
                console.print(f"[bold green]Rebuild Complete![/bold green] Total vectors indexed: [cyan]{res['vector_count']}[/cyan]")

            elif act == "search":
                query_str = target or ""
                if not query_str:
                    console.print("[bold red]Error:[/bold red] Please provide a search query string.")
                    return
                console.print(f"[bold cyan]Hybrid Memory Search for:[/bold cyan] '{query_str}'\n")
                results = service.memory_engine.search(query_str, top_k=5)
                if not results:
                    console.print("[yellow]No matching memory records found.[/yellow]")
                else:
                    for idx, r in enumerate(results, 1):
                        console.print(f"[bold green]{idx}. {r.title}[/bold green] (Type: [cyan]{r.memory_type.value}[/cyan] | Score: [yellow]{r.score:.2f}[/yellow])")
                        console.print(f"   Snippet: {r.snippet[:120]}...")
                        console.print(f"   Source: [dim]{r.source}[/dim]\n")

            elif act == "similar":
                prob_id = target or ""
                if not prob_id:
                    console.print("[bold red]Error:[/bold red] Please specify a Problem Title, Slug, or ID.")
                    return
                sim_res = service.memory_engine.find_similar_problem(prob_id, top_k=5)
                console.print(f"[bold cyan]Problems Similar to '{prob_id}':[/bold cyan]\n")
                if not sim_res:
                    console.print("[yellow]No similar problems found.[/yellow]")
                else:
                    for s in sim_res:
                        console.print(f" • [bold green]{s.title}[/bold green] ([yellow]{s.difficulty}[/yellow]) — Score: [cyan]{s.similarity_score:.2f}[/cyan]")
                        console.print(f"   Why: {s.explanation}\n")

            elif act == "mistakes":
                console.print(f"[bold cyan]Historical Mistake & Failure Memory Records:[/bold cyan]\n")
                mistakes = service.memory_engine.find_common_mistakes(topic=target)
                if not mistakes:
                    console.print("[yellow]No mistake records found.[/yellow]")
                else:
                    for m in mistakes:
                        console.print(f" • [bold red]{m.title}[/bold red] ([cyan]{m.status}[/cyan])")
                        console.print(f"   {m.snippet}\n")

            elif act == "stats":
                stats = service.memory_engine.get_memory_stats()
                console.print("[bold cyan]CodeMemory Personal Memory Statistics[/bold cyan]")
                console.print(f" • Total Memory Documents: [green]{stats['total_documents']}[/green]")
                console.print(f" • Indexed Embeddings: [cyan]{stats['indexed_vectors']}[/cyan]")
                console.print(f" • Tracked Problems: [yellow]{stats['unique_problems']}[/yellow]")
                console.print(" • Document Type Breakdown:")
                for k, v in stats.get("type_counts", {}).items():
                    console.print(f"    - {k}: {v}")

        elif parsed.command == "health":
            console.print(Panel.fit("[bold cyan]CodeMemory — System Health Check[/bold cyan]"))
            report = service.health_check()
            overall = report.pop("overall", "unknown")
            ts = report.pop("timestamp", "")
            color = "bold green" if overall == "ok" else "bold yellow"
            console.print(f"Overall Status: [{color}]{overall.upper()}[/{color}]  ({ts})\n")

            table = Table(show_header=True, header_style="bold blue")
            table.add_column("Component", style="bold")
            table.add_column("Status")
            table.add_column("Detail")

            for component, data in report.items():
                if not isinstance(data, dict):
                    continue
                status = data.get("status", "unknown")
                status_str = f"[{'green' if status == 'ok' else 'red'}]{status.upper()}[/{'green' if status == 'ok' else 'red'}]"
                detail_parts = [f"{k}={v}" for k, v in data.items() if k != "status"]
                table.add_row(component, status_str, "  ".join(detail_parts))

            console.print(table)

    except CodeMemoryError as cme:
        console.print(f"[bold red]CodeMemory Error:[/bold red] {cme}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
