import json

import pytest

from agent.llm.output_validator import (
    validate_llm_output,
)


def _valid_payload():
    return {
        "summary": (
            "The workload exceeded its "
            "configured memory limit."
        ),
        "evidence": [
            "OOMKilled event detected.",
            "Runbook indicates memory limit exhaustion.",
        ],
        "recommendation": (
            "Review memory usage and prepare "
            "a GitOps change for human approval."
        ),
        "uncertainty": (
            "Recent memory history is not available."
        ),
        "requires_human_approval": True,
        "allows_direct_cluster_write": False,
    }


def test_valid_output():
    result = validate_llm_output(
        json.dumps(
            _valid_payload()
        )
    )

    assert (
        result.summary
        == (
            "The workload exceeded its "
            "configured memory limit."
        )
    )

    assert len(result.evidence) == 2

    assert (
        result.requires_human_approval
        is True
    )

    assert (
        result.allows_direct_cluster_write
        is False
    )

    assert result.performs_write is False


def test_invalid_json_is_rejected():
    with pytest.raises(
        ValueError,
        match="valid JSON",
    ):
        validate_llm_output(
            "not-json"
        )


def test_non_object_json_is_rejected():
    with pytest.raises(
        ValueError,
        match="JSON object",
    ):
        validate_llm_output(
            '["invalid"]'
        )


def test_missing_summary_is_rejected():
    payload = _valid_payload()
    payload.pop("summary")

    with pytest.raises(
        ValueError,
        match="summary",
    ):
        validate_llm_output(
            json.dumps(payload)
        )


def test_empty_recommendation_is_rejected():
    payload = _valid_payload()
    payload["recommendation"] = "   "

    with pytest.raises(
        ValueError,
        match="recommendation",
    ):
        validate_llm_output(
            json.dumps(payload)
        )


def test_evidence_must_be_list():
    payload = _valid_payload()
    payload["evidence"] = "not-a-list"

    with pytest.raises(
        ValueError,
        match="evidence",
    ):
        validate_llm_output(
            json.dumps(payload)
        )


def test_evidence_entries_must_be_strings():
    payload = _valid_payload()
    payload["evidence"] = [
        "valid",
        123,
    ]

    with pytest.raises(
        ValueError,
        match="evidence entries",
    ):
        validate_llm_output(
            json.dumps(payload)
        )


def test_missing_human_approval_is_rejected():
    payload = _valid_payload()
    payload[
        "requires_human_approval"
    ] = False

    with pytest.raises(
        ValueError,
        match="must require human approval",
    ):
        validate_llm_output(
            json.dumps(payload)
        )


def test_direct_cluster_write_is_rejected():
    payload = _valid_payload()
    payload[
        "allows_direct_cluster_write"
    ] = True

    with pytest.raises(
        ValueError,
        match="cannot allow direct",
    ):
        validate_llm_output(
            json.dumps(payload)
        )


def test_boolean_fields_must_be_boolean():
    payload = _valid_payload()
    payload[
        "requires_human_approval"
    ] = "true"

    with pytest.raises(
        ValueError,
        match="must be a boolean",
    ):
        validate_llm_output(
            json.dumps(payload)
        )


def test_empty_content_is_rejected():
    with pytest.raises(
        ValueError,
        match="content is required",
    ):
        validate_llm_output(
            "   "
        )