"""
YC Agent Analysis Workflow - Main orchestration

Demonstrates production-ready patterns:
• Two-stage filtering saves 90% on LLM costs
• Structured output eliminates hallucination
• Disk checkpoints enable resumable processing
• Independent step testing

Usage:
  python workflow.py                    # Full analysis (all companies)
  python workflow.py --sample 100       # Test run (100 companies)

Requires: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY environment variables

Outputs:
  ./data/analysis.md           # Human-readable report
  ./data/analysis_data.json    # Structured data for Quarto import
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from picoagents.workflow import (
    FunctionStep,
    StepMetadata,
    Workflow,
    WorkflowMetadata,
    WorkflowRunner,
)

try:
    from .models import (
        AnalysisResult,
        ClassifyResult,
        DataResult,
        FilterResult,
        WorkflowConfig,
    )
    from .steps import analyze_trends, classify_agents, filter_keywords, load_data
except ImportError:
    from models import (
        AnalysisResult,
        ClassifyResult,
        DataResult,
        FilterResult,
        WorkflowConfig,
    )
    from steps import analyze_trends, classify_agents, filter_keywords, load_data


async def create_workflow(config: WorkflowConfig) -> Workflow:
    """Create the YC analysis workflow with chained steps."""

    steps = [
        FunctionStep(
            "load",
            StepMetadata(name="Load Data", description="Load and cache YC companies"),
            WorkflowConfig,
            DataResult,
            load_data,
        ),
        FunctionStep(
            "filter",
            StepMetadata(name="Filter Keywords", description="Apply regex filters"),
            DataResult,
            FilterResult,
            filter_keywords,
        ),
        FunctionStep(
            "classify",
            StepMetadata(
                name="Classify Agents",
                description="LLM classification with structured output",
            ),
            FilterResult,
            ClassifyResult,
            classify_agents,
        ),
        FunctionStep(
            "analyze",
            StepMetadata(
                name="Analyze Results", description="Generate insights and trends"
            ),
            ClassifyResult,
            AnalysisResult,
            analyze_trends,
        ),
    ]

    workflow = Workflow(
        metadata=WorkflowMetadata(
            name="YC Agent Analysis",
            description="Analyze Y Combinator companies to identify AI agent trends",
        ),
        initial_state={"config": config},
    ).chain(*steps)

    return workflow


async def main():
    """Run the YC agent analysis workflow."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="YC Agent Analysis Workflow")
    parser.add_argument(
        "--sample", type=int, help="Run on sample of N companies for testing"
    )
    args = parser.parse_args()

    # Check environment - prefer Anthropic, fall back to Azure
    use_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    use_azure = bool(os.getenv("AZURE_OPENAI_ENDPOINT"))

    if not use_anthropic and not use_azure:
        print(
            "❌ Set ANTHROPIC_API_KEY or AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY"
        )
        return

    print("🚀 YC Agent Analysis Workflow")
    if use_anthropic:
        print("🤖 Using Anthropic Claude for classification")
    if args.sample:
        print(f"🧪 Sample mode: {args.sample} companies")
    print("=" * 40)

    # Configure workflow
    config = WorkflowConfig(
        data_dir="./data",
        azure_deployment="gpt-4.1-mini",
        anthropic_model="claude-sonnet-4-5",
        use_anthropic=use_anthropic,
        batch_size=5,  # Start with smaller batches for testing
        sample_size=args.sample,  # Pass sample size for testing
    )

    # Run workflow
    workflow = await create_workflow(config)
    runner = WorkflowRunner()

    start_time = time.time()
    last_event_time = start_time

    async for event in runner.run_stream(workflow, config.model_dump()):
        last_event_time = time.time()
        # Could log events here to understand progress

    stream_complete_time = time.time()
    execution_time = stream_complete_time - start_time

    print(f"\n✅ Workflow stream completed in {execution_time:.1f}s")

    # Check if report files exist
    report_path = Path(config.data_dir) / "analysis.md"
    json_path = Path(config.data_dir) / "analysis_data.json"

    if report_path.exists():
        print(f"📄 Full report: {report_path}")
    if json_path.exists():
        print(f"📊 Structured data: {json_path}")

    if not (report_path.exists() and json_path.exists()):
        print("⚠️ Some output files not found yet - may still be writing")


if __name__ == "__main__":
    asyncio.run(main())
