---
created: 2026-03-22
modified: 2026-03-22
type: strategy_doc
doc_type: framework
status: draft
origin: claude-code-terminal
project: yc-ai-agent-vertical
organization: [sense-collective, shur-agency]
tags: [sbpi, ontology, ai-agents, stack-ranking, competitive-intelligence]
---

# AI Agent Vertical — SBPI Dimension Design

> Parallel scoring methodology for AI agent companies, structurally identical
> to the micro-drama SBPI system. Designed for cross-vertical weekly analysis.

---

## The Five Scoring Dimensions

| Dimension | Code | Weight | What It Measures |
|-----------|------|--------|-----------------|
| Model Capability | mc | 20% | Quality, performance, and differentiation of core AI/ML technology |
| Market Traction | mt | 25% | Revenue, user base, growth rate, and real-world deployment evidence |
| Platform Ecosystem | pe | 20% | Developer tools, integrations, API surface, partner network |
| Autonomy Depth | ad | 20% | Degree of genuine agent autonomy — acts independently vs. generates output |
| Capital & Defensibility | cd | 15% | Funding, IP moats, regulatory positioning, competitive barriers |

### Weight Rationale

**Market Traction (25%)** carries the highest weight because in AI agents, the gap between demo and production deployment is enormous. Many companies have impressive models but no customers. Traction is the hardest thing to fake and the strongest predictor of survival.

**Model Capability (20%)** and **Autonomy Depth (20%)** share equal weight. Capability measures the engine; autonomy measures whether the engine actually drives. A company can have strong LLM capabilities but no agent architecture (just a chatbot).

**Platform Ecosystem (20%)** captures network effects. Agent companies that build platforms (tool marketplaces, integration layers, orchestration frameworks) create moats that pure-capability players cannot replicate.

**Capital & Defensibility (15%)** carries the lowest weight because funding alone does not predict success in AI — the market moves too fast. But defensibility matters: patents, proprietary data, regulatory positioning, and switching costs.

---

## Dimension Definitions

### 1. Model Capability (mc, 20%)

**What it measures**: The quality, performance, and technical differentiation of the company's core AI/ML technology stack.

**Scoring signals**:
- Foundation model quality (own model vs. API wrapper)
- Benchmark performance on relevant tasks
- Structured output reliability (JSON/schema adherence)
- Multimodal capabilities (text, code, vision, audio)
- Fine-tuning or adaptation methodology
- Latency and cost efficiency at scale
- Open-source contributions or research publications

**Score guide**:
- 90-100: Frontier model provider or differentiated fine-tuned model with published benchmarks
- 70-89: Strong proprietary model or expert fine-tuning of foundation models
- 50-69: Competent API wrapper with meaningful prompt engineering or RAG
- 30-49: Basic API integration, no model differentiation
- 0-29: No meaningful AI/ML technology (keyword-matching company)

### 2. Market Traction (mt, 25%)

**What it measures**: Real-world deployment evidence — revenue, users, enterprise contracts, growth trajectory.

**Scoring signals**:
- Annual recurring revenue (ARR) or GMV
- User base size and growth rate
- Enterprise customer count and logos
- Net revenue retention (NRR)
- Product-market fit evidence (organic growth, word-of-mouth)
- YC batch year (proxy for maturity)
- Public launch vs. stealth

**Score guide**:
- 90-100: >$10M ARR or >1M users, strong growth trajectory
- 70-89: $1M-10M ARR or 100K-1M users, proven PMF
- 50-69: <$1M ARR but growing, early enterprise customers
- 30-49: Pre-revenue but launched product with users
- 0-29: Pre-launch or pivot stage

### 3. Platform Ecosystem (pe, 20%)

**What it measures**: The breadth and depth of the company's platform layer — integrations, APIs, developer tools, partner network.

**Scoring signals**:
- API surface area and documentation quality
- Number of third-party integrations
- Developer community size (GitHub stars, contributors)
- Partner/marketplace ecosystem
- MCP server availability or tool registry
- SDK availability across languages
- Self-serve vs. enterprise-only access

**Score guide**:
- 90-100: Open platform with thriving ecosystem (1000+ integrations, active marketplace)
- 70-89: Strong API platform with 100+ integrations, growing community
- 50-69: API available, 10-100 integrations, emerging developer adoption
- 30-49: Limited API, few integrations, mostly closed system
- 0-29: No platform layer, single-purpose tool

### 4. Autonomy Depth (ad, 20%)

**What it measures**: The degree to which the product operates as a genuine autonomous agent vs. a generation tool requiring human-in-the-loop.

**Scoring signals**:
- Can execute multi-step tasks without human intervention
- Maintains persistent memory across sessions
- Makes decisions and takes real-world actions (API calls, bookings, code execution)
- Handles errors and adapts without human prompting
- Multi-agent orchestration capability
- Tool use sophistication (browsing, code, file systems, external APIs)
- Planning and reasoning evidence

**Score guide**:
- 90-100: Fully autonomous agent performing real-world actions with minimal oversight
- 70-89: Semi-autonomous with meaningful independent action capability
- 50-69: Assisted workflow — AI augments human decisions but doesn't act independently
- 30-49: Generation tool with human-in-the-loop for all actions
- 0-29: Pure generation (text/image output) with no action capability

### 5. Capital & Defensibility (cd, 15%)

**What it measures**: Financial resources, intellectual property, regulatory positioning, and competitive moats.

**Scoring signals**:
- Total funding raised and recent round details
- Patent portfolio (AI-specific patents)
- Proprietary training data or data moats
- Regulatory certifications (SOC 2, HIPAA, FedRAMP)
- Switching costs / lock-in dynamics
- Unique partnerships or exclusive agreements
- Team pedigree (ex-FAANG AI leads, research lab alumni)

**Score guide**:
- 90-100: >$100M raised, strong IP portfolio, significant data moats
- 70-89: $10M-100M raised, some IP protection, growing data advantage
- 50-69: $1M-10M raised, team pedigree, limited but emerging moats
- 30-49: <$1M raised (seed/YC funding), no significant moats yet
- 0-29: Unfunded or bootstrapped with no defensibility

---

## Tier Definitions

| Tier | Range | Label | Description |
|------|-------|-------|-------------|
| T1 | 85-100 | Dominant | Market leaders with clear competitive advantages across all dimensions |
| T2 | 70-84 | Strong | Established players with proven traction and defensible positions |
| T3 | 55-69 | Emerging | Growing companies with promising technology and early traction |
| T4 | 40-54 | Niche | Specialized players with limited market presence or narrow focus |
| T5 | 0-39 | Limited | Early stage, pre-product, or declining companies |

---

## Composite Score Formula

```
composite = 0.20 × mc + 0.25 × mt + 0.20 × pe + 0.20 × ad + 0.15 × cd
```

---

## Domain Sub-Categories (from YC Classification)

The YC analysis workflow classifies AI agent companies into domains. These map to SBPI sub-vertical segmentation:

| Domain | AI Agent Focus | Example Companies |
|--------|---------------|-------------------|
| productivity | Workflow automation, scheduling, task management | Calendar agents, email agents |
| software | Developer tools, code generation, DevOps agents | Code assistants, CI/CD agents |
| health | Clinical decision support, patient engagement | Medical agents, diagnostic AI |
| finance | Trading, compliance, financial analysis | Robo-advisors, audit agents |
| legal | Contract analysis, compliance monitoring | Legal research agents |
| education | Tutoring, curriculum design | AI tutors, learning agents |
| media | Content creation, editing, distribution | Creative agents |
| e_commerce | Shopping assistants, inventory management | Commerce agents |
| government | Civic tech, public service automation | Government AI agents |
| other | Cross-domain or novel applications | General-purpose agents |

---

## Data Flow: YC Analysis → SBPI Semantic Layer

```
YC Company Scraper (GitHub)
    ↓
PicoAgents Workflow (classify_agents step)
    ↓ Anthropic Claude structured output
    ↓ AgentAnalysis Pydantic model
    ↓
classifications.json (checkpoint)
    ↓
ai_agent_to_rdf.py (new ETL script)
    ↓ Maps domain → dimension initial scores
    ↓ Maps is_agent → autonomy signals
    ↓ Maps YC batch year → maturity proxy
    ↓
ai-agent-sbpi.ttl (OWL ontology, parallel to sbpi.ttl)
    ↓
Oxigraph SPARQL Store
    ↓
SPARQL Query Library (parallel to micro-drama queries)
    ↓
Weekly Insight Digests + Stack Rankings
```

---

## Initial Scoring Heuristics

For the first pass (automated from YC classification data), dimension scores will be estimated using heuristics:

### Model Capability (mc)
- `is_about_ai == true` → base 40
- `domain == "software"` → +10 (likely building tools)
- Description mentions "LLM", "foundation model", "fine-tuned" → +15
- Description mentions "GPT wrapper", "API" without model work → -10

### Market Traction (mt)
- YC batch year recent (2024-2025) → base 30 (early stage)
- YC batch year older (2020-2022) → base 50 (more mature)
- Description mentions "enterprise", "Fortune 500" → +20
- Description mentions "beta", "waitlist" → -10

### Platform Ecosystem (pe)
- Description mentions "API", "SDK", "platform" → base 50
- Description mentions "open source" → +15
- Description mentions "integrations", "marketplace" → +10
- Single product/feature focus → base 30

### Autonomy Depth (ad)
- `is_agent == true` → base 60
- `is_agent == false` → base 25
- Description mentions "autonomous", "independently" → +15
- Description mentions "multi-agent", "orchestration" → +15
- Description mentions "assistant", "copilot" → base 45
- Description mentions "chatbot" → base 30

### Capital & Defensibility (cd)
- YC-backed → base 40 (significant signal)
- Description mentions "patent", "proprietary data" → +20
- Description mentions "regulated" domain → +10
- Recent batch (less time to build moats) → -5

---

## Weekly Analysis Cadence

| Day | Activity |
|-----|----------|
| Monday | Refresh YC data (24h cache TTL), run classification on new companies |
| Tuesday | Score dimension updates from market signals (funding, launches, partnerships) |
| Wednesday | Run SPARQL insight queries, generate weekly movers report |
| Thursday | Cross-vertical comparison (micro-drama + AI agents) |
| Friday | Publish editorial digest, update stack rankings |

---

## Cross-Vertical Integration Points

Both verticals share:
1. **Same tier structure** (Dominant/Strong/Emerging/Niche/Limited)
2. **Same composite formula pattern** (weighted sum of 5 dimensions)
3. **Same SPARQL query patterns** (movers, transitions, anomalies, predictions)
4. **Same attestation/confidence framework** (0.0-1.0, source types)
5. **Same prediction engine** (momentum, divergence, boundary proximity, stagnation)

Differences:
- **Dimension names and weights** (content-specific vs. agent-specific)
- **Company roster** (22 micro-drama vs. 200+ AI agent companies)
- **Data sources** (app store metrics vs. GitHub/API metrics)
- **Scoring heuristics** (content metrics vs. technology metrics)

The editorial site template transfers directly — same 7-tab structure with dimension-specific content.
