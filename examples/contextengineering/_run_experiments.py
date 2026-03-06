"""Run compaction experiments and save results via EvalResults.

This script runs the 4 agent configurations and persists results
so the notebook can load from cache without re-running.

Usage:
    python examples/contextengineering/_run_experiments.py
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncGenerator, List, Union

# Add picoagents to path
sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "..", "picoagents", "src"
))

from dotenv import load_dotenv

from picoagents import Agent
from picoagents._middleware import BaseMiddleware, MiddlewareContext
from picoagents.compaction import (
    HeadTailCompaction,
    NoCompaction,
    SlidingWindowCompaction,
)
from picoagents.eval import LLMEvalJudge
from picoagents.eval._results import EvalResults, TaskResult
from picoagents.llm import AzureOpenAIChatCompletionClient
from picoagents.messages import Message, ToolMessage
from picoagents.types import EvalScore, RunTrajectory, Task as EvalTask, Usage

load_dotenv(os.path.join(
    os.path.dirname(__file__), "..", "..", "picoagents", ".env"
))


@dataclass
class TokenSnapshot:
    iteration: int
    messages_in: int
    tokens_input: int
    tokens_output: int


class TokenLoggerMiddleware(BaseMiddleware):
    def __init__(self):
        self.snapshots: List[TokenSnapshot] = []
        self._call_count = 0

    async def process_request(self, ctx: MiddlewareContext) -> AsyncGenerator[Union[MiddlewareContext, Any], None]:
        if ctx.operation == "model_call":
            self._call_count += 1
            ctx.metadata["_iter"] = self._call_count
            ctx.metadata["_msgs"] = len(ctx.data) if isinstance(ctx.data, list) else 0
        yield ctx

    async def process_response(self, ctx: MiddlewareContext, result: Any) -> AsyncGenerator[Union[Any, Any], None]:
        if ctx.operation == "model_call" and hasattr(result, "usage"):
            self.snapshots.append(TokenSnapshot(
                iteration=ctx.metadata.get("_iter", 0),
                messages_in=ctx.metadata.get("_msgs", 0),
                tokens_input=result.usage.tokens_input,
                tokens_output=result.usage.tokens_output,
            ))
        yield result

    async def process_error(self, ctx: MiddlewareContext, error: Exception) -> AsyncGenerator[Any, None]:
        if False:
            yield
        raise error


WORKSPACE = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "picoagents", "src", "picoagents"
))


def read_file(path: str) -> str:
    """Read a file from picoagents source.
    Args:
        path: Relative path within picoagents/src/picoagents/
    Returns:
        File contents as string.
    """
    full = os.path.normpath(os.path.join(WORKSPACE, path))
    if not full.startswith(WORKSPACE):
        return f"Error: blocked '{path}'"
    try:
        with open(full) as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: not found: {path}"


def list_directory(path: str = ".") -> str:
    """List files in a picoagents source directory.
    Args:
        path: Relative directory path
    Returns:
        Newline-separated file/folder names.
    """
    full = os.path.normpath(os.path.join(WORKSPACE, path))
    if not full.startswith(WORKSPACE):
        return f"Error: blocked '{path}'"
    try:
        entries = sorted(os.listdir(full))
        result = []
        for e in entries:
            if e.startswith("__pycache__"):
                continue
            fp = os.path.join(full, e)
            suffix = "/" if os.path.isdir(fp) else ""
            result.append(f"{e}{suffix}")
        return "\n".join(result)
    except FileNotFoundError:
        return f"Error: not found: {path}"


TASK = """Perform an exhaustive code review of the picoagents library.

For EVERY Python file in the source directory and its
subdirectories (agents/, workflow/, orchestration/,
tools/, llm/, memory/, eval/, termination/):

1. List each subdirectory to discover all files
2. Read EVERY .py file completely
3. For each file, document:
   - All classes with their purpose and methods
   - All functions with their signatures
   - Any code quality issues

After reviewing ALL files, produce:
- A summary table of all classes and relationships
- Top 10 code quality issues across the codebase
- Architectural recommendations

Be thorough. Read every single file. Do not skip any.
"""


async def main():
    client = AzureOpenAIChatCompletionClient(
        model="gpt-4.1-mini",
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    )

    results_path = Path(os.path.dirname(__file__)) / "compaction_eval_results.json"

    if results_path.exists():
        print(f"Results already exist at {results_path}")
        print("Delete the file to re-run experiments.")
        return

    run_configs = [
        ("NoCompaction", NoCompaction()),
        ("HeadTail 8k", HeadTailCompaction(token_budget=8_000, head_ratio=0.2)),
        ("HeadTail 50k", HeadTailCompaction(token_budget=50_000, head_ratio=0.2)),
        ("SlidingWindow 50k", SlidingWindowCompaction(token_budget=50_000)),
    ]

    results = []
    for name, strat in run_configs:
        print(f"\n{'='*50}")
        print(f"Running: {name}...")
        print(f"{'='*50}")

        logger = TokenLoggerMiddleware()
        agent = Agent(
            name="reviewer", description="Code review agent",
            instructions="You are a senior software engineer doing a code review. "
                         "Use the tools to read files and list directories. Be thorough.",
            model_client=client,
            tools=[read_file, list_directory],
            compaction=strat,
            max_iterations=20,
            middlewares=[logger],
        )

        t0 = time.time()
        response = await agent.run(TASK)
        duration = time.time() - t0

        tool_msgs = [m for m in response.messages if isinstance(m, ToolMessage)]
        print(f"  {len(logger.snapshots)} LLM calls | {len(tool_msgs)} tool calls | "
              f"{response.usage.tokens_input:,} input tokens | {duration:.0f}s")

        results.append({
            "name": name,
            "messages": list(response.messages),
            "input_tokens": response.usage.tokens_input if response.usage else 0,
            "output_tokens": response.usage.tokens_output if response.usage else 0,
            "tool_calls": len(tool_msgs),
            "duration_s": duration,
            "compaction_count": getattr(strat, "compaction_count", 0),
            "tokens_saved": getattr(strat, "total_tokens_saved", 0),
            "logger": logger,
        })

    # Evaluate with LLM judge
    print(f"\n{'='*50}")
    print("Evaluating with LLM judge...")
    print(f"{'='*50}")

    eval_task = EvalTask(
        name="Exhaustive Code Review", input=TASK, expected_output=None,
        eval_criteria=["completeness", "accuracy", "code_reference_quality"],
        rubric={
            "completeness": "10=all modules/files. 5=covers some. 0=superficial.",
            "accuracy": "10=all correct. 5=mostly correct. 0=errors.",
            "code_reference_quality": "10=specific files/classes/methods. 5=vague. 0=none.",
        },
    )

    judge = LLMEvalJudge(
        client=client, name="gpt-4.1-mini-judge",
        default_criteria=["completeness", "accuracy", "code_reference_quality"],
        custom_instructions=(
            "You are evaluating a code review. Score:\n"
            "- completeness: all modules covered?\n"
            "- accuracy: claims correct?\n"
            "- code_reference_quality: specific files/classes/methods cited?"
        ),
    )

    eval_results = EvalResults(dataset_name="compaction_strategies")

    for r in results:
        trajectory = RunTrajectory(
            task=eval_task, messages=r["messages"], success=True,
            usage=Usage(
                duration_ms=int(r["duration_s"] * 1000),
                llm_calls=len(r["logger"].snapshots),
                tokens_input=r["input_tokens"],
                tokens_output=r["output_tokens"],
                tool_calls=r["tool_calls"],
            ),
        )
        score = await judge.score(trajectory)
        print(f"  {r['name']}: {score.overall:.0f}/10")

        task_result = TaskResult(
            task_id="exhaustive_review", target_name=r["name"],
            trajectory=trajectory, score=score,
            compaction_events=r["compaction_count"],
            tokens_saved=r["tokens_saved"],
            metrics={"snapshots": [
                {"iteration": s.iteration, "messages_in": s.messages_in,
                 "tokens_input": s.tokens_input, "tokens_output": s.tokens_output}
                for s in r["logger"].snapshots
            ]},
        )
        eval_results.add_result(task_result)

    eval_results.save(results_path)
    print(f"\nSaved to {results_path}")


if __name__ == "__main__":
    asyncio.run(main())
