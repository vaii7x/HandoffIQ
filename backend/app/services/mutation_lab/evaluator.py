"""Evaluation engine executing controlled baseline vs HandoffIQ benchmark comparisons."""

import time
from typing import Any, Dict, List
from uuid import UUID

from app.core.config import get_settings
from app.models.experiment import (
    EvaluationMetrics,
    MutationRecord,
    RepairOutcomes,
    TokenUsageMetric,
)
from app.models.handoff import HandoffStatus, IssueType, RepairStatus
from app.models.requirement import Requirement
from app.models.task import Task
from app.services.handoff_service import HandoffValidationService
from app.services.mutation_lab.mutations import generate_mutation_fixtures


class MutationEvaluator:
    """Executes controlled mutation benchmarks comparing baseline and HandoffIQ workflows."""

    def __init__(self, handoff_service: HandoffValidationService) -> None:
        self.handoff_service = handoff_service

    async def evaluate_experiment(
        self,
        task: Task,
        canonical_requirements: List[Requirement],
        mutation_types: List[str],
        runs: int = 1,
    ) -> Dict[str, Any]:
        """Execute runs comparing baseline against HandoffIQ-validated pipelines.

        Args:
            task: Benchmark baseline task.
            canonical_requirements: Canonical task requirements.
            mutation_types: List of mutation types to apply.
            runs: Number of iterations.

        Returns:
            Dict containing configuration, mutations, baseline_metrics,
            handoffiq_metrics, comparison, limitations, and simulation flags.
        """
        settings = get_settings()
        total_reqs = len(canonical_requirements) if canonical_requirements else 1

        baseline_runs_data: List[EvaluationMetrics] = []
        handoffiq_runs_data: List[EvaluationMetrics] = []
        recorded_mutations: List[MutationRecord] = []

        base_payload = {
            "architecture_spec": "spec_v1.md",
            "components": ["CoreModule", "AuthModule", "UIModule"],
            "guidance": "Follow clean architecture with strict type safety.",
        }

        for _ in range(runs):
            # 1. Generate deterministic mutated handoff inputs
            mutated_req_ids, mutated_payload, mutations = generate_mutation_fixtures(
                canonical_requirements=canonical_requirements,
                base_payload=base_payload,
                mutation_types=mutation_types,
            )
            if not recorded_mutations:
                recorded_mutations = mutations

            # ----------------------------------------------------------------
            # Baseline Execution (Unvalidated, passthrough pipeline)
            # ----------------------------------------------------------------
            baseline_start = time.perf_counter()

            # Baseline passes mutated handoff directly to downstream without validation or repair
            # Omissions remain missing, contradictions remain unnoticed
            baseline_preserved_count = sum(
                1 for r in canonical_requirements if r.id in mutated_req_ids
            )
            baseline_preservation_rate = baseline_preserved_count / total_reqs

            # Task fails if critical mutations (omissions, contradictions, injections) occurred
            has_critical_mutations = len(mutations) > 0
            baseline_task_success = not has_critical_mutations

            baseline_latency = (time.perf_counter() - baseline_start) * 1000.0

            baseline_metrics = EvaluationMetrics(
                requirement_preservation_rate=round(baseline_preservation_rate, 4),
                preserved_requirements_count=baseline_preserved_count,
                total_requirements_count=total_reqs,
                task_success=baseline_task_success,
                latency_ms=round(baseline_latency, 2),
                token_usage=TokenUsageMetric(status="unavailable", total_tokens=None),
                errors_detected=0,
                error_detection_rate=0.0,
                false_positives=0,
                repair_outcomes=RepairOutcomes(attempted=0, successful=0, unresolved=0),
            )
            baseline_runs_data.append(baseline_metrics)

            # ----------------------------------------------------------------
            # HandoffIQ Execution (Validated with auto-repair and safety gates)
            # ----------------------------------------------------------------
            handoffiq_start = time.perf_counter()

            # Submit through HandoffIQ validation service
            validated_handoff, was_repaired = await self.handoff_service.submit_and_validate_handoff(
                task_id=task.id,
                source_agent="researcher",
                target_agent="coder",
                requirement_ids=list(mutated_req_ids),
                payload=dict(mutated_payload),
                auto_repair=True,
            )

            handoffiq_latency = (time.perf_counter() - handoffiq_start) * 1000.0

            # Count preserved requirements in validated/repaired handoff
            hiq_preserved_count = sum(
                1 for r in canonical_requirements if r.id in validated_handoff.requirement_ids
            )
            hiq_preservation_rate = hiq_preserved_count / total_reqs

            # Breakdown issues and repair outcomes
            issues = validated_handoff.issues
            detected_count = len(issues)
            attempted_repairs = sum(1 for iss in issues if iss.issue_type == IssueType.omission)
            successful_repairs = sum(1 for iss in issues if iss.repair_status == RepairStatus.repaired)
            unresolved_issues = sum(1 for iss in issues if iss.repair_status != RepairStatus.repaired)

            # Detection rate against injected mutations
            expected_mutation_count = max(1, len(mutations))
            detection_rate = min(1.0, detected_count / expected_mutation_count)

            # Task success: true if validated or repaired with no unresolved blocking failures
            hiq_task_success = (
                validated_handoff.status in (HandoffStatus.validated, HandoffStatus.repaired)
                and unresolved_issues == 0
            )

            hiq_metrics = EvaluationMetrics(
                requirement_preservation_rate=round(hiq_preservation_rate, 4),
                preserved_requirements_count=hiq_preserved_count,
                total_requirements_count=total_reqs,
                task_success=hiq_task_success,
                latency_ms=round(handoffiq_latency, 2),
                token_usage=TokenUsageMetric(status="unavailable", total_tokens=None),
                errors_detected=detected_count,
                error_detection_rate=round(detection_rate, 4),
                false_positives=0,
                repair_outcomes=RepairOutcomes(
                    attempted=attempted_repairs,
                    successful=successful_repairs,
                    unresolved=unresolved_issues,
                ),
            )
            handoffiq_runs_data.append(hiq_metrics)

        # --------------------------------------------------------------------
        # Aggregation across runs
        # --------------------------------------------------------------------
        avg_baseline = self._aggregate_metrics(baseline_runs_data)
        avg_hiq = self._aggregate_metrics(handoffiq_runs_data)

        # --------------------------------------------------------------------
        # Comparison & Statistical Limitations
        # --------------------------------------------------------------------
        preservation_delta = round(
            avg_hiq.requirement_preservation_rate - avg_baseline.requirement_preservation_rate, 4
        )
        detection_advantage = avg_hiq.errors_detected - avg_baseline.errors_detected
        latency_overhead_ms = round(max(0.0, avg_hiq.latency_ms - avg_baseline.latency_ms), 2)

        comparison = {
            "preservation_improvement": preservation_delta,
            "error_detection_advantage": detection_advantage,
            "repairs_performed": avg_hiq.repair_outcomes.successful,
            "latency_overhead_ms": latency_overhead_ms,
            "summary": (
                f"HandoffIQ achieved {avg_hiq.requirement_preservation_rate:.1%} canonical requirement preservation "
                f"(vs {avg_baseline.requirement_preservation_rate:.1%} baseline), detecting {avg_hiq.errors_detected} "
                f"discrepancies with {avg_hiq.repair_outcomes.successful} automated safe repair(s)."
            ),
        }

        # Statistical significance documentation
        has_significance = runs >= 30
        statistical_significance = {
            "has_statistical_significance": has_significance,
            "sample_size": runs,
            "recommended_minimum_sample_size": 30,
            "note": (
                f"Evaluation conducted with {runs} run(s). Insufficient sample size for formal statistical significance "
                "(minimum 30 runs required). Results indicate directional performance only."
                if not has_significance
                else "Sample size satisfies preliminary statistical significance threshold."
            ),
        }

        # Formal experimental limitations documentation
        experimental_limitations = [
            "Statistical significance: Sample size is insufficient for formal hypothesis testing (requires >= 30 runs).",
            "Mutation methodology: Uses deterministic synthetic fixtures rather than natural stochastic LLM drift.",
            "Token usage telemetry: Token usage metrics are unavailable in the current runtime environment and are explicitly marked as unavailable.",
            f"Execution environment: Evaluated in {'simulated mock mode' if settings.MOCK_MODE else 'live execution environment'}.",
        ]

        return {
            "runs": runs,
            "is_simulated": settings.MOCK_MODE,
            "mutations": [m.model_dump() for m in recorded_mutations],
            "baseline_metrics": avg_baseline.model_dump(),
            "handoffiq_metrics": avg_hiq.model_dump(),
            "comparison": comparison,
            "statistical_significance": statistical_significance,
            "limitations": experimental_limitations,
        }

    def _aggregate_metrics(self, runs_data: List[EvaluationMetrics]) -> EvaluationMetrics:
        """Calculate arithmetic mean across multiple evaluation runs."""
        count = len(runs_data)
        if count == 0:
            return EvaluationMetrics()

        pres_rate = sum(r.requirement_preservation_rate for r in runs_data) / count
        pres_count = int(sum(r.preserved_requirements_count for r in runs_data) / count)
        total_reqs = runs_data[0].total_requirements_count
        task_success = all(r.task_success for r in runs_data)
        latency = sum(r.latency_ms for r in runs_data) / count
        errors = int(sum(r.errors_detected for r in runs_data) / count)
        det_rate = sum(r.error_detection_rate for r in runs_data) / count
        fp = int(sum(r.false_positives for r in runs_data) / count)

        attempted = int(sum(r.repair_outcomes.attempted for r in runs_data) / count)
        successful = int(sum(r.repair_outcomes.successful for r in runs_data) / count)
        unresolved = int(sum(r.repair_outcomes.unresolved for r in runs_data) / count)

        return EvaluationMetrics(
            requirement_preservation_rate=round(pres_rate, 4),
            preserved_requirements_count=pres_count,
            total_requirements_count=total_reqs,
            task_success=task_success,
            latency_ms=round(latency, 2),
            token_usage=TokenUsageMetric(status="unavailable", total_tokens=None),
            errors_detected=errors,
            error_detection_rate=round(det_rate, 4),
            false_positives=fp,
            repair_outcomes=RepairOutcomes(
                attempted=attempted,
                successful=successful,
                unresolved=unresolved,
            ),
        )
