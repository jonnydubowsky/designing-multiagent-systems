"""
Workflow steps for YC analysis - each function is independently testable.
"""

import asyncio
import concurrent.futures
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from picoagents.llm import AzureOpenAIChatCompletionClient
from picoagents.llm import AnthropicChatCompletionClient
from picoagents.messages import SystemMessage, UserMessage
from picoagents.workflow import Context

try:
    from .models import (
        AgentAnalysis,
        AnalysisResult,
        ClassifyResult,
        DataResult,
        FilterResult,
        WorkflowConfig,
    )
except ImportError:
    from models import (
        AgentAnalysis,
        AnalysisResult,
        ClassifyResult,
        DataResult,
        FilterResult,
        WorkflowConfig,
    )


def clean_key_component(text: str) -> str:
    """Clean text component for use in keys by removing special characters."""
    if pd.isna(text) or text is None:
        return ""
    # Convert to string, lowercase, and keep only alphanumeric
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", str(text).strip().lower())
    return cleaned


def generate_long_slug(row: pd.Series) -> str:
    """Generate a long_slug key in format: id_name_slug_website"""
    id_part = clean_key_component(row.get("id", ""))
    name_part = clean_key_component(row.get("name", ""))
    slug_part = clean_key_component(row.get("slug", ""))
    website_part = clean_key_component(row.get("website", ""))

    # Combine parts with underscores, filter out empty parts
    parts = [part for part in [id_part, name_part, slug_part, website_part] if part]
    long_slug = "_".join(parts)
    return long_slug


def save_checkpoint(data: Any, path: Path) -> None:
    """Save data with timestamp."""
    with open(path, "w") as f:
        json.dump(
            {"timestamp": datetime.now().isoformat(), "data": data}, f, default=str
        )


def load_checkpoint(path: Path) -> Any:
    """Load data from checkpoint."""
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)["data"]


async def load_data(config: WorkflowConfig, context: Context) -> DataResult:
    """
    Load YC data with smart caching.

    Engineering patterns demonstrated:
    • Cache with TTL to avoid redundant downloads
    • Data validation and cleaning
    • Shared state via Context
    """
    data_dir = Path(config.data_dir)
    data_dir.mkdir(exist_ok=True)
    cache_file = data_dir / "companies.json"

    # Check cache (24h TTL)
    if cache_file.exists() and not config.force_refresh:
        age = time.time() - cache_file.stat().st_mtime
        if age < 86400:
            df = pd.read_json(cache_file)
            context.set("df", df)
            return DataResult(companies=len(df), from_cache=True)

    # Download fresh data
    url = "https://raw.githubusercontent.com/akshaybhalotia/yc_company_scraper/refs/heads/main/data/combined_companies_data.json"
    df = pd.read_json(url)

    # Clean and process (following original yc.py pattern)
    df = df.drop_duplicates(subset=["id", "slug", "name", "website"], keep="first")
    df["one_liner"] = df.one_liner.fillna("").astype(str)
    df["long_description"] = df.long_description.fillna("").astype(str)
    df["desc"] = df.one_liner + " " + df.long_description
    df["short"] = df.name + " \n " + df.one_liner

    # Filter out rows with insufficient description
    original_length = len(df)
    df = df[df["desc"].notna() & (df["desc"].str.len() >= 5)]
    rows_dropped = original_length - len(df)
    print(
        f"Dropped {rows_dropped} rows where 'desc' was NaN or had length less than 5."
    )

    # Generate long_slug (using original pattern)
    df["long_slug"] = df.apply(generate_long_slug, axis=1)

    # Cache results
    df.to_json(cache_file, orient="records", date_format="iso")
    context.set("df", df)

    return DataResult(companies=len(df), from_cache=False)


async def filter_keywords(data_result: DataResult, context: Context) -> FilterResult:
    """
    Filter companies using regex patterns.

    Engineering patterns demonstrated:
    • Cost optimization through pre-filtering
    • Regex patterns for accuracy
    • Metrics collection
    """
    df = context.get("df")
    config = context.get("config")

    # Apply sampling if specified (for testing)
    if config.sample_size:
        original_size = len(df)
        df = df.sample(n=min(config.sample_size, len(df)), random_state=42)
        print(f"🧪 Sampling {len(df)}/{original_size} companies for testing")
        context.set("df", df)  # Update the filtered dataset

    # Define patterns (enhanced for better coverage)
    AI_REGEX = re.compile(
        r"""
        \bai\b|artificial[\s-]intelligence|machine[\s-]learning|
        llm|nlp|ai-power|ai[\s-]assistant|ai[\s-]copilot|
        ai[\s-]agent|generative[\s-]ai|chatbot|conversational[\s-]ai
    """,
        re.VERBOSE | re.IGNORECASE,
    )
    AGENT_REGEX = re.compile(r"\bagents?\b", re.IGNORECASE)
    HEALTH_REGEX = re.compile(
        r"""
        \b(health(care)?|medical|medicine|med(i)?tech|pharma(ceuticals?)?|biotech|
        wellness|fitness|nutrition|therapy|mental[\s-]health|telemedicine|
        diagnosis|treatment|patient|doctor|hospital|clinic|drug|vaccine|
        health[\s-]tech|life[\s-]sciences?|genomics?|bioinformatics)\b
    """,
        re.VERBOSE | re.IGNORECASE,
    )

    def mentions_ai(text):
        if not isinstance(text, str):
            return False
        return bool(AI_REGEX.search(text.lower()))

    def mentions_ai_agents(text):
        if not isinstance(text, str):
            return False
        text = text.lower()
        return bool(AI_REGEX.search(text) and AGENT_REGEX.search(text))

    def mentions_health(text):
        if not isinstance(text, str):
            return False
        return bool(HEALTH_REGEX.search(text.lower()))

    # Apply filters (following original naming)
    df["mentions_ai_agents"] = df.desc.apply(mentions_ai_agents)
    df["mentions_ai"] = df.desc.apply(mentions_ai)
    df["mentions_health"] = df.desc.apply(mentions_health)

    # Store filtered data
    context.set("filtered_df", df)

    ai_count = df.mentions_ai.sum()
    agent_count = df.mentions_ai_agents.sum()
    health_count = df.mentions_health.sum()

    print(
        f"Filter results: {ai_count} AI, {agent_count} AI+agents, {health_count} health"
    )

    return FilterResult(
        total=len(df), ai_companies=ai_count, agent_keywords=agent_count
    )


async def process_company_batch(companies_batch, client, system_prompt):
    """Process a batch of companies concurrently."""
    batch_results = []

    for company in companies_batch:
        try:
            messages = [
                SystemMessage(content=system_prompt, source="system"),
                UserMessage(
                    content=f"Company: {company['name']}\nDescription: {company['desc']}",
                    source="user",
                ),
            ]

            result = await client.create(messages=messages, output_format=AgentAnalysis)

            if result.structured_output:
                analysis = result.structured_output.model_dump()
                company_data = {**company.to_dict(), **analysis}

                if result.usage:
                    company_data["usage"] = {
                        "tokens_input": result.usage.tokens_input,
                        "tokens_output": result.usage.tokens_output,
                        "total_tokens": result.usage.tokens_input
                        + result.usage.tokens_output,
                        "duration_ms": result.usage.duration_ms,
                        "cost_estimate": result.usage.cost_estimate,
                    }

                batch_results.append(company_data)
                # Less verbose output - just count progress
                pass  # Remove individual company output to reduce noise

            await asyncio.sleep(0.1)  # Rate limit

        except Exception as e:
            print(f"✗ Error processing {company['name']}: {e}")

    return batch_results


async def classify_agents(
    filter_result: FilterResult, context: Context
) -> ClassifyResult:
    """
    Classify AI companies using structured LLM output.

    Engineering patterns demonstrated:
    • Structured output for reliability
    • Batch processing with checkpoints
    • Cost tracking
    """
    config = context.get("config")
    df = context.get("filtered_df")
    data_dir = Path(config.data_dir)

    # Load checkpoint (but not in sample mode to avoid stale data)
    checkpoint_file = data_dir / "classifications.json"

    if config.sample_size:
        # In sample mode, start fresh to avoid stale checkpoint data
        processed = {}
        if checkpoint_file.exists():
            print("🧪 Sample mode: Ignoring existing checkpoint")
    else:
        processed = load_checkpoint(checkpoint_file) or {}

    # Filter to AI companies needing classification
    ai_df = df[df.mentions_ai].copy()
    to_process = ai_df[~ai_df.long_slug.isin(processed.keys())]

    total_tokens = 0

    if len(to_process) == 0:
        all_results = list(processed.values())
    else:
        # Initialize LLM client (Anthropic or Azure)
        if config.use_anthropic:
            client = AnthropicChatCompletionClient(
                model=config.anthropic_model,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )
        else:
            client = AzureOpenAIChatCompletionClient(
                azure_endpoint=config.azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                azure_deployment=config.azure_deployment,
            )

        # Define domain categories with descriptions
        allowed_domains = {
            "health": "Healthcare, medical services, and life sciences",
            "finance": "Banking, investing, insurance, and financial services",
            "legal": "Law, legal services, and compliance",
            "government": "Public sector, civic tech, and government services",
            "education": "Learning, training, and educational technology",
            "productivity": "Workflow, automation, and tools to improve efficiency",
            "software": "Developer tools, platforms, and infrastructure",
            "e_commerce": "Online retail, marketplaces, and commerce platforms",
            "media": "Content creation, publishing, and entertainment",
            "real_estate": "Property, housing, and real estate services",
            "transportation": "Mobility, logistics, and transportation services",
            "other": "Does not fit in the above categories",
        }

        allowed_domain_keys = list(allowed_domains.keys())
        domain_descriptions = ", ".join(
            [f"{k}: {v}" for k, v in allowed_domains.items()]
        )

        system_prompt = f"""You are an expert in AI company analysis.

Analyze the company description in two steps:

**Step 1: AI Validation**
Determine if this company is actually about AI/ML technology:
- is_about_ai=true: Genuinely involves artificial intelligence, machine learning, LLMs, neural networks, etc.
- is_about_ai=false: Just mentions "artificial" in other contexts (artificial flavoring, artificial turf, etc.)

**Step 2: Agent Classification (if AI)**
If the company IS about AI, determine if it builds autonomous agents:
- is_agent=true: AI acts independently on user's behalf (schedules meetings, trades stocks, writes and executes code, calls APIs)
- is_agent=false: AI just generates output or is used in some other minimal way)

Return JSON with: is_about_ai (true/false), domain (choose from: {allowed_domain_keys}), subdomain (fine-grained), is_agent (true/false), ai_rationale (why AI or not), agent_rationale (why agent or not).

**Examples:**
- "AI-powered image generation" → is_about_ai=true, is_agent=false
- "Artificial flavoring company" → is_about_ai=false, is_agent=false
- "AI assistant that books flights autonomously" → is_about_ai=true, is_agent=true
- "ChatGPT-style writing assistant" → is_about_ai=true, is_agent=false

IMPORTANT: Many companies matched our "AI" keyword filter but may not actually be about artificial intelligence technology. Be precise.

Domain descriptions: {domain_descriptions}"""

        # Create batches for concurrent processing
        batch_size = config.batch_size
        companies_list = [row for _, row in to_process.iterrows()]
        batches = [
            companies_list[i : i + batch_size]
            for i in range(0, len(companies_list), batch_size)
        ]

        print(
            f"Processing {len(companies_list)} companies in {len(batches)} batches..."
        )

        # Process batches with limited concurrency
        max_concurrent_batches = 3
        companies_processed = 0

        for batch_group_idx in range(0, len(batches), max_concurrent_batches):
            concurrent_batches = batches[
                batch_group_idx : batch_group_idx + max_concurrent_batches
            ]

            # Track how many we're submitting
            submitting_count = sum(len(batch) for batch in concurrent_batches)
            print(
                f"Submitting batch group {batch_group_idx//max_concurrent_batches + 1}: {submitting_count} companies..."
            )

            # Create tasks for concurrent execution
            tasks = [
                process_company_batch(batch, client, system_prompt)
                for batch in concurrent_batches
            ]

            # Execute batches concurrently
            batch_results_list = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and update checkpoint
            batch_group_processed = 0
            for batch_results in batch_results_list:
                if not isinstance(batch_results, BaseException):
                    for company_data in batch_results:
                        processed[company_data["long_slug"]] = company_data
                        if "usage" in company_data:
                            total_tokens += company_data["usage"]["total_tokens"]
                        batch_group_processed += 1
                else:
                    print(f"Batch failed with error: {batch_results}")

            companies_processed += batch_group_processed

            # Checkpoint after each set of concurrent batches
            save_checkpoint(processed, checkpoint_file)
            print(
                f"✅ Completed: {companies_processed}/{len(companies_list)} companies ({companies_processed*100/len(companies_list):.1f}%)"
            )

        all_results = list(processed.values())

    # Count agents and AI companies
    agents = [r for r in all_results if r.get("is_agent", False)]
    actual_ai_companies = [r for r in all_results if r.get("is_about_ai", False)]

    context.set("classifications", all_results)
    context.set("agents", agents)
    context.set("actual_ai_companies", actual_ai_companies)

    return ClassifyResult(
        processed=len(all_results), agents=len(agents), tokens=total_tokens
    )


async def analyze_trends(
    classify_result: ClassifyResult, context: Context
) -> AnalysisResult:
    """
    Generate analysis and insights.

    Engineering patterns demonstrated:
    • Statistical analysis
    • Automated insight generation
    • Report generation
    """
    config = context.get("config")
    df = context.get("df")
    agents = context.get("agents", [])
    actual_ai_companies = context.get("actual_ai_companies", [])
    all_classifications = context.get("classifications", [])

    # Pipeline validation metrics
    total_companies = len(df)
    companies_with_ai_keyword = len(df[df.mentions_ai])
    companies_with_agent_keyword = len(df[df.mentions_ai_agents])
    actual_ai_count = len(actual_ai_companies)
    agent_count = len(agents)

    # Calculate precision rates
    ai_keyword_precision = (
        (actual_ai_count / companies_with_ai_keyword * 100)
        if companies_with_ai_keyword > 0
        else 0
    )
    agent_keyword_precision = (
        (agent_count / companies_with_agent_keyword * 100)
        if companies_with_agent_keyword > 0
        else 0
    )

    # Domain distribution for all AI companies (not just agents)
    ai_domain_counts = {}
    for company in actual_ai_companies:
        domain = company.get("domain", "unknown")
        ai_domain_counts[domain] = ai_domain_counts.get(domain, 0) + 1

    # Agent domain distribution
    agent_domain_counts = {}
    for agent in agents:
        domain = agent.get("domain", "unknown")
        agent_domain_counts[domain] = agent_domain_counts.get(domain, 0) + 1

    top_ai_domains = sorted(ai_domain_counts.items(), key=lambda x: x[1], reverse=True)[
        :10
    ]
    top_agent_domains = sorted(
        agent_domain_counts.items(), key=lambda x: x[1], reverse=True
    )[:10]

    # Year-over-year analysis for both AI companies and agents
    agent_df = pd.DataFrame(agents) if agents else pd.DataFrame()
    ai_df = pd.DataFrame(actual_ai_companies) if actual_ai_companies else pd.DataFrame()
    yoy_stats = []

    if not df.empty and "launched_at" in df.columns:
        df["year"] = pd.to_datetime(df["launched_at"], errors="coerce").dt.year

        if not agent_df.empty:
            agent_df["year"] = pd.to_datetime(
                agent_df["launched_at"], errors="coerce"
            ).dt.year
        if not ai_df.empty:
            ai_df["year"] = pd.to_datetime(
                ai_df["launched_at"], errors="coerce"
            ).dt.year

        previous_agents = 0
        for year in range(2020, 2026):
            year_total = len(df[df.year == year])
            year_agents = (
                len(agent_df[agent_df.year == year]) if not agent_df.empty else 0
            )
            year_ai = len(ai_df[ai_df.year == year]) if not ai_df.empty else 0

            if year_total > 0:
                agent_percentage = round(year_agents / year_total * 100, 1)
                ai_percentage = round(year_ai / year_total * 100, 1)
                yoy_growth = (
                    round((year_agents - previous_agents) / previous_agents * 100, 1)
                    if previous_agents > 0
                    else 0
                )

                yoy_stats.append(
                    {
                        "year": year,
                        "total_companies": year_total,
                        "ai_companies": year_ai,
                        "ai_percentage": ai_percentage,
                        "agent_companies": year_agents,
                        "agent_percentage": agent_percentage,
                        "yoy_growth": yoy_growth,
                    }
                )
                previous_agents = year_agents

    # Calculate total usage metrics
    all_classifications = context.get("classifications", [])
    total_cost = sum(
        c.get("usage", {}).get("cost_estimate", 0) for c in all_classifications
    )
    total_llm_tokens = sum(
        c.get("usage", {}).get("total_tokens", 0) for c in all_classifications
    )
    avg_tokens_per_company = (
        total_llm_tokens / len(all_classifications) if all_classifications else 0
    )

    # Generate enhanced summary report
    ai_percentage = round(actual_ai_count / total_companies * 100, 1)
    agent_percentage = round(agent_count / total_companies * 100, 1)

    # Create YoY table
    yoy_table = "\n".join(
        [
            "| Year | Total | AI Companies | AI % | Agent Companies | Agent % | YoY Growth |",
            "|------|-------|--------------|------|-----------------|---------|------------|",
        ]
        + [
            f"| {stat['year']} | {stat['total_companies']} | {stat['ai_companies']} | {stat['ai_percentage']}% | {stat['agent_companies']} | {stat['agent_percentage']}% | {stat['yoy_growth']:+.1f}% |"
            for stat in yoy_stats
        ]
    )

    # Create domain tables
    ai_domain_table = "\n".join(
        [
            "| Domain | AI Companies | Percentage |",
            "|--------|--------------|------------|",
        ]
        + [
            f"| {domain} | {count} | {round(count/actual_ai_count*100, 1)}% |"
            for domain, count in top_ai_domains
        ]
    )

    agent_domain_table = (
        "\n".join(
            [
                "| Domain | Agent Companies | Percentage |",
                "|--------|-----------------|------------|",
            ]
            + [
                f"| {domain} | {count} | {round(count/agent_count*100, 1)}% |"
                for domain, count in top_agent_domains
            ]
        )
        if agent_count > 0
        else "No agent companies found."
    )

    summary = f"""# YC AI Agent Analysis Report

## Executive Summary
• **{actual_ai_count}/{total_companies} companies ({ai_percentage}%) are actually about AI**
• **{agent_count}/{actual_ai_count} AI companies ({round(agent_count/actual_ai_count*100, 1) if actual_ai_count > 0 else 0}%) build autonomous agents**
• **Overall agent adoption:** {agent_count}/{total_companies} companies ({agent_percentage}%)

## Pipeline Validation Results
• **AI keyword precision:** {ai_keyword_precision:.1f}% ({actual_ai_count}/{companies_with_ai_keyword} companies)
• **Agent keyword precision:** {agent_keyword_precision:.1f}% ({agent_count}/{companies_with_agent_keyword} companies)
• **Filter efficiency:** {round(len(all_classifications) / total_companies * 100, 1)}% companies needed LLM classification

## Year-over-Year Trends
{yoy_table}

## Top 10 AI Company Domains
{ai_domain_table}

## Top Agent Company Domains
{agent_domain_table}

## Cost Metrics
• **Total LLM cost:** ${total_cost:.2f}
• **Total tokens:** {total_llm_tokens:,}
• **Avg tokens/company:** {avg_tokens_per_company:.0f}
• **Companies analyzed:** {len(all_classifications)}

---
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

    # Save markdown report
    report_file = Path(config.data_dir) / "analysis.md"
    with open(report_file, "w") as f:
        f.write(summary)

    # Save structured JSON data for Quarto import
    analysis_data = {
        "executive_summary": {
            "total_companies": total_companies,
            "ai_companies": actual_ai_count,
            "ai_percentage": ai_percentage,
            "agent_companies": agent_count,
            "agent_percentage": agent_percentage,
            "ai_to_agent_ratio": round(agent_count / actual_ai_count * 100, 1)
            if actual_ai_count > 0
            else 0,
        },
        "pipeline_validation": {
            "companies_with_ai_keyword": companies_with_ai_keyword,
            "companies_with_agent_keyword": companies_with_agent_keyword,
            "ai_keyword_precision": round(ai_keyword_precision, 1),
            "agent_keyword_precision": round(agent_keyword_precision, 1),
            "filter_efficiency": round(
                len(all_classifications) / total_companies * 100, 1
            ),
        },
        "yoy_trends": [
            {
                "Year": stat["year"],
                "Total Companies": stat["total_companies"],
                "AI Companies": stat["ai_companies"],
                "AI %": f"{stat['ai_percentage']}%",
                "Agent Companies": stat["agent_companies"],
                "Agent %": f"{stat['agent_percentage']}%",
                "YoY Growth": f"{stat['yoy_growth']:+.1f}%"
                if stat["yoy_growth"] != 0
                else "—",
            }
            for stat in yoy_stats
        ],
        "top_ai_domains": [
            {
                "Domain": d.replace("_", " ").title(),
                "Companies": c,
                "Percentage": f"{round(c/actual_ai_count*100, 1)}%",
            }
            for d, c in top_ai_domains
        ],
        "top_agent_domains": [
            {
                "Domain": d.replace("_", " ").title(),
                "Companies": c,
                "Percentage": f"{round(c/agent_count*100, 1)}%",
            }
            for d, c in top_agent_domains
        ]
        if agent_count > 0
        else [],
        "cost_metrics": {
            "total_cost": round(total_cost, 2),
            "total_tokens": total_llm_tokens,
            "avg_tokens_per_company": round(avg_tokens_per_company, 0),
            "companies_analyzed": len(all_classifications),
        },
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "sample_mode": config.sample_size is not None,
            "sample_size": config.sample_size,
        },
    }

    json_file = Path(config.data_dir) / "analysis_data.json"
    with open(json_file, "w") as f:
        json.dump(analysis_data, f, indent=2)

    return AnalysisResult(
        total_companies=total_companies,
        agent_companies=agent_count,
        agent_percentage=agent_percentage,
        top_domains=top_agent_domains,
        yoy_growth=yoy_stats,
    )
