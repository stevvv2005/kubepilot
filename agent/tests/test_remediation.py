from agent.sre_agent.diagnostic import Diagnosis
from agent.sre_agent.remediation import build_remediation_proposal


def test_oomkilled_remediation_is_git_only():
    diagnosis = Diagnosis(
        incident_type="OOMKilled",
        root_cause="Memory limit exceeded.",
        recommendation="Increase memory through Git/PR.",
        confidence="high",
    )

    proposal = build_remediation_proposal(
        diagnosis,
        target_file="gitops/apps/checkout/deployment.yaml",
    )

    assert proposal.incident_type == "OOMKilled"
    assert proposal.requires_human_approval is True
    assert proposal.direct_cluster_write is False
    assert "Pull Request" in proposal.proposed_change
    assert proposal.target_file == "gitops/apps/checkout/deployment.yaml"


def test_imagepullbackoff_remediation_is_git_only():
    diagnosis = Diagnosis(
        incident_type="ImagePullBackOff",
        root_cause="Invalid image.",
        recommendation="Fix image configuration.",
        confidence="high",
    )

    proposal = build_remediation_proposal(diagnosis)

    assert proposal.incident_type == "ImagePullBackOff"
    assert proposal.requires_human_approval is True
    assert proposal.direct_cluster_write is False
    assert "Git" in proposal.proposed_change


def test_readiness_remediation_is_git_only():
    diagnosis = Diagnosis(
        incident_type="ReadinessProbeFailed",
        root_cause="Readiness probe is failing.",
        recommendation="Review readiness configuration.",
        confidence="medium",
    )

    proposal = build_remediation_proposal(diagnosis)

    assert proposal.incident_type == "ReadinessProbeFailed"
    assert proposal.requires_human_approval is True
    assert proposal.direct_cluster_write is False
    assert "Pull Request" in proposal.proposed_change


def test_healthy_requires_no_remediation():
    diagnosis = Diagnosis(
        incident_type="Healthy",
        root_cause="No incident.",
        recommendation="No action.",
        confidence="high",
    )

    proposal = build_remediation_proposal(diagnosis)

    assert proposal.incident_type == "Healthy"
    assert proposal.target_file is None
    assert proposal.direct_cluster_write is False
    assert proposal.proposed_change == "No Git change is required."
