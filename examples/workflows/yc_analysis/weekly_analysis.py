#!/usr/bin/env python3
"""
Weekly Analysis Runner — AI Agent SBPI
Generates the weekly intelligence digest from RDF data.

Phases:
1. Load latest classifications → run ETL → produce TTL
2. Execute SPARQL query library → collect results
3. Generate markdown digest with key findings
4. (Optional) Push to editorial site

Usage:
    python weekly_analysis.py                    # Full weekly run
    python weekly_analysis.py --week W13-2026    # Specific week
    python weekly_analysis.py --skip-etl         # Reuse existing TTL
    python weekly_analysis.py --digest-only      # Just generate report
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from rdflib import Graph


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
QUERIES_DIR = BASE_DIR / "queries"
ONTOLOGY_PATH = BASE_DIR / "ontology" / "ai-agent-sbpi.ttl"
DIGESTS_DIR = DATA_DIR / "digests"


def current_week_label() -> str:
    """Generate W{N}-{YYYY} label for current week."""
    now = datetime.now()
    return f"W{now.isocalendar()[1]}-{now.year}"


def run_etl(week: str) -> Path:
    """Run the ETL pipeline and return path to TTL file."""
    print(f"\n{'='*60}")
    print(f"  Phase 1: ETL — Loading classifications → RDF")
    print(f"{'='*60}")

    ttl_path = DATA_DIR / f"ai-agent-sbpi-{week}.ttl"
    cmd = [
        sys.executable, str(BASE_DIR / "etl" / "yc_to_rdf.py"),
        "--validate", "--week", week
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
    print(result.stdout)
    if result.returncode != 0:
        print(f"ETL FAILED:\n{result.stderr}")
        sys.exit(1)

    return ttl_path


def load_graph(ttl_path: Path) -> Graph:
    """Load TTL data + ontology."""
    g = Graph()
    g.parse(ttl_path, format="turtle")
    if ONTOLOGY_PATH.exists():
        g.parse(ONTOLOGY_PATH, format="turtle")
    return g


def run_query(g: Graph, query_path: Path) -> list[dict]:
    """Execute a SPARQL query."""
    query_text = query_path.read_text()
    results = g.query(query_text)
    rows = []
    for row in results:
        row_dict = {}
        for var in results.vars:
            val = getattr(row, str(var), None)
            if val is not None:
                try:
                    row_dict[str(var)] = float(val) if "." in str(val) else int(val)
                except (ValueError, TypeError):
                    row_dict[str(var)] = str(val)
            else:
                row_dict[str(var)] = None
        rows.append(row_dict)
    return rows


def generate_digest(g: Graph, week: str) -> str:
    """Generate markdown weekly digest from SPARQL results."""
    lines = [
        f"# AI Agent SBPI — Weekly Intelligence Digest",
        f"**Week**: {week}",
        f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    # --- Summary stats ---
    summary_q = """
    PREFIX asbpi: <https://shurai.com/ontology/ai-agent-sbpi#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT
        (COUNT(DISTINCT ?c) AS ?totalCompanies)
        (SUM(IF(?isAgent, 1, 0)) AS ?agentCount)
        (AVG(?composite) AS ?avgScore)
        (MAX(?composite) AS ?maxScore)
    WHERE {
        ?sr a asbpi:ScoreRecord ;
            asbpi:forCompany ?c ;
            asbpi:compositeScore ?composite .
        ?c asbpi:isAgent ?isAgent ;
           asbpi:isAboutAI true .
    }
    """
    for row in g.query(summary_q):
        lines.extend([
            "## Summary",
            f"- **Total AI companies**: {int(row.totalCompanies)}",
            f"- **True agents**: {int(row.agentCount)} ({int(row.agentCount)/int(row.totalCompanies)*100:.0f}%)",
            f"- **Average SBPI score**: {float(row.avgScore):.1f}",
            f"- **Highest score**: {float(row.maxScore):.1f}",
            "",
        ])

    # --- Tier distribution ---
    tier_q = """
    PREFIX asbpi: <https://shurai.com/ontology/ai-agent-sbpi#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?tier (COUNT(?sr) AS ?count) (AVG(?composite) AS ?avg)
    WHERE {
        ?sr a asbpi:ScoreRecord ;
            asbpi:forCompany ?c ;
            asbpi:compositeScore ?composite ;
            asbpi:inTier ?t .
        ?c asbpi:isAboutAI true .
        ?t rdfs:label ?tier .
    }
    GROUP BY ?tier ORDER BY DESC(?avg)
    """
    lines.append("## Tier Distribution")
    lines.append("| Tier | Companies | Avg Score |")
    lines.append("|------|-----------|-----------|")
    for row in g.query(tier_q):
        lines.append(f"| {row.tier} | {int(row['count'])} | {float(row.avg):.1f} |")
    lines.append("")

    # --- Top 10 agents ---
    top_q = """
    PREFIX asbpi: <https://shurai.com/ontology/ai-agent-sbpi#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?name ?domain ?composite ?tier
    WHERE {
        ?sr a asbpi:ScoreRecord ;
            asbpi:forCompany ?c ;
            asbpi:compositeScore ?composite ;
            asbpi:inTier ?t .
        ?c asbpi:companyName ?name ;
           asbpi:isAgent true ;
           asbpi:inDomain ?d .
        ?d rdfs:label ?domain .
        ?t rdfs:label ?tier .
    }
    ORDER BY DESC(?composite)
    LIMIT 10
    """
    lines.append("## Top 10 AI Agent Companies")
    lines.append("| Rank | Company | Domain | Score | Tier |")
    lines.append("|------|---------|--------|-------|------|")
    for i, row in enumerate(g.query(top_q), 1):
        lines.append(f"| {i} | {row.name} | {row.domain} | {float(row.composite):.1f} | {row.tier} |")
    lines.append("")

    # --- Domain breakdown ---
    domain_q = """
    PREFIX asbpi: <https://shurai.com/ontology/ai-agent-sbpi#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?domain
        (COUNT(?c) AS ?total)
        (SUM(IF(?isAgent, 1, 0)) AS ?agents)
        (AVG(?composite) AS ?avg)
    WHERE {
        ?sr a asbpi:ScoreRecord ;
            asbpi:forCompany ?c ;
            asbpi:compositeScore ?composite .
        ?c asbpi:isAgent ?isAgent ;
           asbpi:isAboutAI true ;
           asbpi:inDomain ?d .
        ?d rdfs:label ?domain .
    }
    GROUP BY ?domain
    ORDER BY DESC(?total)
    """
    lines.append("## Domain Breakdown")
    lines.append("| Domain | Total | Agents | Agent % | Avg Score |")
    lines.append("|--------|-------|--------|---------|-----------|")
    for row in g.query(domain_q):
        total = int(row.total)
        agents = int(row.agents)
        pct = agents / total * 100 if total > 0 else 0
        lines.append(f"| {row.domain} | {total} | {agents} | {pct:.0f}% | {float(row.avg):.1f} |")
    lines.append("")

    # --- Dimension anomalies (top 10) ---
    lines.append("## Key Dimension Anomalies (Top 10)")
    anomaly_q = """
    PREFIX asbpi: <https://shurai.com/ontology/ai-agent-sbpi#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?name ?domain ?dimLabel ?dimValue ?composite ?gap
    WHERE {
        ?sr a asbpi:ScoreRecord ;
            asbpi:forCompany ?c ;
            asbpi:compositeScore ?composite ;
            asbpi:hasDimensionScore ?ds .
        ?c asbpi:companyName ?name ;
           asbpi:isAgent true ;
           asbpi:inDomain ?d .
        ?d rdfs:label ?domain .
        ?ds asbpi:forDimension ?dim ;
            asbpi:dimensionValue ?dimValue .
        ?dim rdfs:label ?dimLabel .
        BIND((?dimValue - ?composite) AS ?gap)
        FILTER(ABS(?gap) > 20)
    }
    ORDER BY DESC(ABS(?gap))
    LIMIT 10
    """
    lines.append("| Company | Domain | Dimension | Value | Composite | Gap |")
    lines.append("|---------|--------|-----------|-------|-----------|-----|")
    for row in g.query(anomaly_q):
        gap = float(row.gap)
        marker = "+" if gap > 0 else ""
        lines.append(f"| {row.name} | {row.domain} | {row.dimLabel} | {int(row.dimValue)} | {float(row.composite):.1f} | {marker}{gap:.1f} |")
    lines.append("")

    # --- Agent vs Tool comparison ---
    lines.append("## Agent vs Tool Comparison")
    avt_q = """
    PREFIX asbpi: <https://shurai.com/ontology/ai-agent-sbpi#>

    SELECT ?isAgent (COUNT(?c) AS ?count) (AVG(?composite) AS ?avg)
    WHERE {
        ?sr a asbpi:ScoreRecord ;
            asbpi:forCompany ?c ;
            asbpi:compositeScore ?composite .
        ?c asbpi:isAgent ?isAgent ;
           asbpi:isAboutAI true .
    }
    GROUP BY ?isAgent
    """
    lines.append("| Category | Count | Avg Score |")
    lines.append("|----------|-------|-----------|")
    for row in g.query(avt_q):
        label = "True Agents" if str(row.isAgent) == "true" else "AI Tools"
        lines.append(f"| {label} | {int(row['count'])} | {float(row.avg):.1f} |")
    lines.append("")

    lines.extend([
        "---",
        f"*Generated by AI Agent SBPI Weekly Analysis Pipeline*",
        f"*Data source: YC company classifications + heuristic dimension scoring*",
        f"*Ontology: ai-agent-sbpi.ttl (OWL 2) + SHACL validation*",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="AI Agent SBPI Weekly Analysis")
    parser.add_argument("--week", default=None, help="Week label (default: current)")
    parser.add_argument("--skip-etl", action="store_true", help="Skip ETL, use existing TTL")
    parser.add_argument("--digest-only", action="store_true", help="Only generate digest")
    args = parser.parse_args()

    week = args.week or current_week_label()

    # Phase 1: ETL
    ttl_path = DATA_DIR / f"ai-agent-sbpi-{week}.ttl"
    if not args.skip_etl and not args.digest_only:
        ttl_path = run_etl(week)
    elif not ttl_path.exists():
        print(f"TTL not found: {ttl_path}. Run without --skip-etl first.")
        sys.exit(1)

    # Phase 2: Load graph
    print(f"\n{'='*60}")
    print(f"  Phase 2: Loading RDF graph")
    print(f"{'='*60}")
    g = load_graph(ttl_path)
    print(f"  Loaded {len(g)} triples")

    # Phase 3: Generate digest
    print(f"\n{'='*60}")
    print(f"  Phase 3: Generating weekly digest")
    print(f"{'='*60}")
    digest = generate_digest(g, week)

    # Save digest
    DIGESTS_DIR.mkdir(exist_ok=True)
    digest_path = DIGESTS_DIR / f"digest-{week}.md"
    digest_path.write_text(digest)
    print(f"  Written to: {digest_path}")

    # Also save as JSON for downstream consumers
    json_path = DIGESTS_DIR / f"digest-{week}.json"
    json_data = {
        "week": week,
        "generated": datetime.now().isoformat(),
        "triples": len(g),
        "digest_path": str(digest_path),
    }
    json_path.write_text(json.dumps(json_data, indent=2))

    # Print digest to stdout
    print(f"\n{'='*60}")
    print(digest)


if __name__ == "__main__":
    main()
