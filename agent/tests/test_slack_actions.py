import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

import agent.webhook.app as webhook_app
from agent.notifications.slack_approval_repository import (
    InMemoryApprovalRepository,
)
from agent.notifications.slack_approval_service import SlackApprovalService
from agent.sre_agent.candidate_value import CandidateValue
from agent.sre_agent.patch_proposal import PatchProposal


SECRET = "slack-test-secret"


class FakeGitHubClient:
    def __init__(self):
        self.calls = []

    def get_branch_sha(self, *, repository, branch):
        self.calls.append(("get_branch_sha", repository, branch))
        return "base-sha"

    def create_branch(self, *, repository, branch, source_sha):
        self.calls.append(("create_branch", repository, branch, source_sha))

    def update_file(
        self,
        *,
        repository,
        branch,
        path,
        content,
        message,
    ):
        self.calls.append(
            ("update_file", repository, branch, path, content, message)
        )
        return "commit-sha"

    def create_pull_request(
        self,
        *,
        repository,
        base_branch,
        head_branch,
        title,
        body,
    ):
        self.calls.append(
            (
                "create_pull_request",
                repository,
                base_branch,
                head_branch,
                title,
                body,
            )
        )
        return 99, "https://github.test/pull/99"


@pytest.fixture
def approval_context(monkeypatch):
    repository = InMemoryApprovalRepository()
    github_client = FakeGitHubClient()
    service = SlackApprovalService(
        repository,
        repository_root=".",
        github_client_factory=lambda: github_client,
    )
    monkeypatch.setattr(webhook_app, "slack_approval_service", service)
    monkeypatch.setattr(webhook_app, "slack_approval_repository", repository)
    monkeypatch.setenv("SLACK_SIGNING_SECRET", SECRET)
    monkeypatch.setenv("KUBEPILOT_GITHUB_LIVE_AUTHORIZED", "false")

    record = service.register_remediation(
        patch_proposal=PatchProposal(
            incident_type="OOMKilled",
            target_file="chaos/oomkilled-pod.yaml",
            container_name="memory-hog",
            field="resources.limits.memory",
            current_value="memory: 32Mi",
            proposed_value=None,
            reason="Review memory limit.",
        ),
        candidate_value=CandidateValue(
            incident_type="OOMKilled",
            field="resources.limits.memory",
            current_value="memory: 32Mi",
            candidate_value="64Mi",
            reason="Conservative increase.",
            confidence="medium",
        ),
        namespace="default",
        pod_name="kubepilot-oomkilled",
        container_name="memory-hog",
        diagnosis="Container exceeded its memory limit.",
        evidence=("terminated_reason=OOMKilled",),
    )
    return repository, github_client, record


def _signed_request(
    remediation_id,
    action_id,
    *,
    timestamp=None,
    extra=None,
):
    payload = {
        "type": "block_actions",
        "team": {"id": "T123"},
        "channel": {"id": "C123"},
        "user": {"id": "U123", "username": "reviewer"},
        "actions": [
            {
                "action_id": action_id,
                "value": remediation_id,
                "action_ts": "1700000000.000100",
            }
        ],
    }
    if extra:
        payload.update(extra)
    body = urlencode({"payload": json.dumps(payload)}).encode()
    request_timestamp = int(time.time()) if timestamp is None else timestamp
    base = f"v0:{request_timestamp}:".encode() + body
    signature = "v0=" + hmac.new(
        SECRET.encode(), base, hashlib.sha256
    ).hexdigest()
    return body, {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Slack-Request-Timestamp": str(request_timestamp),
        "X-Slack-Signature": signature,
    }


def _post(client, remediation_id, action_id, **kwargs):
    body, headers = _signed_request(remediation_id, action_id, **kwargs)
    return client.post("/slack/actions", content=body, headers=headers)


def test_valid_approve_is_recorded_and_live_execution_is_blocked(
    approval_context,
):
    repository, github_client, record = approval_context
    response = _post(
        TestClient(webhook_app.app),
        record.remediation_id,
        "kubepilot_approve",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPROVED"
    assert body["approved_value"] == "64Mi"
    assert body["reviewer"] == {
        "id": "U123",
        "name": "reviewer",
        "source": "slack",
    }
    assert body["github_execution"]["blocked"] is True
    assert body["github_execution"]["executed"] is False
    assert body["safety"]["performs_cluster_write"] is False
    assert body["safety"]["auto_merge"] is False
    assert github_client.calls == []
    assert repository.get(record.remediation_id).reviewer_id == "U123"


def test_valid_reject_never_calls_github(approval_context):
    repository, github_client, record = approval_context
    response = _post(
        TestClient(webhook_app.app),
        record.remediation_id,
        "kubepilot_reject",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    assert response.json()["approved"] is False
    assert response.json()["rejection_reason"] == (
        "Rejected through verified Slack interaction."
    )
    assert repository.get(record.remediation_id).source == "slack"
    assert github_client.calls == []


def test_unknown_remediation_is_not_accepted(approval_context):
    response = _post(
        TestClient(webhook_app.app),
        "rem_unknown",
        "kubepilot_approve",
    )
    assert response.status_code == 404


def test_malformed_action_is_rejected(approval_context):
    _, _, record = approval_context
    response = _post(
        TestClient(webhook_app.app),
        record.remediation_id,
        "kubepilot_delete",
    )
    assert response.status_code == 400


def test_malformed_signed_metadata_is_rejected(approval_context):
    _, _, record = approval_context
    response = _post(
        TestClient(webhook_app.app),
        record.remediation_id,
        "kubepilot_approve",
        extra={"team": "not-an-object"},
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ("kubepilot_approve", "kubepilot_approve", 200),
        ("kubepilot_reject", "kubepilot_reject", 200),
        ("kubepilot_reject", "kubepilot_approve", 409),
        ("kubepilot_approve", "kubepilot_reject", 409),
    ],
)
def test_terminal_decisions_are_idempotent_and_cannot_be_reversed(
    approval_context,
    first,
    second,
    expected,
):
    _, _, record = approval_context
    client = TestClient(webhook_app.app)
    assert _post(client, record.remediation_id, first).status_code == 200
    response = _post(client, record.remediation_id, second)
    assert response.status_code == expected
    if expected == 200:
        assert response.json()["idempotent"] is True


def test_live_approval_executes_once_using_only_trusted_server_state(
    approval_context,
    monkeypatch,
):
    _, github_client, record = approval_context
    monkeypatch.setenv("KUBEPILOT_GITHUB_LIVE_AUTHORIZED", "true")
    hostile = {
        "repository": "attacker/repository",
        "branch": "main",
        "target_file": "../../other.yaml",
        "rendered_yaml": "malicious: true",
    }
    client = TestClient(webhook_app.app)
    first = _post(
        client,
        record.remediation_id,
        "kubepilot_approve",
        extra=hostile,
    )
    second = _post(client, record.remediation_id, "kubepilot_approve")

    assert first.status_code == 200
    assert first.json()["status"] == "EXECUTED"
    assert first.json()["github_execution"]["pr_url"] == (
        "https://github.test/pull/99"
    )
    assert second.status_code == 200
    assert second.json()["idempotent"] is True
    assert len([call for call in github_client.calls if call[0] == "create_pull_request"]) == 1

    update_call = next(call for call in github_client.calls if call[0] == "update_file")
    assert update_call[1] == "stevvv2005/kubepilot"
    assert update_call[2] == "fix/sre-oomkilled"
    assert update_call[3] == "chaos/oomkilled-pod.yaml"
    assert "memory: 64Mi" in update_call[4]
    assert "malicious" not in update_call[4]


def test_missing_or_invalid_signature_is_rejected(approval_context):
    _, _, record = approval_context
    client = TestClient(webhook_app.app)
    body, headers = _signed_request(
        record.remediation_id,
        "kubepilot_approve",
    )
    headers.pop("X-Slack-Signature")
    assert client.post(
        "/slack/actions", content=body, headers=headers
    ).status_code == 401

    headers["X-Slack-Signature"] = "v0=invalid"
    assert client.post(
        "/slack/actions", content=body, headers=headers
    ).status_code == 401


def test_stale_callback_is_rejected(approval_context):
    repository, _, record = approval_context
    response = _post(
        TestClient(webhook_app.app),
        record.remediation_id,
        "kubepilot_approve",
        timestamp=int(time.time()) - 301,
    )
    assert response.status_code == 401
    assert repository.audit_entries()[-1].event == "replay_blocked"
