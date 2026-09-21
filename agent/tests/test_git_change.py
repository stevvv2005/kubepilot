from agent.sre_agent.git_change import build_git_change_proposal
from agent.sre_agent.remediation import RemediationProposal


def test_imagepullbackoff_git_change_is_safe():
    remediation = RemediationProposal(
        incident_type="ImagePullBackOff",
        summary="Correct the container image configuration.",
        proposed_change="Update the image in Git.",
        target_file="gitops/apps/frontend/deployment.yaml",
    )

    proposal = build_git_change_proposal(remediation)

    assert proposal.incident_type == "ImagePullBackOff"
    assert proposal.change_type == "update_container_image"
    assert proposal.target_file == "gitops/apps/frontend/deployment.yaml"
    assert proposal.requires_human_approval is True
    assert proposal.apply_directly is False


def test_oomkilled_git_change_is_safe():
    remediation = RemediationProposal(
        incident_type="OOMKilled",
        summary="Increase memory limit.",
        proposed_change="Update memory in Git.",
        target_file="gitops/apps/checkout/deployment.yaml",
    )

    proposal = build_git_change_proposal(remediation)

    assert proposal.incident_type == "OOMKilled"
    assert proposal.change_type == "update_memory_limit"
    assert proposal.requires_human_approval is True
    assert proposal.apply_directly is False


def test_readiness_git_change_is_safe():
    remediation = RemediationProposal(
        incident_type="ReadinessProbeFailed",
        summary="Fix readiness probe.",
        proposed_change="Update readiness probe in Git.",
        target_file="gitops/apps/frontend/deployment.yaml",
    )

    proposal = build_git_change_proposal(remediation)

    assert proposal.incident_type == "ReadinessProbeFailed"
    assert proposal.change_type == "update_readiness_probe"
    assert proposal.requires_human_approval is True
    assert proposal.apply_directly is False


def test_healthy_has_no_git_change():
    remediation = RemediationProposal(
        incident_type="Healthy",
        summary="No remediation required.",
        proposed_change="No Git change is required.",
        target_file=None,
    )

    proposal = build_git_change_proposal(remediation)

    assert proposal.incident_type == "Healthy"
    assert proposal.change_type == "none"
    assert proposal.target_file is None
    assert proposal.apply_directly is False
