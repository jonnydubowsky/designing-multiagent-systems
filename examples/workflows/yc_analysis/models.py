"""
Data models for YC analysis workflow.
"""

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class WorkflowConfig(BaseModel):
    """Configuration for the YC analysis workflow."""

    data_dir: str = "./data"  # Keep data within the package
    azure_endpoint: Optional[str] = None
    azure_deployment: str = "gpt-4.1-mini"  # Updated to user's deployment
    anthropic_model: str = "claude-sonnet-4-5"  # Anthropic model for classification
    use_anthropic: bool = True  # Use Anthropic instead of Azure OpenAI
    batch_size: int = 10
    force_refresh: bool = False
    sample_size: Optional[int] = None  # For testing: limit to N companies


class DataResult(BaseModel):
    """Result from data loading step."""

    companies: int
    from_cache: bool


class FilterResult(BaseModel):
    """Result from keyword filtering step."""

    total: int
    ai_companies: int
    agent_keywords: int


class AgentAnalysis(BaseModel):
    """Structured output for agent classification."""

    is_about_ai: bool = Field(
        description="True if company is actually about AI/ML technology (not just keyword matches)"
    )
    domain: str = Field(
        description="Choose one: health, finance, legal, government, education, productivity, software, e_commerce, media, real_estate, transportation, other"
    )
    subdomain: str = Field(description="Fine-grained category within the domain")
    is_agent: bool = Field(
        description="True if company builds autonomous AI agents acting on user's behalf (only relevant if is_about_ai=True)"
    )
    ai_rationale: str = Field(
        description="Why is/isn't this actually about AI technology?"
    )
    agent_rationale: str = Field(description="Why is/isn't this an autonomous agent?")


class ClassifyResult(BaseModel):
    """Result from AI classification step."""

    processed: int
    agents: int
    tokens: int


class AnalysisResult(BaseModel):
    """Final analysis result."""

    total_companies: int
    agent_companies: int
    agent_percentage: float
    top_domains: List[Tuple[str, int]]
    yoy_growth: List[Dict[str, Any]]
