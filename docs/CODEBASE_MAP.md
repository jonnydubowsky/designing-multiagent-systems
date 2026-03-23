# CODEBASE_MAP.md -- Designing Multi-Agent Systems

> Victor Dibia's companion repository for "Designing Multi-Agent Systems."
> Contains the **PicoAgents** framework (a minimal, educational multi-agent framework),
> production workflow examples (YC Analysis), course samples across 8+ agent frameworks,
> and research data on the AI-agent startup landscape.

---

## Repository Layout

```
designing-multiagent-systems/
├── picoagents/                  # PicoAgents framework (core library)
│   ├── src/picoagents/          # Framework source (~31k LOC Python)
│   ├── tests/                   # Test suite (~12k LOC, pytest-asyncio)
│   ├── docs/                    # Framework-specific docs (memory_tool.md)
│   ├── pyproject.toml           # Package config, deps, optional extras
│   └── README.md                # Framework readme
├── examples/                    # Runnable examples organized by capability
│   ├── agents/                  # Agent patterns (basic, structured output, memory, etc.)
│   ├── orchestration/           # Orchestration patterns (round-robin, AI-driven, plan-based)
│   ├── workflows/               # Workflow examples (YC analysis, data viz, sequential)
│   ├── tools/                   # Tool usage examples (approval, context, youtube)
│   ├── mcp/                     # MCP integration examples
│   ├── memory/                  # Memory system examples
│   ├── evaluation/              # Eval system examples
│   ├── webui/                   # WebUI usage examples
│   ├── otel/                    # OpenTelemetry tracing examples
│   ├── frameworks/              # Same patterns in other frameworks for comparison
│   │   ├── agent-framework/     # Microsoft Agent Framework
│   │   ├── claude-agent-sdk/    # Anthropic Claude Agent SDK
│   │   ├── google-adk/          # Google ADK
│   │   └── langgraph/           # LangGraph
│   └── notebooks/               # Jupyter notebooks
├── course/                      # Course materials (hello_world, RAG, router, voice, etc.)
│   ├── samples/                 # Per-use-case implementations across frameworks
│   ├── generate_results.py      # Result generation script
│   └── generate_meta.py         # Metadata generation script
├── code_along/                  # Step-by-step code-along files (ch04 progressive build)
├── research/                    # Research data and analysis
│   ├── ycdata/                  # Y Combinator company data + agent analysis scripts
│   ├── frameworks/              # Framework comparison metadata (JSON)
│   ├── components/              # Component gallery and team configs
│   └── news/                    # News data
├── workspace/                   # Scratch workspace (calculator example)
├── premium-samples/             # Premium sample listings
├── docs/                        # Documentation directory
│   └── images/                  # Documentation images
├── images/                      # Repository images
├── .devcontainer/               # Dev container configuration
├── README.md                    # Main repo readme
├── LICENSE                      # MIT License
└── Citation.cff                 # Citation metadata
```

---

## PicoAgents Framework Architecture

**Version**: 0.4.0 | **Python**: >=3.10 | **License**: MIT

PicoAgents is a lightweight, type-safe framework built on Pydantic v2 for building AI agents with LLMs. It supports tool calling, memory, streaming, structured output, multi-agent orchestration, workflows, evaluation, and a web UI.

### Module Map

```
picoagents/src/picoagents/
├── __init__.py                  # Public API surface -- exports everything below
├── types.py                     # Core Pydantic models: Usage, ToolResult, AgentResponse,
│                                #   ChatCompletionResult, AgentEvent union, OrchestrationResponse,
│                                #   Task, RunTrajectory, EvalScore, streaming event hierarchy
├── messages.py                  # Message types: SystemMessage, UserMessage, AssistantMessage,
│                                #   ToolMessage, MultiModalMessage, ToolCallRequest
├── context.py                   # AgentContext: messages + metadata + shared_state + environment
│                                #   ToolApprovalRequest / ToolApprovalResponse for HITL
├── compaction.py                # Context compaction: NoCompaction, SlidingWindowCompaction,
│                                #   HeadTailCompaction (manage context window size)
├── _cancellation_token.py       # CancellationToken for cooperative cancellation across async tasks
├── _component_config.py         # Component serialization system (ComponentBase, Component,
│                                #   ComponentModel) -- enables JSON config round-tripping
├── _hooks.py                    # Deterministic loop hooks: BaseStartHook, BaseEndHook,
│                                #   PlanningHook, CompletionCheckHook, LLMCompletionCheckHook,
│                                #   TerminationCondition, CompositeTermination
├── _instructions.py             # Instruction presets (get_instructions)
├── _middleware.py               # Middleware chain: LoggingMiddleware, RateLimitMiddleware,
│                                #   PIIRedactionMiddleware, GuardrailMiddleware, MetricsMiddleware
├── _otel.py                     # OpenTelemetry auto-instrumentation (opt-in via env var)
│
├── agents/                      # Agent implementations
│   ├── _base.py                 # BaseAgent ABC: run(), run_stream(), as_tool(), middleware,
│   │                            #   memory integration, tool processing, context preparation
│   ├── _agent.py                # Agent (concrete): tool loop with structured output, streaming,
│   │                            #   hooks, compaction, approval workflow, persist support
│   ├── _agent_as_tool.py        # AgentAsTool: wrap any agent as a tool for hierarchical composition
│   └── _computer_use/           # Computer use agent (Playwright-based browser automation)
│       ├── _computer_use.py     # ComputerUseAgent implementation
│       ├── _playwright_tools.py # Browser interaction tools
│       ├── _planning_models.py  # Planning models for multi-step browser tasks
│       └── _interface_clients.py # Interface abstraction for different browsers
│
├── llm/                         # LLM client abstraction layer
│   ├── _base.py                 # BaseChatCompletionClient ABC: create(), create_stream(),
│   │                            #   message format conversion, error hierarchy
│   ├── _openai.py               # OpenAIChatCompletionClient: GPT models, structured output
│   │                            #   via json_schema, streaming with usage tracking, cost estimation
│   ├── _azure_openai.py         # AzureOpenAIChatCompletionClient: Azure-hosted models
│   └── _anthropic.py            # AnthropicChatCompletionClient: Claude models with native
│                                #   tool_use blocks and structured output
│
├── tools/                       # Tool system
│   ├── _base.py                 # BaseTool, FunctionTool, ApprovalMode (always/never/once)
│   ├── _decorator.py            # @tool decorator for function-to-tool conversion
│   ├── _core_tools.py           # Built-in: Calculator, DateTime, JSONParser, Regex, ThinkTool,
│   │                            #   TaskStatusTool
│   ├── _coding_tools.py         # File read/write/list, bash execution tools
│   ├── _context_tools.py        # Context engineering: TaskTool, TodoWriteTool, TodoReadTool,
│   │                            #   SkillsTool (SKILL.md injection), MultiEditTool
│   ├── _memory_tool.py          # MemoryTool: agent-controlled memory add/search/list/delete
│   ├── _research_tools.py       # ArxivSearchTool, YouTubeCaptionTool
│   └── _mcp/                    # MCP (Model Context Protocol) integration
│       ├── _client.py           # MCPClientManager: lifecycle management for MCP servers
│       ├── _tool.py             # MCPTool: wraps MCP server tools as PicoAgents tools
│       ├── _integration.py      # create_mcp_tools() helper
│       ├── _config.py           # MCPServerConfig, StdioServerConfig, HTTPServerConfig
│       └── _transports.py       # Transport layer abstraction (stdio, HTTP)
│
├── memory/                      # Memory system
│   ├── _base.py                 # BaseMemory ABC, ListMemory (in-memory), FileMemory (JSON file),
│   │                            #   MemoryContent, MemoryQueryResult
│   └── _chromadb.py             # ChromaDBMemory: vector similarity search via ChromaDB
│
├── orchestration/               # Multi-agent orchestration patterns
│   ├── _base.py                 # BaseOrchestrator ABC: universal orchestration loop with
│   │                            #   streaming, cancellation, usage aggregation, termination checks
│   ├── _round_robin.py          # RoundRobinOrchestrator: fixed-order agent cycling
│   ├── _ai.py                   # AIOrchestrator: LLM-based agent selection with structured output
│   │                            #   (AgentSelection model with confidence scoring)
│   ├── _plan.py                 # PlanBasedOrchestrator: LLM generates ExecutionPlan with PlanSteps,
│   │                            #   evaluates progress via StepProgressEvaluation, retry logic
│   └── _handoff.py              # HandoffOrchestrator: TODO stub for agent-to-agent handoff
│
├── termination/                 # Termination conditions (composable)
│   ├── _base.py                 # BaseTermination ABC
│   ├── _max_message.py          # MaxMessageTermination
│   ├── _text_mention.py         # TextMentionTermination (stop on keyword)
│   ├── _token_usage.py          # TokenUsageTermination
│   ├── _timeout.py              # TimeoutTermination
│   ├── _handoff.py              # HandoffTermination
│   ├── _function_call.py        # FunctionCallTermination
│   ├── _external.py             # ExternalTermination (programmatic stop)
│   ├── _cancellation.py         # CancellationTermination
│   └── _composite.py            # CompositeTermination (AND/OR logic)
│
├── workflow/                    # Deterministic workflow engine
│   ├── __init__.py              # Exports: Workflow, WorkflowRunner, steps, Context
│   ├── schema_utils.py          # Schema validation utilities
│   ├── defaults.py              # Default workflow configurations
│   ├── core/
│   │   ├── _workflow.py         # Workflow: DAG of steps with edges, conditions, validation,
│   │   │                        #   cycle detection, type compatibility checks, chain() helper
│   │   ├── _runner.py           # WorkflowRunner: parallel execution with semaphore control,
│   │   │                        #   streaming events, checkpoint support, cancellation
│   │   ├── _models.py           # Core models: StepStatus, WorkflowStatus, Edge, EdgeCondition,
│   │   │                        #   Context (shared mutable state + emit_progress), event hierarchy
│   │   └── _checkpoint.py       # CheckpointStore ABC, FileCheckpointStore, InMemoryCheckpointStore,
│   │                            #   WorkflowCheckpoint, structure hash for safe resume
│   └── steps/
│       ├── _step.py             # BaseStep[Input, Output]: typed step with schema serialization
│       ├── _function.py         # FunctionStep: wraps async functions as workflow steps
│       ├── _echo.py             # EchoStep: pass-through (testing)
│       ├── _http.py             # HttpStep: HTTP request step
│       ├── _transform.py        # TransformStep: data transformation
│       └── picoagent.py         # PicoAgentStep: wraps a PicoAgents Agent as a workflow step
│
├── eval/                        # Evaluation framework
│   ├── _base.py                 # EvalJudge ABC, Target ABC
│   ├── _runner.py               # EvalRunner: run targets against datasets, parallel execution
│   ├── _targets.py              # AgentEvalTarget, ModelEvalTarget, OrchestratorEvalTarget,
│   │                            #   PicoAgentTarget, ClaudeCodeTarget, CallableTarget
│   ├── _dataset.py              # Dataset: load from JSON/dict, built-in datasets
│   ├── _config.py               # AgentConfig for eval parameterization
│   ├── _results.py              # EvalResults, TaskResult, TargetSummary, persistence
│   ├── _analysis.py             # Result formatting: summary tables, task breakdowns,
│   │                            #   token growth analysis, file read analysis
│   ├── _middleware.py           # RunMiddleware for eval pipeline
│   ├── judges/
│   │   ├── _base.py             # BaseEvalJudge, ExactMatchJudge, FuzzyMatchJudge, ContainsJudge
│   │   ├── _llm.py              # LLMEvalJudge: LLM-based scoring with dimensional breakdown
│   │   ├── _composite.py        # CompositeJudge: combine multiple judges
│   │   └── _reference.py        # Reference-based evaluation
│   ├── datasets/                # Built-in evaluation datasets
│   └── examples/
│       └── basic_evaluation.py  # Example eval workflow
│
├── store/                       # Persistence layer (optional: picoagents[persist])
│   ├── _store.py                # PicoStore: SQLModel async engine, saves agent/orchestrator/eval
│   │                            #   runs to SQLite (swappable to Postgres), JSON files for full data
│   ├── _models.py               # DB models: DBRun, DBEvalRun, DBEvalResult, DBDataset, DBTask
│   └── _converters.py           # Convert framework objects to/from DB models
│
├── webui/                       # Web UI (optional: picoagents[web])
│   ├── _server.py               # PicoAgentsWebUIServer: FastAPI app, REST API for entities,
│   │                            #   sessions, streaming execution, GitHub example import
│   ├── _registry.py             # EntityRegistry: auto-discover agents/orchestrators/workflows
│   ├── _discovery.py            # File-based entity discovery from Python modules
│   ├── _execution.py            # ExecutionEngine: run agents/orchestrators/workflows with streaming
│   ├── _sessions.py             # SessionManager: session state management
│   ├── _session_store.py        # Session persistence
│   ├── _models.py               # API models: Entity, HealthResponse, AddExampleRequest
│   ├── _cli.py                  # CLI entry point for `picoagents` command
│   ├── _eval_jobs.py            # Background eval job management
│   ├── _eval_router.py          # FastAPI router for eval endpoints
│   ├── _runs_router.py          # FastAPI router for run history endpoints
│   ├── ui/                      # Pre-built frontend (Vite + React)
│   │   └── assets/              # Bundled JS/CSS
│   └── frontend/                # Frontend source (TypeScript + React)
│       ├── src/
│       │   ├── types/           # TypeScript type definitions (picoagents.ts, eval.ts)
│       │   ├── components/      # React components (message renderer)
│       │   ├── hooks/           # Custom hooks (useEntityExecution, messageHandlers)
│       │   └── services/        # API client (api.ts, eval-api.ts)
│       └── vite.config.ts       # Vite build configuration
│
├── cli/                         # CLI interface
│   └── _main.py                 # `picoagents` CLI entry point (uvicorn launcher)
│
└── skills/                      # Skill definitions (SKILL.md files for SkillsTool)
    ├── code-review/SKILL.md     # Code review skill prompt
    └── debug/SKILL.md           # Debug skill prompt
```

---

## Key Architectural Patterns

### 1. Agent Execution Loop

The core agent loop in `agents/_agent.py` follows this pattern:

```
run(task) ->
  1. Convert task to messages
  2. Run start_hooks (inject planning prompts, etc.)
  3. Loop (max_iterations):
     a. Apply compaction strategy to manage context window
     b. Prepare messages (system prompt + memory + history + task)
     c. Call LLM via model_client.create() with tools and output_format
     d. If tool_calls in response:
        - Check approval mode (always/never/once)
        - Execute approved tools, collect results
        - If summarize_tool_result=False, return immediately
        - Otherwise, continue loop with tool results in context
     e. If no tool_calls:
        - Run end_hooks (check todo completion, etc.)
        - If end_hook injects UserMessage, continue loop
        - Otherwise, break
  4. Return AgentResponse with context, usage, finish_reason
```

### 2. Structured Output

Structured output flows through the LLM client layer. When `output_format` (a Pydantic model) is provided:

- **OpenAI**: Converts to JSON schema via `response_format.json_schema` with `strict: True`. The `_make_schema_compatible()` method ensures all properties are required and `additionalProperties: false`.
- **Anthropic**: Uses native tool_use blocks to enforce structured output.
- **Azure**: Same as OpenAI via `AzureOpenAIChatCompletionClient`.

The parsed result is available at `ChatCompletionResult.structured_output`.

### 3. Component Serialization System

All framework objects (agents, LLM clients, tools, workflows, orchestrators) inherit from `ComponentBase` or `Component`. This enables:

- `dump_component()` -> `ComponentModel` (JSON-serializable config)
- `load_component(config)` -> reconstructed object
- Provider string resolution for class lookup

This powers the WebUI entity registry and workflow checkpoint/resume.

### 4. Workflow Engine

The workflow engine is a separate system from the agent orchestration layer:

- **Workflow**: A DAG of typed steps connected by edges with conditions
- **WorkflowRunner**: Executes steps with parallel concurrency (semaphore-controlled), emits streaming events
- **Steps**: Typed `BaseStep[InputType, OutputType]` with Pydantic validation at boundaries
- **Context**: Shared mutable state dictionary accessible by all steps via `context.get()`/`context.set()`
- **Checkpoints**: Structure-hash validated, resumable execution with file or in-memory storage
- **Validation**: Cycle detection, unreachable step detection, type compatibility between connected steps

Key distinction: **Orchestration** = dynamic multi-agent conversation with LLM-driven routing. **Workflow** = deterministic DAG execution with typed data flow.

### 5. Evaluation Framework

The eval system supports comparing different configurations:

- **Targets**: What to evaluate (Agent, Model, Orchestrator, ClaudeCode, Callable)
- **Datasets**: Collections of Tasks with expected outputs and rubrics
- **Judges**: How to score (LLM-based, ExactMatch, FuzzyMatch, Contains, Composite)
- **Runner**: Parallel execution with middleware hooks
- **Results**: Dimensional scoring with persistence to SQLite + JSON

---

## YC Analysis Workflow (Deep Dive)

**Location**: `examples/workflows/yc_analysis/`

A 4-stage production-ready pipeline analyzing Y Combinator companies for AI agent trends.

### Pipeline Architecture

```
WorkflowConfig ──> [load_data] ──> DataResult ──> [filter_keywords] ──> FilterResult
                                                                           │
                   AnalysisResult <── [analyze_trends] <── ClassifyResult <─┘
                                                              [classify_agents]
```

### Stage Details

| Stage | Step ID | Input | Output | Purpose |
|-------|---------|-------|--------|---------|
| 1. Load Data | `load` | WorkflowConfig | DataResult | Download/cache YC company data from GitHub, clean with pandas, generate long_slug keys |
| 2. Filter Keywords | `filter` | DataResult | FilterResult | Regex-based pre-filtering for AI/agent/health keywords. Saves ~90% LLM cost by narrowing candidates |
| 3. Classify Agents | `classify` | FilterResult | ClassifyResult | LLM classification via Azure OpenAI with `AgentAnalysis` structured output. Batch processing with checkpoints, concurrent execution |
| 4. Analyze Trends | `analyze` | ClassifyResult | AnalysisResult | Statistical analysis: domain distribution, YoY trends, precision rates. Generates markdown report + JSON for Quarto |

### Key Engineering Patterns

- **Two-stage filtering**: Regex pre-filter -> LLM classification reduces cost by ~90%
- **Structured output**: `AgentAnalysis` Pydantic model eliminates hallucination in classification
- **Disk checkpoints**: `save_checkpoint()`/`load_checkpoint()` enable resumable processing at the classify step
- **Shared context**: Steps communicate via `context.get()`/`context.set()` for dataframes and intermediate results
- **Batch concurrency**: Companies processed in batches of `batch_size` with `max_concurrent_batches=3`
- **Cost tracking**: Per-company token usage and cost estimates accumulated through the pipeline

### Data Models

```python
# Structured LLM output for company classification
class AgentAnalysis(BaseModel):
    is_about_ai: bool          # Validates AI keyword match is genuine
    domain: str                # One of 12 categories (health, finance, legal, ...)
    subdomain: str             # Fine-grained category
    is_agent: bool             # Whether company builds autonomous agents
    ai_rationale: str          # Reasoning for AI classification
    agent_rationale: str       # Reasoning for agent classification
```

---

## WebUI System

**Location**: `picoagents/src/picoagents/webui/`

A FastAPI server + React frontend for interacting with PicoAgents entities.

### Architecture

```
Browser (React + Vite)
  ↕ SSE (streaming) / REST
FastAPI Server (_server.py)
  ├── EntityRegistry (_registry.py)    # Auto-discovers agents/orchestrators/workflows from Python files
  ├── ExecutionEngine (_execution.py)  # Runs entities with streaming events
  ├── SessionManager (_sessions.py)    # Tracks conversation state across requests
  ├── PicoStore (_store.py)            # Optional SQLite persistence for runs/evals
  └── EvalJobManager (_eval_jobs.py)   # Background eval job execution
```

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health check with entity count |
| GET | `/api/entities` | List all discovered entities |
| GET | `/api/entities/{id}` | Entity details |
| POST | `/api/entities/{id}/run` | Non-streaming execution |
| POST | `/api/entities/{id}/run/stream` | SSE streaming execution |
| POST | `/api/entities/add` | Import example from GitHub |
| GET/POST/DELETE | `/api/sessions/*` | Session management |
| GET | `/api/stats` | System statistics |

The WebUI supports agents, orchestrators, and workflows as first-class "entities" -- each discovered from Python files in a configured directory.

---

## Framework Comparison Examples

**Location**: `examples/frameworks/`

The same patterns implemented across multiple frameworks for educational comparison:

| Pattern | PicoAgents | LangGraph | Google ADK | Claude Agent SDK | MS Agent Framework |
|---------|-----------|-----------|------------|-----------------|-------------------|
| Basic Agent | `examples/agents/basic-agent.py` | `langgraph/agents/basic_agent.py` | `google-adk/agents/basic_agent.py` | `claude-agent-sdk/agents/basic_agent.py` | `agent-framework/agents/basic_agent.py` |
| Structured Output | `examples/agents/structured-output.py` | `langgraph/agents/structured_output.py` | `google-adk/agents/structured_output.py` | `claude-agent-sdk/agents/structured_output.py` | `agent-framework/agents/structured_output.py` |
| Memory | `examples/agents/memory.py` | `langgraph/agents/memory.py` | `google-adk/agents/memory.py` | `claude-agent-sdk/agents/memory.py` | `agent-framework/agents/memory.py` |
| Middleware | `examples/agents/middleware.py` | `langgraph/agents/middleware.py` | `google-adk/agents/middleware.py` | `claude-agent-sdk/agents/middleware.py` | `agent-framework/agents/middleware.py` |
| Sequential Workflow | `examples/workflows/sequential.py` | `langgraph/workflows/sequential.py` | `google-adk/workflows/sequential.py` | `claude-agent-sdk/workflows/sequential.py` | `agent-framework/workflows/sequential.py` |
| Orchestration | `examples/orchestration/round-robin.py` | `langgraph/orchestration/round_robin.py` | `google-adk/orchestration/parallel.py` | `claude-agent-sdk/orchestration/agents.py` | `agent-framework/orchestration/handoff.py` |

---

## Optional Dependencies

PicoAgents uses extras for optional capabilities:

| Extra | Dependencies | Enables |
|-------|-------------|---------|
| `web` | fastapi, uvicorn, sqlmodel, aiosqlite | WebUI server + persistence |
| `persist` | sqlmodel, aiosqlite | Run/eval persistence to SQLite |
| `computer-use` | playwright, pillow, beautifulsoup4 | Browser automation agent |
| `rag` | chromadb, sentence-transformers | Vector memory (ChromaDBMemory) |
| `mcp` | mcp>=1.0.0 | Model Context Protocol tool integration |
| `anthropic` | anthropic>=0.70.0 | Claude model support |
| `research` | httpx, beautifulsoup4, arxiv, youtube-transcript-api | Research tools |
| `otel` | opentelemetry-* | Distributed tracing |
| `examples` | matplotlib, yfinance, python-dotenv | Example dependencies |
| `frameworks` | langchain, langgraph, google-adk, agent-framework, claude-agent-sdk | Comparison frameworks |

---

## Test Coverage

**Location**: `picoagents/tests/` (~12k LOC)

| Test File | Coverage Area |
|-----------|--------------|
| `test_agent_basic.py` | Agent creation, execution, tool calling |
| `test_orchestrator.py` | Orchestration patterns (round-robin, AI, plan) |
| `test_tools.py` | Tool system, FunctionTool, @tool decorator |
| `test_tool_approval.py` | Approval workflows (always/never/once modes) |
| `test_model_clients.py` | LLM client abstraction |
| `test_memory_tool.py` | Memory tool operations |
| `test_middleware.py` | Middleware chain execution |
| `test_context_compaction.py` | Context window management |
| `test_hooks.py` | Start/end hook system |
| `test_eval.py` | Evaluation framework |
| `test_serialization.py` | Component config round-tripping |
| `test_mcp_integration.py` | MCP tool integration |
| `test_otel.py` | OpenTelemetry instrumentation |
| `test_cancellation_token.py` | Cooperative cancellation |
| `test_context_tools.py` | Context engineering tools |
| `test_agent_as_tool_strategies.py` | Agent-as-tool composition |
| `test_computer_use_agent.py` | Browser automation agent |
| `test_benchmarks.py` | Performance benchmarks |
| `workflow/test_workflow.py` | Workflow engine (DAG, conditions, parallel) |
| `workflow/test_checkpoint.py` | Checkpoint save/resume/validation |
| `test_workflow_progress.py` | Workflow progress events |
| `webui/test_server.py` | WebUI FastAPI endpoints |
| `webui/test_registry.py` | Entity discovery and registration |
| `webui/test_execution.py` | Streaming execution engine |
| `webui/test_sessions.py` | Session management |
| `webui/test_discovery.py` | File-based entity discovery |
| `webui/test_cli.py` | CLI entry point |
| `webui/test_workflow_integration.py` | WebUI + workflow integration |

---

## Research Data

**Location**: `research/`

| Directory | Contents |
|-----------|----------|
| `ycdata/` | YC company data (`yc_data.json`), clustering scripts (`yc_cluster.py`), agent analysis (`yc_agents.py`, `yc_agents_analysis.py`), clustered results (`yc_clustered.json`), summary (`yc_agents_summary.md`) |
| `frameworks/` | Metadata for 7 frameworks: AutoGen, CrewAI, LangGraph, LlamaIndex, OpenAI Agents, PydanticAI, Google ADK |
| `components/` | Component gallery (`gallery/base.json`), team configurations (`teams/`) |
| `news/` | AI agent news data (`news.json`) |

---

## Entry Points

| Entry Point | Command | Purpose |
|-------------|---------|---------|
| CLI | `picoagents` (or `python -m picoagents.cli`) | Launch WebUI server via uvicorn |
| WebUI | `picoagents --entities-dir ./examples` | Start web interface with entity discovery |
| YC Workflow | `python examples/workflows/yc_analysis/workflow.py` | Run YC analysis pipeline |
| YC Workflow (sample) | `python examples/workflows/yc_analysis/workflow.py --sample 100` | Test run with 100 companies |
| Tests | `pytest picoagents/tests/ -v` | Run test suite |

---

## Key Design Decisions

1. **Pydantic v2 everywhere**: All data models, configs, and API types use Pydantic for validation and serialization.
2. **Async-first**: All agent execution, LLM calls, and workflow steps are async. The workflow runner uses `asyncio.Semaphore` for concurrency control.
3. **Streaming by default**: Both `run()` and `run_stream()` exist on agents and orchestrators. The non-streaming `run()` consumes the stream internally.
4. **Type-safe workflows**: Workflow steps are generically typed `BaseStep[InputType, OutputType]` with compile-time and runtime type checking at edge boundaries.
5. **Separation of concerns**: Orchestration (dynamic, LLM-routed multi-agent conversation) is completely separate from Workflows (deterministic, typed DAG execution).
6. **Educational focus**: The entire repo is designed as a teaching resource. Examples exist for every pattern, and the framework itself is intentionally minimal (~31k LOC) to be readable.
