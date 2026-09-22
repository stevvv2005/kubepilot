from agent.sre_agent.candidate_value import suggest_candidate_value


def test_oomkilled_suggests_conservative_memory_candidate():
    candidate = suggest_candidate_value(
        incident_type="OOMKilled",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
    )

    assert candidate.incident_type == "OOMKilled"
    assert candidate.field == "resources.limits.memory"
    assert candidate.current_value == "memory: 32Mi"
    assert candidate.candidate_value == "64Mi"
    assert candidate.confidence == "medium"
    assert candidate.requires_human_approval is True
    assert candidate.auto_apply is False


def test_oomkilled_unknown_memory_has_no_candidate():
    candidate = suggest_candidate_value(
        incident_type="OOMKilled",
        field="resources.limits.memory",
        current_value="memory: 128Mi",
    )

    assert candidate.candidate_value is None
    assert candidate.confidence == "low"
    assert candidate.requires_human_approval is True
    assert candidate.auto_apply is False


def test_imagepullbackoff_does_not_guess_image():
    candidate = suggest_candidate_value(
        incident_type="ImagePullBackOff",
        field="image",
        current_value=(
            "image: ghcr.io/kubepilot/"
            "this-image-does-not-exist:never"
        ),
    )

    assert candidate.candidate_value is None
    assert candidate.confidence == "low"
    assert candidate.requires_human_approval is True
    assert candidate.auto_apply is False


def test_readiness_does_not_guess_probe():
    candidate = suggest_candidate_value(
        incident_type="ReadinessProbeFailed",
        field="readinessProbe",
        current_value=(
            "readinessProbe: "
            "path=/this-path-does-not-exist, port=80"
        ),
    )

    assert candidate.candidate_value is None
    assert candidate.confidence == "low"
    assert candidate.requires_human_approval is True
    assert candidate.auto_apply is False


def test_healthy_has_no_candidate():
    candidate = suggest_candidate_value(
        incident_type="Healthy",
        field="none",
        current_value=None,
    )

    assert candidate.field == "none"
    assert candidate.current_value is None
    assert candidate.candidate_value is None
    assert candidate.confidence == "high"
    assert candidate.requires_human_approval is True
    assert candidate.auto_apply is False
