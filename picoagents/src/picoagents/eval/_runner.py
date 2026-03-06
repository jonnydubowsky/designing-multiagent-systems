"""
Evaluation runner - orchestrates evaluation execution.

This module provides EvalRunner which executes tasks against targets,
scores results with judges, and collects metrics.
"""

import asyncio
import copy
import shutil
import tempfile
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from .._cancellation_token import CancellationToken
from ..types import EvalScore, RunTrajectory, Task, Usage
from ._base import EvalJudge, Target
from ._config import AgentConfig
from ._dataset import Dataset
from ._middleware import RunMiddleware
from ._results import EvalResults, TaskResult
from ._targets import PicoAgentTarget


class EvalRunner:
    """Runs evaluation tasks against targets and scores the results.

    Supports two modes:
    - Simple: evaluate(target, tasks) -> List[EvalScore]
    - Full: run(dataset, targets) -> EvalResults

    Example:
        >>> runner = EvalRunner(judge=my_judge)
        >>> results = await runner.run(
        ...     dataset=my_dataset,
        ...     targets=[
        ...         PicoAgentTarget(config_baseline),
        ...         PicoAgentTarget(config_optimized),
        ...     ]
        ... )
    """

    def __init__(
        self,
        judge: EvalJudge,
        parallel_tasks: bool = False,
        parallel_targets: bool = False,
    ):
        """Initialize evaluation runner.

        Args:
            judge: Judge to score task outputs
            parallel_tasks: Run tasks in parallel (default: False for fair comparison)
            parallel_targets: Run targets in parallel (default: False)
        """
        self.judge = judge
        self.parallel_tasks = parallel_tasks
        self.parallel_targets = parallel_targets

    # --- Simple mode (backward compatible) ---

    async def evaluate(
        self,
        target: Target,
        tasks: List[Task],
        criteria: Optional[List[str]] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> List[EvalScore]:
        """Evaluate a target on multiple tasks (simple mode).

        Args:
            target: The evaluation target to test
            tasks: List of tasks to evaluate
            criteria: Optional evaluation criteria
            cancellation_token: Optional token to cancel evaluation

        Returns:
            List of evaluation scores, one per task
        """
        if self.parallel_tasks:
            eval_tasks = [
                self._evaluate_single(target, task, criteria, cancellation_token)
                for task in tasks
            ]
            return await asyncio.gather(*eval_tasks)
        else:
            scores = []
            for task in tasks:
                if cancellation_token and cancellation_token.is_cancelled():
                    break
                score = await self._evaluate_single(
                    target, task, criteria, cancellation_token
                )
                scores.append(score)
            return scores

    async def _evaluate_single(
        self,
        target: Target,
        task: Task,
        criteria: Optional[List[str]] = None,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> EvalScore:
        """Evaluate a single task (simple mode)."""
        try:
            trajectory = await target.run(task, cancellation_token)
            score = await self.judge.score(trajectory, criteria, cancellation_token)
            return score

        except Exception as e:
            failed_trajectory = RunTrajectory(
                task=task,
                messages=[],
                success=False,
                error=str(e),
                usage=Usage(
                    duration_ms=0, llm_calls=0, tokens_input=0, tokens_output=0
                ),
                metadata={"error": str(e)},
            )

            return EvalScore(
                overall=0.0,
                dimensions={dim: 0.0 for dim in (criteria or ["accuracy"])},
                reasoning={
                    dim: f"Execution failed: {str(e)}"
                    for dim in (criteria or ["accuracy"])
                },
                trajectory=failed_trajectory,
                metadata={"error": str(e), "judge": self.judge.name},
            )

    # --- Full mode (dataset + multiple targets -> EvalResults) ---

    async def run(
        self,
        dataset: Dataset,
        targets: Sequence[Target],
        task_filter: Optional[Callable[[Task], bool]] = None,
        cancellation_token: Optional[CancellationToken] = None,
        persist: bool = False,
    ) -> EvalResults:
        """Execute full evaluation of dataset against multiple targets.

        Each task runs in an isolated temp directory so targets don't
        share filesystem state.

        Args:
            dataset: Dataset of tasks to run
            targets: Targets to evaluate
            task_filter: Optional filter to select subset of tasks
            cancellation_token: For cancellation support
            persist: If True, save results to ~/.picoagents/ (DB
                index + JSON file with full eval data)

        Returns:
            EvalResults with full results matrix
        """
        tasks = list(dataset.tasks)
        if task_filter:
            tasks = [t for t in tasks if task_filter(t)]

        results = EvalResults(
            dataset_name=dataset.name,
            dataset_version=dataset.version,
        )

        if self.parallel_targets:
            target_coros = [
                self._run_target(target, tasks, dataset, cancellation_token)
                for target in targets
            ]
            target_results = await asyncio.gather(*target_coros, return_exceptions=True)

            for target, target_result in zip(targets, target_results):
                if isinstance(target_result, Exception):
                    continue
                for task_result in target_result:
                    results.add_result(task_result)
        else:
            for target in targets:
                if cancellation_token and cancellation_token.is_cancelled():
                    break

                task_results = await self._run_target(
                    target, tasks, dataset, cancellation_token
                )
                for task_result in task_results:
                    results.add_result(task_result)

        if persist:
            try:
                # Save JSON file via existing method
                file_path = results.save()

                # Index in DB
                from ..store import get_default_store

                store = get_default_store()
                await store.save_eval_run_from_results(
                    results, file_path=file_path
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    f"Failed to persist eval results: {e}"
                )

        return results

    async def run_configs(
        self,
        dataset: Dataset,
        configs: List[AgentConfig],
        task_filter: Optional[Callable[[Task], bool]] = None,
        cancellation_token: Optional[CancellationToken] = None,
        persist: bool = False,
    ) -> EvalResults:
        """Convenience method to run with AgentConfigs directly.

        Args:
            dataset: Dataset of tasks
            configs: Agent configurations to compare
            task_filter: Optional task filter
            cancellation_token: For cancellation
            persist: If True, save results to ~/.picoagents/

        Returns:
            EvalResults
        """
        targets = [PicoAgentTarget(config) for config in configs]
        return await self.run(
            dataset, targets, task_filter, cancellation_token,
            persist=persist,
        )

    async def _run_target(
        self,
        target: Target,
        tasks: List[Task],
        dataset: Dataset,
        cancellation_token: Optional[CancellationToken],
    ) -> List[TaskResult]:
        """Run all tasks for a single target."""
        results = []

        if self.parallel_tasks:
            task_coroutines = [
                self._run_single_task(target, task, dataset, cancellation_token)
                for task in tasks
            ]
            results = await asyncio.gather(*task_coroutines, return_exceptions=True)
            results = [r for r in results if isinstance(r, TaskResult)]
        else:
            for task in tasks:
                if cancellation_token and cancellation_token.is_cancelled():
                    break

                result = await self._run_single_task(
                    target, task, dataset, cancellation_token
                )
                results.append(result)

        return results

    async def _run_single_task(
        self,
        target: Target,
        task: Task,
        dataset: Dataset,
        cancellation_token: Optional[CancellationToken],
    ) -> TaskResult:
        """Run a single task and score it.

        When a PicoAgentTarget has no explicit workspace, an isolated temp
        directory is created per task so targets don't share filesystem
        state.  When the config already specifies a workspace, it is
        respected as-is (no temp dir, no mutation).
        """
        middleware = RunMiddleware()
        task_id = task.id or task.name

        # Only create a temp workspace when the target has none set
        needs_temp = (
            isinstance(target, PicoAgentTarget)
            and target.config.workspace is None
        )
        task_workspace = None
        if needs_temp:
            task_workspace = Path(tempfile.mkdtemp(
                prefix=f"eval_{target.name}_{task_id}_"
            ))

        try:
            if isinstance(target, PicoAgentTarget):
                if needs_temp:
                    # Copy config with temp workspace (parallel-safe,
                    # never mutates the original target)
                    task_config = copy.copy(target.config)
                    task_config.workspace = str(task_workspace)
                    task_target = PicoAgentTarget(
                        task_config,
                        middlewares=target.middlewares,
                    )
                else:
                    task_target = target

                trajectory = await task_target.run(
                    task,
                    cancellation_token=cancellation_token,
                    middlewares=[middleware],
                )
            else:
                trajectory = await target.run(
                    task,
                    cancellation_token=cancellation_token,
                )
        finally:
            if task_workspace is not None:
                shutil.rmtree(task_workspace, ignore_errors=True)

        # Score with judge
        criteria = task.eval_criteria or dataset.default_eval_criteria
        score = await self._score_trajectory(trajectory, criteria, cancellation_token)

        # Get metrics from middleware
        metrics = middleware.get_metrics()

        # Build task result
        return TaskResult(
            task_id=task_id,
            target_name=target.name,
            trajectory=trajectory,
            score=score,
            files_read=metrics.get("file_reads", {}),
            unique_files=metrics.get("unique_files", 0),
            duplicate_reads=metrics.get("duplicate_reads", 0),
            compaction_events=metrics.get("compaction_events", 0),
            tokens_saved=metrics.get("tokens_saved", 0),
            metrics=metrics,
        )

    async def _score_trajectory(
        self,
        trajectory: RunTrajectory,
        criteria: List[str],
        cancellation_token: Optional[CancellationToken],
    ) -> EvalScore:
        """Score trajectory with judge."""
        try:
            return await self.judge.score(
                trajectory,
                criteria=criteria,
                cancellation_token=cancellation_token,
            )
        except Exception as e:
            return EvalScore(
                overall=0.0,
                dimensions={c: 0.0 for c in criteria},
                reasoning={c: f"Judge error: {str(e)}" for c in criteria},
                trajectory=trajectory,
                metadata={"judge_error": str(e)},
            )
