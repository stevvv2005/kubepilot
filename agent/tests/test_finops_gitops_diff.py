import pytest

from agent.finops_agent.gitops_diff import (
    _cpu_cores_to_kubernetes,
    _memory_mib_to_kubernetes,
    build_gitops_diff_proposal,
)
from agent.finops_agent.manifest_inspector import (
    FinOpsManifestState,
)
from agent.finops_agent.rightsizing_proposal import (
    RightsizingProposal,
)


def _manifest_state() -> FinOpsManifestState:
    return FinOpsManifestState(
        target_file=(
            "gitops/apps/online-boutique/base/"
            "kubernetes-manifests.yaml"
        ),
        manifest_kind="Deployment",
        manifest_name="checkoutservice",
        container_name="server",
        cpu_request="100m",
        memory_request="64Mi",
        cpu_limit="200m",
        memory_limit="128Mi",
        found=True,
        reason="test",
        read_only=True,
        performs_write=False,
    )


def _proposal() -> RightsizingProposal:
    return RightsizingProposal(
        namespace="default",
        workload_name="checkoutservice",
        workload_type="Deployment",
        current_cpu_request_cores=0.1,
        current_memory_request_mib=64.0,
        suggested_cpu_request_cores=0.01,
        suggested_memory_request_mib=16.0,
        cpu_utilization_pct=5.0,
        memory_utilization_pct=10.0,
        current_monthly_cost_usd=2.47,
        estimated_monthly_savings_usd=0.62,
        reason="test",
        confidence="medium",
        requires_human_approval=True,
        auto_apply=False,
        performs_write=False,
    )


def test_build_gitops_diff_proposal():
    diff = build_gitops_diff_proposal(
        proposal=_proposal(),
        manifest_state=_manifest_state(),
    )

    assert diff.namespace == "default"
    assert diff.workload_name == "checkoutservice"

    assert (
        diff.target_file
        == (
            "gitops/apps/online-boutique/base/"
            "kubernetes-manifests.yaml"
        )
    )

    assert diff.manifest_kind == "Deployment"
    assert diff.manifest_name == "checkoutservice"
    assert diff.container_name == "server"

    assert diff.current_cpu_request == "100m"
    assert diff.proposed_cpu_request == "10m"

    assert diff.current_memory_request == "64Mi"
    assert diff.proposed_memory_request == "16Mi"

    assert diff.estimated_monthly_savings_usd == 0.62

    assert diff.requires_human_approval is True
    assert diff.writes_file is False
    assert diff.writes_git is False
    assert diff.auto_apply is False


def test_pod_style_name_matches_manifest_name():
    proposal = _proposal()

    proposal = RightsizingProposal(
        namespace=proposal.namespace,
        workload_name="checkoutservice-abc123",
        workload_type=proposal.workload_type,
        current_cpu_request_cores=proposal.current_cpu_request_cores,
        current_memory_request_mib=proposal.current_memory_request_mib,
        suggested_cpu_request_cores=proposal.suggested_cpu_request_cores,
        suggested_memory_request_mib=proposal.suggested_memory_request_mib,
        cpu_utilization_pct=proposal.cpu_utilization_pct,
        memory_utilization_pct=proposal.memory_utilization_pct,
        current_monthly_cost_usd=proposal.current_monthly_cost_usd,
        estimated_monthly_savings_usd=(
            proposal.estimated_monthly_savings_usd
        ),
        reason=proposal.reason,
        confidence=proposal.confidence,
        requires_human_approval=True,
        auto_apply=False,
        performs_write=False,
    )

    diff = build_gitops_diff_proposal(
        proposal=proposal,
        manifest_state=_manifest_state(),
    )

    assert diff.manifest_name == "checkoutservice"


def test_cpu_conversion():
    assert _cpu_cores_to_kubernetes(0.1) == "100m"
    assert _cpu_cores_to_kubernetes(0.01) == "10m"
    assert _cpu_cores_to_kubernetes(0.3) == "300m"


def test_memory_conversion():
    assert _memory_mib_to_kubernetes(64.0) == "64Mi"
    assert _memory_mib_to_kubernetes(16.0) == "16Mi"
    assert _memory_mib_to_kubernetes(86.0) == "86Mi"


def test_none_values_remain_none():
    assert _cpu_cores_to_kubernetes(None) is None
    assert _memory_mib_to_kubernetes(None) is None


def test_negative_cpu_is_rejected():
    with pytest.raises(
        ValueError,
        match="CPU request cannot be negative",
    ):
        _cpu_cores_to_kubernetes(
            -0.1,
        )


def test_negative_memory_is_rejected():
    with pytest.raises(
        ValueError,
        match="Memory request cannot be negative",
    ):
        _memory_mib_to_kubernetes(
            -1.0,
        )


def test_unresolved_manifest_is_rejected():
    state = _manifest_state()

    state = FinOpsManifestState(
        target_file=state.target_file,
        manifest_kind=state.manifest_kind,
        manifest_name=state.manifest_name,
        container_name="",
        cpu_request=None,
        memory_request=None,
        cpu_limit=None,
        memory_limit=None,
        found=False,
        reason="not found",
        read_only=True,
        performs_write=False,
    )

    with pytest.raises(
        ValueError,
        match="unresolved manifest state",
    ):
        build_gitops_diff_proposal(
            proposal=_proposal(),
            manifest_state=state,
        )


def test_mismatched_workload_is_rejected():
    proposal = _proposal()

    proposal = RightsizingProposal(
        namespace="default",
        workload_name="frontend",
        workload_type=proposal.workload_type,
        current_cpu_request_cores=proposal.current_cpu_request_cores,
        current_memory_request_mib=proposal.current_memory_request_mib,
        suggested_cpu_request_cores=proposal.suggested_cpu_request_cores,
        suggested_memory_request_mib=proposal.suggested_memory_request_mib,
        cpu_utilization_pct=proposal.cpu_utilization_pct,
        memory_utilization_pct=proposal.memory_utilization_pct,
        current_monthly_cost_usd=proposal.current_monthly_cost_usd,
        estimated_monthly_savings_usd=(
            proposal.estimated_monthly_savings_usd
        ),
        reason=proposal.reason,
        confidence=proposal.confidence,
        requires_human_approval=True,
        auto_apply=False,
        performs_write=False,
    )

    with pytest.raises(
        ValueError,
        match="do not match",
    ):
        build_gitops_diff_proposal(
            proposal=proposal,
            manifest_state=_manifest_state(),
        )