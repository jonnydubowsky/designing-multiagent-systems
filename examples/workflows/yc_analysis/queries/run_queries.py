#!/usr/bin/env python3
"""
SPARQL Query Runner for AI Agent SBPI
Loads RDF data into rdflib graph and executes .rq query files.
Outputs results as formatted tables or JSON.

Usage:
    python queries/run_queries.py                       # Run all queries
    python queries/run_queries.py weekly-movers          # Run specific query
    python queries/run_queries.py --json                 # JSON output
    python queries/run_queries.py --ttl data/custom.ttl  # Custom data file
"""

import argparse
import json
import sys
from pathlib import Path

from rdflib import Graph


def load_graph(ttl_path: Path, ontology_path: Path = None) -> Graph:
    """Load RDF data + ontology into a single graph."""
    g = Graph()
    g.parse(ttl_path, format="turtle")

    if ontology_path and ontology_path.exists():
        g.parse(ontology_path, format="turtle")

    return g


def run_query(g: Graph, query_path: Path) -> list[dict]:
    """Execute a SPARQL query and return results as list of dicts."""
    query_text = query_path.read_text()
    results = g.query(query_text)

    rows = []
    for row in results:
        row_dict = {}
        for var in results.vars:
            val = getattr(row, str(var), None)
            if val is not None:
                # Convert to native Python types
                try:
                    row_dict[str(var)] = float(val) if "." in str(val) else int(val)
                except (ValueError, TypeError):
                    row_dict[str(var)] = str(val)
            else:
                row_dict[str(var)] = None
        rows.append(row_dict)

    return rows


def format_table(rows: list[dict], max_width: int = 120) -> str:
    """Format results as a readable text table."""
    if not rows:
        return "  (no results)"

    cols = list(rows[0].keys())

    # Calculate column widths
    widths = {}
    for col in cols:
        values = [str(row.get(col, ""))[:40] for row in rows]
        widths[col] = max(len(col), max(len(v) for v in values))

    # Header
    header = " | ".join(col.ljust(widths[col]) for col in cols)
    separator = "-+-".join("-" * widths[col] for col in cols)

    # Rows
    lines = [header, separator]
    for row in rows[:30]:  # Limit display to 30 rows
        line = " | ".join(
            str(row.get(col, ""))[:40].ljust(widths[col]) for col in cols
        )
        lines.append(line)

    if len(rows) > 30:
        lines.append(f"  ... and {len(rows) - 30} more rows")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run SPARQL queries against AI Agent SBPI data")
    parser.add_argument("query", nargs="?", help="Query name (without .rq) or 'all'")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--ttl", default=None, help="Path to TTL data file")
    parser.add_argument("--week", default="W12-2026", help="Week label for default TTL file")
    args = parser.parse_args()

    # Resolve paths
    base_dir = Path(__file__).parent.parent
    queries_dir = Path(__file__).parent

    ttl_path = Path(args.ttl) if args.ttl else base_dir / "data" / f"ai-agent-sbpi-{args.week}.ttl"
    ontology_path = base_dir / "ontology" / "ai-agent-sbpi.ttl"

    if not ttl_path.exists():
        print(f"Data file not found: {ttl_path}")
        sys.exit(1)

    # Load graph
    print(f"Loading {ttl_path.name}...", file=sys.stderr)
    g = load_graph(ttl_path, ontology_path)
    print(f"Loaded {len(g)} triples", file=sys.stderr)

    # Find queries to run
    if args.query and args.query != "all":
        query_files = [queries_dir / f"{args.query}.rq"]
        if not query_files[0].exists():
            print(f"Query not found: {query_files[0]}")
            sys.exit(1)
    else:
        query_files = sorted(queries_dir.glob("*.rq"))

    # Run queries
    all_results = {}
    for qf in query_files:
        name = qf.stem
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"  {name}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)

        # Print query comment header
        with open(qf) as f:
            for line in f:
                if line.startswith("#"):
                    print(f"  {line.rstrip()}", file=sys.stderr)
                else:
                    break

        try:
            rows = run_query(g, qf)
            all_results[name] = rows

            if args.json:
                pass  # Collect for final JSON output
            else:
                print(f"\n  Results: {len(rows)} rows\n")
                print(format_table(rows))

        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            all_results[name] = {"error": str(e)}

    if args.json:
        print(json.dumps(all_results, indent=2, default=str))

    # Summary
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  Ran {len(query_files)} queries against {len(g)} triples", file=sys.stderr)
    for name, rows in all_results.items():
        count = len(rows) if isinstance(rows, list) else "ERROR"
        print(f"    {name}: {count} results", file=sys.stderr)


if __name__ == "__main__":
    main()
