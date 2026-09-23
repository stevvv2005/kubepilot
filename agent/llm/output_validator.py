import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class StructuredLLMOutput:
    summary: str
    evidence: tuple[str, ...]
    recommendation: str
    uncertainty: str

    requires_human_approval: bool
    allows_direct_cluster_write: bool

    performs_write: bool = False


def _require_non_empty_string(
    payload: dict[str, Any],
    field: str,
) -> str:
    value = payload.get(field)

    if not isinstance(value, str):
        raise ValueError(
            f"LLM output field '{field}' "
            "must be a string."
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"LLM output field '{field}' "
            "must not be empty."
        )

    return normalized


def _require_boolean(
    payload: dict[str, Any],
    field: str,
) -> bool:
    value = payload.get(field)

    if not isinstance(value, bool):
        raise ValueError(
            f"LLM output field '{field}' "
            "must be a boolean."
        )

    return value


def _parse_evidence(
    payload: dict[str, Any],
) -> tuple[str, ...]:
    evidence = payload.get("evidence")

    if not isinstance(evidence, list):
        raise ValueError(
            "LLM output field 'evidence' "
            "must be a list."
        )

    normalized = []

    for item in evidence:
        if not isinstance(item, str):
            raise ValueError(
                "LLM output evidence entries "
                "must be strings."
            )

        value = item.strip()

        if not value:
            raise ValueError(
                "LLM output evidence entries "
                "must not be empty."
            )

        normalized.append(
            value
        )

    return tuple(normalized)


def validate_llm_output(
    content: str,
) -> StructuredLLMOutput:
    """
    Validate structured LLM JSON output.

    This function performs no network, Kubernetes,
    Git, or cloud write.
    """

    normalized_content = content.strip()

    if not normalized_content:
        raise ValueError(
            "LLM output content is required."
        )

    try:
        payload = json.loads(
            normalized_content
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            "LLM output must be valid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError(
            "LLM output must be a JSON object."
        )

    summary = _require_non_empty_string(
        payload,
        "summary",
    )

    evidence = _parse_evidence(
        payload
    )

    recommendation = _require_non_empty_string(
        payload,
        "recommendation",
    )

    uncertainty = _require_non_empty_string(
        payload,
        "uncertainty",
    )

    requires_human_approval = _require_boolean(
        payload,
        "requires_human_approval",
    )

    allows_direct_cluster_write = _require_boolean(
        payload,
        "allows_direct_cluster_write",
    )

    if not requires_human_approval:
        raise ValueError(
            "LLM output must require human approval."
        )

    if allows_direct_cluster_write:
        raise ValueError(
            "LLM output cannot allow direct "
            "Kubernetes writes."
        )

    return StructuredLLMOutput(
        summary=summary,
        evidence=evidence,
        recommendation=recommendation,
        uncertainty=uncertainty,
        requires_human_approval=True,
        allows_direct_cluster_write=False,
        performs_write=False,
    )