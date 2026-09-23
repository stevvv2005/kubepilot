from dataclasses import replace

from agent.sre_agent.git_commit_dry_run import GitCommitDryRun
from agent.sre_agent.git_execution_gateway import validate_git_execution
from agent.sre_agent.github_pr import GitHubPRGatewayResult
from agent.sre_agent.pr_payload import PullRequestPayload


def build_commit_plan() -> GitCommitDryRun:
    return GitCommitDryRun(
        target_file="chaos/oomkilled-pod.yaml",
        branch_name="fix/sre-oomkilled",
        commit_message="fix(sre): remediate OOMKilled",
        rendered_yaml="memory: 64Mi\n",
        ready_to_commit=True,
        performs_write=False,
        writes_file=False,
        writes_git=False,
    )


def build_pr_payload() -> PullRequestPayload:
    return PullRequestPayload(
        incident_type="OOMKilled",
        title="fix(sre): remediate OOMKilled",
        branch_name="fix/sre-oomkilled",
        target_file="chaos/oomkilled-pod.yaml",
        container_name="memory-hog",
        field="resources.limits.memory",
        current_value="memory: 32Mi",
        approved_value="64Mi",
        commit_message="fix(sre): remediate OOMKilled",
        pr_body="Approved remediation.",
        ready_to_create=True,
        writes_git=False,
        creates_pr=False,
    )


def build_github_gateway() -> GitHubPRGatewayResult:
    return GitHubPRGatewayResult(
        allowed=True,
        reason="Payload passed all GitHub PR safety checks.",
        ready_to_send=True,
        performs_write=False,
    )


def test_approved_execution_passes_gateway():
    result = validate_git_execution(
        commit_plan=build_commit_plan(),
        pr_payload=build_pr_payload(),
        github_gateway=build_github_gateway(),
    )

    assert result.allowed is True
    assert result.ready_to_execute is True
    assert result.performs_write is False


def test_commit_plan_must_be_ready():
    commit_plan = replace(
        build_commit_plan(),
        ready_to_commit=False,
    )

    result = validate_git_execution(
        commit_plan=commit_plan,
        pr_payload=build_pr_payload(),
        github_gateway=build_github_gateway(),
    )

    assert result.allowed is False
    assert result.ready_to_execute is False


def test_pr_payload_must_be_ready():
    pr_payload = replace(
        build_pr_payload(),
        ready_to_create=False,
    )

    result = validate_git_execution(
        commit_plan=build_commit_plan(),
        pr_payload=pr_payload,
        github_gateway=build_github_gateway(),
    )

    assert result.allowed is False
    assert result.ready_to_execute is False


def test_github_gateway_must_allow_execution():
    github_gateway = replace(
        build_github_gateway(),
        allowed=False,
        ready_to_send=False,
    )

    result = validate_git_execution(
        commit_plan=build_commit_plan(),
        pr_payload=build_pr_payload(),
        github_gateway=github_gateway,
    )

    assert result.allowed is False
    assert result.ready_to_execute is False


def test_commit_plan_write_flag_is_blocked():
    commit_plan = replace(
        build_commit_plan(),
        writes_git=True,
    )

    result = validate_git_execution(
        commit_plan=commit_plan,
        pr_payload=build_pr_payload(),
        github_gateway=build_github_gateway(),
    )

    assert result.allowed is False
    assert result.ready_to_execute is False


def test_pr_creation_flag_is_blocked():
    pr_payload = replace(
        build_pr_payload(),
        creates_pr=True,
    )

    result = validate_git_execution(
        commit_plan=build_commit_plan(),
        pr_payload=pr_payload,
        github_gateway=build_github_gateway(),
    )

    assert result.allowed is False
    assert result.ready_to_execute is False
