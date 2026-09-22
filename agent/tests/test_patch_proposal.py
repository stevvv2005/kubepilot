from agent.sre_agent.manifest_diff import ManifestDiffProposal
from agent.sre_agent.patch_proposal import build_patch_proposal


def test_imagepullbackoff_patch_proposal_is_safe():
    manifest_diff = ManifestDiffProposal(
        incident_type="ImagePullBackOff",
        target_file="chaos/imagepullbackoff-pod.yaml",
        change_type="update_container_image",
        before="image: ghcr.io/kubepilot/this-image-does-not-exist:never",
        after="image: <validated-image>:<validated-tag>",
    )

    proposal = build_patch_proposal(
        manifest_diff=manifest_diff,
        container_name="broken-container",
        proposed_value="nginx:1.27",
    )

    assert proposal.incident_type == "ImagePullBackOff"
    assert proposal.target_file == "chaos/imagepullbackoff-pod.yaml"
    assert proposal.container_name == "broken-container"
    assert proposal.field == "image"
    assert proposal.current_value == (
        "image: ghcr.io/kubepilot/this-image-does-not-exist:never"
    )
    assert proposal.proposed_value == "nginx:1.27"
    assert proposal.requires_human_approval is True
    assert proposal.writes_file is False


def test_oomkilled_patch_proposal_is_safe():
    manifest_diff = ManifestDiffProposal(
        incident_type="OOMKilled",
        target_file="chaos/oomkilled-pod.yaml",
        change_type="update_memory_limit",
        before="memory: 32Mi",
        after="memory: <reviewed-new-limit>",
    )

    proposal = build_patch_proposal(
        manifest_diff=manifest_diff,
        container_name="memory-hog",
        proposed_value="64Mi",
    )

    assert proposal.incident_type == "OOMKilled"
    assert proposal.container_name == "memory-hog"
    assert proposal.field == "resources.limits.memory"
    assert proposal.current_value == "memory: 32Mi"
    assert proposal.proposed_value == "64Mi"
    assert proposal.requires_human_approval is True
    assert proposal.writes_file is False


def test_readiness_patch_proposal_is_safe():
    manifest_diff = ManifestDiffProposal(
        incident_type="ReadinessProbeFailed",
        target_file="chaos/readiness-failed-pod.yaml",
        change_type="update_readiness_probe",
        before=(
            "readinessProbe: "
            "path=/this-path-does-not-exist, port=80"
        ),
        after="readinessProbe: <validated-configuration>",
    )

    proposal = build_patch_proposal(
        manifest_diff=manifest_diff,
        container_name="web",
        proposed_value="path=/, port=80",
    )

    assert proposal.incident_type == "ReadinessProbeFailed"
    assert proposal.container_name == "web"
    assert proposal.field == "readinessProbe"
    assert proposal.proposed_value == "path=/, port=80"
    assert proposal.requires_human_approval is True
    assert proposal.writes_file is False


def test_healthy_has_no_patch():
    manifest_diff = ManifestDiffProposal(
        incident_type="Healthy",
        target_file=None,
        change_type="none",
        before=None,
        after=None,
    )

    proposal = build_patch_proposal(
        manifest_diff=manifest_diff,
    )

    assert proposal.incident_type == "Healthy"
    assert proposal.target_file is None
    assert proposal.container_name is None
    assert proposal.field == "none"
    assert proposal.current_value is None
    assert proposal.proposed_value is None
    assert proposal.requires_human_approval is True
    assert proposal.writes_file is False
