from dataclasses import dataclass
from typing import Optional

from agent.finops_agent.manifest_inspector import (
    FinOpsManifestState,
)
from agent.finops_agent.rightsizing_proposal import (
    RightsizingProposal,
)


@dataclass(frozen=True)
class GitOpsDiffProposal:
    namespace: str
    workload_name: str
    workload_type: str

    target_file: str
    manifest_kind: str
    manifest_name: str
    container_name: str

    current_cpu_request: Optional[str]
    proposed_cpu_request: Optional[str]

    current_memory_request: Optional[str]
    proposed_memory_request: Optional[str]

    estimated_monthly_savings_usd: Optional[float]

    reason: str
    confidence: str

    requires_human_approval: bool = True
    writes_file: bool = False
    writes_git: bool = False
    auto_apply: bool = False


def _cpu_cores_to_kubernetes(
    value: Optional[float],
) -> Optional[str]:
    if value is None:
        return None

    if value < 0:
        raise ValueError(
            "CPU request cannot be negative."
        )

    millicores = round(
        value * 1000
    )

    return f"{millicores}m"


def _memory_mib_to_kubernetes(
    value: Optional[float],
) -> Optional[str]:
    if value is None:
        return None

    if value < 0:
        raise ValueError(
            "Memory request cannot be negative."
        )

    memory_mib = round(
        value
    )

    return f"{memory_mib}Mi"


def build_gitops_diff_proposal(
    proposal: RightsizingProposal,
    manifest_state: FinOpsManifestState,
) -> GitOpsDiffProposal:
    """
    Build a read-only GitOps diff proposal.

    No file, Git, Kubernetes, or cloud write is performed.
    """

    if not manifest_state.found:
        raise ValueError(
            "Cannot build GitOps diff from an unresolved manifest state."
        )

    if (
        proposal.namespace
        != "default"
    ):
        raise ValueError(
            "FinOps GitOps diff is currently restricted to "
            "the default namespace."
        )

    if (
        proposal.workload_name
        != manifest_state.manifest_name
        and not proposal.workload_name.startswith(
            f"{manifest_state.manifest_name}-"
        )
    ):
        raise ValueError(
            "Rightsizing proposal and manifest do not match."
        )

    proposed_cpu = _cpu_cores_to_kubernetes(
        proposal.suggested_cpu_request_cores,
    )

    proposed_memory = _memory_mib_to_kubernetes(
        proposal.suggested_memory_request_mib,
    )

    return GitOpsDiffProposal(
        namespace=proposal.namespace,
        workload_name=proposal.workload_name,
        workload_type=proposal.workload_type,
        target_file=manifest_state.target_file,
        manifest_kind=manifest_state.manifest_kind,
        manifest_name=manifest_state.manifest_name,
        container_name=manifest_state.container_name,
        current_cpu_request=manifest_state.cpu_request,
        proposed_cpu_request=proposed_cpu,
        current_memory_request=manifest_state.memory_request,
        proposed_memory_request=proposed_memory,
        estimated_monthly_savings_usd=(
            proposal.estimated_monthly_savings_usd
        ),
        reason=(
            "Compare current GitOps resource requests "
            "with the human-reviewable FinOps rightsizing proposal."
        ),
        confidence=proposal.confidence,
        requires_human_approval=True,
        writes_file=False,
        writes_git=False,
        auto_apply=False,
    )