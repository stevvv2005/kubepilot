from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class WorkloadCostSnapshot:
    namespace: str
    workload_name: str
    workload_type: str

    cpu_request_cores: float
    cpu_usage_cores: float

    memory_request_mib: float
    memory_usage_mib: float

    monthly_cost_usd: float


@dataclass(frozen=True)
class FinOpsAnalysis:
    namespace: str
    workload_name: str
    workload_type: str

    cpu_utilization_pct: Optional[float]
    memory_utilization_pct: Optional[float]

    monthly_cost_usd: float

    waste_detected: bool
    recommendation: str

    estimated_monthly_savings_usd: Optional[float]
    confidence: str

    requires_human_approval: bool = True
    auto_apply: bool = False


def _utilization_percent(
    usage: float,
    request: float,
) -> Optional[float]:
    if request <= 0:
        return None

    return round(
        (usage / request) * 100,
        2,
    )


def analyze_workload_cost(
    snapshot: WorkloadCostSnapshot,
) -> FinOpsAnalysis:
    """
    Analyze one workload for obvious resource waste.

    This first version is intentionally conservative.

    It performs no Kubernetes, Git, or cloud write.
    """

    numeric_values = (
        snapshot.cpu_request_cores,
        snapshot.cpu_usage_cores,
        snapshot.memory_request_mib,
        snapshot.memory_usage_mib,
        snapshot.monthly_cost_usd,
    )

    if any(value < 0 for value in numeric_values):
        raise ValueError(
            "Resource and cost values cannot be negative."
        )

    cpu_utilization_pct = _utilization_percent(
        usage=snapshot.cpu_usage_cores,
        request=snapshot.cpu_request_cores,
    )

    memory_utilization_pct = _utilization_percent(
        usage=snapshot.memory_usage_mib,
        request=snapshot.memory_request_mib,
    )

    has_cpu_signal = cpu_utilization_pct is not None
    has_memory_signal = memory_utilization_pct is not None

    clearly_underutilized = (
        has_cpu_signal
        and has_memory_signal
        and cpu_utilization_pct < 30
        and memory_utilization_pct < 30
    )

    if clearly_underutilized:
        # Conservative first-pass estimate.
        # This is not an automatic rightsizing decision.
        estimated_savings = round(
            snapshot.monthly_cost_usd * 0.25,
            2,
        )

        return FinOpsAnalysis(
            namespace=snapshot.namespace,
            workload_name=snapshot.workload_name,
            workload_type=snapshot.workload_type,
            cpu_utilization_pct=cpu_utilization_pct,
            memory_utilization_pct=memory_utilization_pct,
            monthly_cost_usd=snapshot.monthly_cost_usd,
            waste_detected=True,
            recommendation=(
                "Workload appears underutilized. "
                "Review CPU and memory requests before proposing "
                "a rightsizing change through Git and Pull Request."
            ),
            estimated_monthly_savings_usd=estimated_savings,
            confidence="medium",
            requires_human_approval=True,
            auto_apply=False,
        )

    if not has_cpu_signal or not has_memory_signal:
        return FinOpsAnalysis(
            namespace=snapshot.namespace,
            workload_name=snapshot.workload_name,
            workload_type=snapshot.workload_type,
            cpu_utilization_pct=cpu_utilization_pct,
            memory_utilization_pct=memory_utilization_pct,
            monthly_cost_usd=snapshot.monthly_cost_usd,
            waste_detected=False,
            recommendation=(
                "Insufficient resource request data for a reliable "
                "rightsizing recommendation."
            ),
            estimated_monthly_savings_usd=None,
            confidence="low",
            requires_human_approval=True,
            auto_apply=False,
        )

    return FinOpsAnalysis(
        namespace=snapshot.namespace,
        workload_name=snapshot.workload_name,
        workload_type=snapshot.workload_type,
        cpu_utilization_pct=cpu_utilization_pct,
        memory_utilization_pct=memory_utilization_pct,
        monthly_cost_usd=snapshot.monthly_cost_usd,
        waste_detected=False,
        recommendation=(
            "No obvious resource waste detected by the current "
            "conservative FinOps rules."
        ),
        estimated_monthly_savings_usd=0.0,
        confidence="medium",
        requires_human_approval=True,
        auto_apply=False,
    )
