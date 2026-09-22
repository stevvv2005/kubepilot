from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CandidateValue:
    incident_type: str
    field: str
    current_value: Optional[str]
    candidate_value: Optional[str]
    reason: str
    confidence: str
    requires_human_approval: bool = True
    auto_apply: bool = False


def suggest_candidate_value(
    incident_type: str,
    field: str,
    current_value: Optional[str],
) -> CandidateValue:
    """
    Suggest a candidate value for a remediation.

    This function only returns a recommendation.
    It never writes files and never modifies Kubernetes.
    """

    if incident_type == "OOMKilled":
        if current_value == "memory: 32Mi":
            return CandidateValue(
                incident_type=incident_type,
                field=field,
                current_value=current_value,
                candidate_value="64Mi",
                reason=(
                    "Increase the memory limit conservatively from 32Mi "
                    "to 64Mi for human review."
                ),
                confidence="medium",
            )

        return CandidateValue(
            incident_type=incident_type,
            field=field,
            current_value=current_value,
            candidate_value=None,
            reason=(
                "No deterministic memory recommendation is available "
                "for the current limit."
            ),
            confidence="low",
        )

    if incident_type == "ImagePullBackOff":
        return CandidateValue(
            incident_type=incident_type,
            field=field,
            current_value=current_value,
            candidate_value=None,
            reason=(
                "A replacement image must be validated before it can "
                "be proposed safely."
            ),
            confidence="low",
        )

    if incident_type == "ReadinessProbeFailed":
        return CandidateValue(
            incident_type=incident_type,
            field=field,
            current_value=current_value,
            candidate_value=None,
            reason=(
                "The correct readiness probe depends on the application "
                "endpoint and must be validated before proposing a value."
            ),
            confidence="low",
        )

    if incident_type == "Healthy":
        return CandidateValue(
            incident_type=incident_type,
            field="none",
            current_value=None,
            candidate_value=None,
            reason="No candidate value is required.",
            confidence="high",
        )

    return CandidateValue(
        incident_type=incident_type,
        field=field,
        current_value=current_value,
        candidate_value=None,
        reason="Manual investigation is required.",
        confidence="low",
    )
