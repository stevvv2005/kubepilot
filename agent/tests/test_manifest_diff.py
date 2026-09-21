from agent.sre_agent.git_change import GitChangeProposal
from agent.sre_agent.manifest_diff import build_manifest_diff_proposal


def test_imagepullbackoff_manifest_diff_is_safe():
    git_change = GitChangeProposal(
        incident_type="ImagePullBackOff",
        target_file="gitops/apps/frontend/deployment.yaml",
        change_type="update_container_image",
        description="Prepare image correction.",
    )

    diff = build_manifest_diff_proposal(git_change)

    assert diff.incident_type == "ImagePullBackOff"
    assert diff.change_type == "update_container_image"
    assert diff.target_file == "gitops/apps/frontend/deployment.yaml"
    assert diff.before == "image: invalid-or-missing-image"
    assert diff.after == "image: <validated-image>:<validated-tag>"
    assert diff.requires_human_approval is True
    assert diff.writes_file is False


def test_oomkilled_manifest_diff_is_safe():
    git_change = GitChangeProposal(
        incident_type="OOMKilled",
        target_file="gitops/apps/checkout/deployment.yaml",
        change_type="update_memory_limit",
        description="Prepare memory correction.",
    )

    diff = build_manifest_diff_proposal(git_change)

    assert diff.incident_type == "OOMKilled"
    assert diff.change_type == "update_memory_limit"
    assert diff.before == "memory: <current-limit>"
    assert diff.after == "memory: <reviewed-new-limit>"
    assert diff.requires_human_approval is True
    assert diff.writes_file is False


def test_readiness_manifest_diff_is_safe():
    git_change = GitChangeProposal(
        incident_type="ReadinessProbeFailed",
        target_file="gitops/apps/frontend/deployment.yaml",
        change_type="update_readiness_probe",
        description="Prepare readiness correction.",
    )

    diff = build_manifest_diff_proposal(git_change)

    assert diff.incident_type == "ReadinessProbeFailed"
    assert diff.change_type == "update_readiness_probe"
    assert diff.before == "readinessProbe: <current-configuration>"
    assert diff.after == "readinessProbe: <validated-configuration>"
    assert diff.requires_human_approval is True
    assert diff.writes_file is False


def test_healthy_has_no_manifest_diff():
    git_change = GitChangeProposal(
        incident_type="Healthy",
        target_file=None,
        change_type="none",
        description="No Git change is required.",
    )

    diff = build_manifest_diff_proposal(git_change)

    assert diff.incident_type == "Healthy"
    assert diff.change_type == "none"
    assert diff.target_file is None
    assert diff.before is None
    assert diff.after is None
    assert diff.writes_file is False
