#!/usr/bin/env python3
"""
YC Classifications → RDF ETL Pipeline
======================================
Converts PicoAgents workflow output (classifications.json) into RDF triples
compatible with the AI Agent SBPI ontology.

Step 1: Load classifications from checkpoint
Step 2: Score each company across 5 dimensions using heuristics
Step 3: Generate RDF triples via rdflib
Step 4: Validate against SHACL shapes
Step 5: Optionally load into Oxigraph store

Usage:
    python yc_to_rdf.py                    # Generate RDF from latest classifications
    python yc_to_rdf.py --validate         # Run SHACL validation
    python yc_to_rdf.py --store PATH       # Load into Oxigraph store
    python yc_to_rdf.py --output FILE      # Write to specific file
"""

import json
import re
import sys
import argparse
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal

try:
    from rdflib import Graph, Namespace, Literal, URIRef
    from rdflib.namespace import RDF, RDFS, OWL, XSD, DCTERMS, PROV
except ImportError:
    print("Missing dependency: pip install rdflib")
    sys.exit(1)

# --- Namespaces ---
ASBPI = Namespace("https://shurai.com/ontology/ai-agent-sbpi#")
COMPANY = Namespace("https://shurai.com/data/agent-company/")
WEEK = Namespace("https://shurai.com/data/agent-week/")
SCORE = Namespace("https://shurai.com/data/agent-score/")

# --- Paths ---
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data"
ONTOLOGY_DIR = SCRIPT_DIR.parent / "ontology"

# --- Dimension weights ---
DIMENSIONS = {
    "mc": {"uri": ASBPI.ModelCapability, "weight": 0.20},
    "mt": {"uri": ASBPI.MarketTraction, "weight": 0.25},
    "pe": {"uri": ASBPI.PlatformEcosystem, "weight": 0.20},
    "ad": {"uri": ASBPI.AutonomyDepth, "weight": 0.20},
    "cd": {"uri": ASBPI.CapitalDefensibility, "weight": 0.15},
}

# --- Tier boundaries ---
TIERS = [
    (85, 100, ASBPI.TierDominant),
    (70, 84, ASBPI.TierStrong),
    (55, 69, ASBPI.TierEmerging),
    (40, 54, ASBPI.TierNiche),
    (0, 39, ASBPI.TierLimited),
]

# --- Domain mapping ---
DOMAIN_MAP = {
    "health": ASBPI.DomainHealth,
    "finance": ASBPI.DomainFinance,
    "legal": ASBPI.DomainLegal,
    "government": ASBPI.DomainGovernment,
    "education": ASBPI.DomainEducation,
    "productivity": ASBPI.DomainProductivity,
    "software": ASBPI.DomainSoftware,
    "e_commerce": ASBPI.DomainEcommerce,
    "media": ASBPI.DomainMedia,
    "real_estate": ASBPI.DomainRealEstate,
    "transportation": ASBPI.DomainTransportation,
    "other": ASBPI.DomainOther,
}


def slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    # Ensure slug starts with a letter (SHACL pattern requirement)
    if s and not s[0].isalpha():
        s = "co-" + s
    return s or "unknown"


def get_tier(score: float) -> URIRef:
    """Map composite score to tier URI."""
    for floor, ceiling, uri in TIERS:
        if floor <= score <= ceiling:
            return uri
    return ASBPI.TierLimited


def score_model_capability(company: dict) -> int:
    """Heuristic scoring for Model Capability dimension."""
    score = 40  # Base: is about AI

    desc = (company.get("desc", "") or "").lower()

    if company.get("domain") == "software":
        score += 10
    if any(kw in desc for kw in ["llm", "foundation model", "fine-tun", "training"]):
        score += 15
    if any(kw in desc for kw in ["gpt wrapper", "api wrapper", "uses openai"]):
        score -= 10
    if any(kw in desc for kw in ["multimodal", "vision", "audio", "speech"]):
        score += 10
    if any(kw in desc for kw in ["research", "benchmark", "state-of-the-art"]):
        score += 10
    if any(kw in desc for kw in ["open source", "open-source"]):
        score += 5

    return max(0, min(100, score))


def score_market_traction(company: dict) -> int:
    """Heuristic scoring for Market Traction dimension."""
    score = 35  # Base: YC-backed

    desc = (company.get("desc", "") or "").lower()

    # Year-based maturity proxy
    launched = company.get("launched_at", "")
    if launched:
        try:
            year = int(str(launched)[:4])
            if year <= 2021:
                score += 20  # More mature
            elif year <= 2023:
                score += 10
        except (ValueError, TypeError):
            pass

    if any(kw in desc for kw in ["enterprise", "fortune 500", "fortune500"]):
        score += 20
    if any(kw in desc for kw in ["beta", "waitlist", "early access"]):
        score -= 10
    if any(kw in desc for kw in ["revenue", "paying customer", "arr"]):
        score += 15
    if any(kw in desc for kw in ["million user", "thousands of", "growing"]):
        score += 10

    return max(0, min(100, score))


def score_platform_ecosystem(company: dict) -> int:
    """Heuristic scoring for Platform Ecosystem dimension."""
    score = 30  # Base

    desc = (company.get("desc", "") or "").lower()

    if any(kw in desc for kw in ["api", "sdk", "platform"]):
        score += 20
    if any(kw in desc for kw in ["open source", "open-source", "github"]):
        score += 15
    if any(kw in desc for kw in ["integration", "marketplace", "plugin"]):
        score += 10
    if any(kw in desc for kw in ["developer", "dev tool", "infrastructure"]):
        score += 10
    if any(kw in desc for kw in ["mcp", "tool use", "function calling"]):
        score += 10

    return max(0, min(100, score))


def score_autonomy_depth(company: dict) -> int:
    """Heuristic scoring for Autonomy Depth dimension."""
    if company.get("is_agent"):
        score = 60  # Agent classification base
    else:
        score = 25  # Non-agent base

    desc = (company.get("desc", "") or "").lower()

    if any(kw in desc for kw in ["autonomous", "independently", "on behalf"]):
        score += 15
    if any(kw in desc for kw in ["multi-agent", "orchestrat", "multi agent"]):
        score += 15
    if any(kw in desc for kw in ["assistant", "copilot"]):
        score = max(score, 45)
    if any(kw in desc for kw in ["chatbot", "chat bot"]):
        score = max(score, 30)
    if any(kw in desc for kw in ["execute", "action", "automate"]):
        score += 10
    if any(kw in desc for kw in ["workflow", "pipeline", "chain"]):
        score += 5

    return max(0, min(100, score))


def score_capital_defensibility(company: dict) -> int:
    """Heuristic scoring for Capital & Defensibility dimension."""
    score = 40  # Base: YC-backed is a defensibility signal

    desc = (company.get("desc", "") or "").lower()

    if any(kw in desc for kw in ["patent", "proprietary data", "proprietary"]):
        score += 20
    if any(kw in desc for kw in ["hipaa", "soc 2", "fedramp", "regulated"]):
        score += 10
    if any(kw in desc for kw in ["enterprise", "government"]):
        score += 5

    # Older companies have had more time to build moats
    launched = company.get("launched_at", "")
    if launched:
        try:
            year = int(str(launched)[:4])
            if year <= 2021:
                score += 10
        except (ValueError, TypeError):
            pass

    return max(0, min(100, score))


def compute_composite(scores: dict) -> float:
    """Compute weighted composite score."""
    total = 0.0
    for code, dim_info in DIMENSIONS.items():
        total += scores[code] * dim_info["weight"]
    return round(total, 2)


def build_rdf(classifications: dict, week_label: str) -> Graph:
    """Convert classifications dict to RDF graph."""
    g = Graph()
    g.bind("asbpi", ASBPI)
    g.bind("company", COMPANY)
    g.bind("week", WEEK)
    g.bind("score", SCORE)
    g.bind("prov", PROV)
    g.bind("dcterms", DCTERMS)

    # Week node
    week_uri = WEEK[week_label]
    g.add((week_uri, RDF.type, ASBPI.Week))
    g.add((week_uri, ASBPI.weekLabel, Literal(week_label, datatype=XSD.string)))

    companies_processed = 0
    agents_found = 0

    seen_slugs = set()
    for long_slug, company in classifications.items():
        if not company.get("is_about_ai", False):
            continue

        slug = slugify(company.get("name", long_slug))
        # Deduplicate: append YC ID if slug collision
        if slug in seen_slugs:
            cid = company.get("id", "")
            slug = f"{slug}-{cid}" if cid else f"{slug}-{hash(long_slug) % 10000}"
        seen_slugs.add(slug)
        company_uri = COMPANY[slug]

        # Company node
        g.add((company_uri, RDF.type, ASBPI.AgentCompany))
        g.add((company_uri, ASBPI.companyName, Literal(company.get("name", ""), datatype=XSD.string)))
        g.add((company_uri, ASBPI.slug, Literal(slug, datatype=XSD.string)))
        g.add((company_uri, ASBPI.isAgent, Literal(company.get("is_agent", False), datatype=XSD.boolean)))
        g.add((company_uri, ASBPI.isAboutAI, Literal(True, datatype=XSD.boolean)))
        g.add((company_uri, ASBPI.inVertical, ASBPI.AIAgentVertical))

        # Domain
        domain = company.get("domain", "other")
        domain_uri = DOMAIN_MAP.get(domain, ASBPI.DomainOther)
        g.add((company_uri, ASBPI.inDomain, domain_uri))

        # Optional properties
        if company.get("one_liner"):
            g.add((company_uri, ASBPI.oneLiner, Literal(company["one_liner"], datatype=XSD.string)))
        if company.get("ai_rationale"):
            g.add((company_uri, ASBPI.aiRationale, Literal(company["ai_rationale"], datatype=XSD.string)))
        if company.get("agent_rationale"):
            g.add((company_uri, ASBPI.agentRationale, Literal(company["agent_rationale"], datatype=XSD.string)))
        if company.get("subdomain"):
            g.add((company_uri, ASBPI.subdomain, Literal(company["subdomain"], datatype=XSD.string)))
        if company.get("id"):
            g.add((company_uri, ASBPI.ycId, Literal(str(company["id"]), datatype=XSD.string)))
        if company.get("website"):
            g.add((company_uri, ASBPI.website, Literal(company["website"], datatype=XSD.anyURI)))
        if company.get("launched_at"):
            try:
                launch_date = str(company["launched_at"])[:10]
                g.add((company_uri, ASBPI.launchedAt, Literal(launch_date, datatype=XSD.date)))
            except (ValueError, TypeError):
                pass

        # Score dimensions
        dim_scores = {
            "mc": score_model_capability(company),
            "mt": score_market_traction(company),
            "pe": score_platform_ecosystem(company),
            "ad": score_autonomy_depth(company),
            "cd": score_capital_defensibility(company),
        }
        composite = compute_composite(dim_scores)
        tier_uri = get_tier(composite)

        # Score record
        score_uri = SCORE[f"{slug}-{week_label}"]
        g.add((score_uri, RDF.type, ASBPI.ScoreRecord))
        g.add((score_uri, ASBPI.forCompany, company_uri))
        g.add((score_uri, ASBPI.forWeek, week_uri))
        g.add((score_uri, ASBPI.compositeScore, Literal(Decimal(str(composite)), datatype=XSD.decimal)))
        g.add((score_uri, ASBPI.delta, Literal(Decimal("0"), datatype=XSD.decimal)))  # First week: delta=0
        g.add((score_uri, ASBPI.inTier, tier_uri))

        # Dimension scores
        for code, value in dim_scores.items():
            ds_uri = SCORE[f"{slug}-{week_label}-{code}"]
            g.add((ds_uri, RDF.type, ASBPI.DimensionScore))
            g.add((ds_uri, ASBPI.forDimension, DIMENSIONS[code]["uri"]))
            g.add((ds_uri, ASBPI.dimensionValue, Literal(value, datatype=XSD.integer)))
            g.add((score_uri, ASBPI.hasDimensionScore, ds_uri))

        # Attestation (automated inference from YC data)
        att_uri = SCORE[f"{slug}-{week_label}-att"]
        g.add((att_uri, RDF.type, ASBPI.Attestation))
        g.add((att_uri, ASBPI.confidence, Literal(Decimal("0.60"), datatype=XSD.decimal)))
        g.add((att_uri, ASBPI.sourceType, Literal("automated_inference", datatype=XSD.string)))
        g.add((score_uri, ASBPI.hasAttestation, att_uri))

        companies_processed += 1
        if company.get("is_agent"):
            agents_found += 1

    return g, companies_processed, agents_found


def validate_graph(g: Graph) -> bool:
    """Validate RDF graph against SHACL shapes."""
    try:
        from pyshacl import validate as shacl_validate
    except ImportError:
        print("pyshacl not installed, skipping validation")
        return True

    shapes_path = ONTOLOGY_DIR / "ai-agent-sbpi-shapes.ttl"
    ontology_path = ONTOLOGY_DIR / "ai-agent-sbpi.ttl"
    if not shapes_path.exists():
        print(f"Shapes file not found: {shapes_path}")
        return False

    shapes_graph = Graph()
    shapes_graph.parse(str(shapes_path), format="turtle")

    # Load ontology into data graph so class instances are visible to SHACL
    ont_graph = Graph()
    if ontology_path.exists():
        ont_graph.parse(str(ontology_path), format="turtle")

    # Merge ontology + data for validation
    combined = g + ont_graph

    conforms, results_graph, results_text = shacl_validate(
        data_graph=combined,
        shacl_graph=shapes_graph,
        inference="none",
    )

    if conforms:
        print("SHACL validation: PASSED")
    else:
        print("SHACL validation: FAILED")
        print(results_text[:2000])

    return conforms


def main():
    parser = argparse.ArgumentParser(description="YC Classifications → RDF ETL")
    parser.add_argument("--validate", action="store_true", help="Run SHACL validation")
    parser.add_argument("--store", type=str, help="Oxigraph store path")
    parser.add_argument("--output", type=str, help="Output Turtle file path")
    parser.add_argument("--week", type=str, help="Week label (default: current week)")
    args = parser.parse_args()

    # Determine week label
    if args.week:
        week_label = args.week
    else:
        now = datetime.now()
        week_num = now.isocalendar()[1]
        week_label = f"W{week_num}-{now.year}"

    # Load classifications
    checkpoint_file = DATA_DIR / "classifications.json"
    if not checkpoint_file.exists():
        print(f"No classifications found at {checkpoint_file}")
        print("Run the workflow first: python workflow.py")
        sys.exit(1)

    with open(checkpoint_file) as f:
        checkpoint = json.load(f)
    classifications = checkpoint.get("data", checkpoint)

    print(f"Loaded {len(classifications)} classifications")

    # Build RDF
    g, companies, agents = build_rdf(classifications, week_label)
    triples = len(g)

    print(f"Generated {triples} triples for {companies} AI companies ({agents} agents)")
    print(f"Week: {week_label}")

    # Output
    output_path = args.output or str(DATA_DIR / f"ai-agent-sbpi-{week_label}.ttl")
    g.serialize(destination=output_path, format="turtle")
    print(f"Written to: {output_path}")

    # Validate
    if args.validate:
        validate_graph(g)

    # Load to store
    if args.store:
        try:
            import pyoxigraph
            store = pyoxigraph.Store(args.store)
            ttl_content = g.serialize(format="turtle")
            store.load(ttl_content.encode(), "text/turtle")
            print(f"Loaded into Oxigraph store: {args.store}")
        except ImportError:
            print("pyoxigraph not installed, cannot load to store")
        except Exception as e:
            print(f"Store load error: {e}")

    # Summary stats
    print("\n--- Summary ---")
    print(f"Total AI companies: {companies}")
    print(f"Agent companies: {agents}")
    print(f"Agent rate: {agents/companies*100:.1f}%")
    print(f"Total triples: {triples}")
    print(f"Week: {week_label}")


if __name__ == "__main__":
    main()
