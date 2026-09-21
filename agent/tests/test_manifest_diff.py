from agent.sre_agent.git_change import GitChangeProposal
from agent.sre_agent.manifest_diff import build_manifest_diff_proposal


def test_imagepullbackoff_manifest_diff_reads_real_image():
    git_change = GitChangeProposal(
        incident_type="ImagePullBackOff",
        target_file="chaos/imagepullbackoff-pod.yaml",
        change_type="update_container_image",
        description="Prepare image correction.",
    )

    diff = build_manifest_diff_proposal(
        git_change=git_change,
        container_name="broken-container",
    )

    assert diff.incident_type == "ImagePullBackOff"
    assert diff.change_type == "update_container_image"
    assert diff.target_file == "chaos/imagepullbackoff-pod.yaml"
    assert diff.before == (
        "image: ghcr.io/kubepilot/this-image-does-not-exist:never"
    )
    assert diff.after == "image: <validated-image>:<validated-tag>"
    assert diff.requires_human_approval is True
    assert diff.writes_file is False


def test_imagepullbackoff_without_manifest_context_uses_unknown():
    git_change = GitChangeProposal(
        incident_type="ImagePullBackOff",
        target_file=None,
        change_type="update_container_image",
        description="Prepare image correction.",
    )

    diff = build_manifest_diff_proposal(git_change)

    assert diff.before == "image: <unknown>"
    assert diff.after == "image: <validated-image>:<validated-tag>"
    assert diff.requires_human_approval is True
    assert diff.writes_file is False


def test_oomkilled_manifest_diff_reads_real_memory_limit():
    git_change = GitChangeProposal(
        incident_type="OOMKilled",
        target_file="chaos/oomkilled-pod.yaml",
        change_type="update_memory_limit",
        description="Prepare memory correction.",
    )

    diff = build_manifest_diff_proposal(
        git_change=git_change,
        container_name="memory-hog",
    )

    assert diff.incident_type == "OOMKilled"
    assert diff.change_type == "update_memory_limit"
    assert diff.target_file == "chaos/oomkilled-pod.yaml"
    assert diff.before == "memory: 32Mi"
    assert diff.after == "memory: <reviewed-new-limit>"
    assert diff.requires_human_approval is True
    assert diff.writes_file is False


def test_oomkilled_without_manifest_context_uses_unknown():
    git_change = GitChangeProposal(
        incident_type="OOMKilled",
        target_file=None,
        change_type="update_memory_limit",
        description="Prepare memory correction.",
    )

    diff = build_manifest_diff_proposal(git_change)

    assert diff.before == "memory: <unknown>"
    assert diff.after == "memory: <reviewed-new-limit>"
    assert diff.requires_human_approval is True
    assert diff.writes_file is False


def test_readiness_manifest_diff_reads_real_probe():
    git_change = GitChangeProposal(
        incident_type="ReadinessProbeFailed",
        target_file="chaos/readiness-failed-pod.yaml",
        change_type="update_readiness_probe",
        description="Prepare readiness correction.",
    )

    diff = build_manifest_diff_proposal(
        git_change=git_change,
        container_name="web",
    )

    assert diff.incident_type == "ReadinessProbeFailed"
    assert diff.change_type == "update_readiness_probe"
    assert diff.target_file == "chaos/readiness-failed-pod.yaml"
    assert diff.before == (
        "readinessProbe: path=/this-path-does-not-exist, port=80"
    )
    assert diff.after == "readinessProbe: <validated-configuration>"
    assert diff.requires_human_approval is True
    assert diff.writes_file is False


def test_readiness_without_manifest_context_uses_unknown():
    git_change = GitChangeProposal(
        incident_type="ReadinessProbeFailed",
        target_file=None,
        change_type="update_readiness_probe",
        description="Prepare readiness correction.",
    )

    diff = build_manifest_diff_proposal(git_change)

    assert diff.before == "readinessProbe: <unknown>"
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
    assert diff.requires_human_approval is True
    assert diff.writes_file is False
