# Context Compaction Strategies

Demonstrates how context compaction strategies affect agent performance on a multi-step task.

## Running

Open `compaction_strategies.ipynb` in Jupyter and run all cells. Requires:

- Azure OpenAI API access (set `AZURE_OPENAI_ENDPOINT` in `picoagents/.env`)
- PicoAgents installed: `pip install -e ".[all]"` from `picoagents/`

Each run takes 1-5 minutes (4 agent runs with real API calls).

## What It Shows

The notebook runs an exhaustive code review task with four compaction configurations:

| Run | Strategy | Budget | Result |
|-----|----------|--------|--------|
| NoCompaction | None | — | Unbounded growth, expensive |
| HeadTail 8k | HeadTail | 8,000 | Thrashing — reads files, drops them, re-reads |
| HeadTail 50k | HeadTail | 50,000 | Right-sized — good quality at low cost |
| SlidingWindow 50k | SlidingWindow | 50,000 | Loses task context, incomplete |

Key outputs:
- **Sawtooth chart** — real API token counts per LLM call showing context growth and compaction
- **Trace analysis** — tool call batching per strategy (reveals thrashing vs methodical work)
- **Cost vs quality scatter** — cost and LLM-as-judge quality scores
- **Judge reasoning** — per-criterion evaluation explaining *why* each strategy scored as it did

Results are persisted via `EvalResults` — re-run visualizations without re-running agents.
