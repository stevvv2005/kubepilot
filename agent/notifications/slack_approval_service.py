from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from agent.notifications.slack_approval_repository import (
    ApprovalRepository,
    DecisionResult,
    RemediationRecord,
    RemediationStatus,
    new_remediation_id,
    utc_now,
)
from agent.sre_agent.approved_manifest import render_approved_manifest
from agent.sre_agent.candidate_value import CandidateValue
from agent.sre_agent.git_commit_dry_run import build_git_commit_dry_run
from agent.sre_agent.git_execution_gateway import validate_git_execution
from agent.sre_agent.git_execution_request import build_git_execution_request
from agent.sre_agent.git_executor import execute_git_request
from agent.sre_agent.github_execution_gateway import (
    validate_sre_github_execution,
)
from agent.sre_agent.github_pr import validate_pr_payload_for_github
from agent.sre_agent.github_pr_executor import (
    SREGitHubPRExecutionResult,
    SREGitHubRepositoryClient,
    execute_sre_github_pr_request,
)
from agent.sre_agent.github_request import build_github_pr_request
from agent.sre_agent.human_approval import (
    HumanApprovalDecision,
    apply_human_approval,
)
from agent.sre_agent.patch_proposal import PatchProposal
from agent.sre_agent.pr_payload import build_pr_payload


@dataclass(frozen=True)
class SlackApprovalResult:
    remediation_id: str
    status: str
    approved: bool
    approved_value: Optional[str]
    reviewer_id: str
    reviewer_name: str
    source: str
    rejection_reason: Optional[str]
    idempotent: bool
    live_authorized: bool
    execution_blocked: bool
    executed: bool
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    performs_cluster_write: bool = False
    auto_merge: bool = False


class SlackApprovalService:
    def __init__(
        self,
        repository: ApprovalRepository,
        *,
        repository_root: str | Path = ".",
        github_client_factory: Optional[
            Callable[[], SREGitHubRepositoryClient]
        ] = None,
    ) -> None:
        self.repository = repository
        self.repository_root = Path(repository_root)
        self.github_client_factory = github_client_factory

    def register_remediation(
        self,
        *,
        patch_proposal: PatchProposal,
        candidate_value: CandidateValue,
        namespace: str,
        pod_name: str,
        container_name: str,
        diagnosis: str,
        evidence: tuple[str, ...],
    ) -> RemediationRecord:
        record = RemediationRecord(
            remediation_id=new_remediation_id(),
            patch_proposal=patch_proposal,
            candidate_value=candidate_value,
            namespace=namespace,
            pod_name=pod_name,
            container_name=container_name,
            diagnosis=diagnosis,
            evidence=evidence,
            created_at=utc_now(),
        )
        return self.repository.create(record)

    def mark_notification_sent(
        self,
        remediation_id: str,
        *,
        dry_run: bool,
    ) -> None:
        self.repository.record_audit(
            "slack_notification_sent",
            remediation_id,
            (("dry_run", str(dry_run).lower()),),
        )

    def process_action(
        self,
        *,
        remediation_id: str,
        action: str,
        reviewer_id: str,
        reviewer_name: str,
        rejection_reason: Optional[str],
        live_authorized: bool,
        audit_metadata: tuple[tuple[str, str], ...] = (),
    ) -> SlackApprovalResult:
        record = self.repository.get(remediation_id)
        approved = action == "approve"

        if action not in {"approve", "reject"}:
            raise ValueError("Unsupported Slack approval action.")

        if approved and not record.candidate_value.candidate_value:
            raise ValueError(
                "This remediation has no trusted server-side candidate value."
            )

        decision = self.repository.decide(
            remediation_id=remediation_id,
            approved=approved,
            approved_value=(
                record.candidate_value.candidate_value if approved else None
            ),
            reviewer_id=reviewer_id,
            reviewer_name=reviewer_name,
            rejection_reason=rejection_reason,
            audit_metadata=audit_metadata,
        )

        if not approved:
            return self._result(
                decision,
                live_authorized=live_authorized,
                execution_blocked=False,
            )

        execution_request = self._build_execution_request(decision.record)

        if not live_authorized:
            # Preserve a complete dry-run result while blocking all GitHub writes.
            execute_git_request(request=execution_request, dry_run=True)
            return self._result(
                decision,
                live_authorized=False,
                execution_blocked=True,
            )

        live_gateway = validate_sre_github_execution(
            request=execution_request,
            live_authorized=True,
        )
        if not live_gateway.allowed or not live_gateway.ready_to_execute:
            raise ValueError(live_gateway.reason)

        if self.github_client_factory is None:
            raise ValueError("GitHub client is not configured.")

        def execute() -> SREGitHubPRExecutionResult:
            return execute_sre_github_pr_request(
                request=execution_request,
                client=self.github_client_factory(),
                live_authorized=True,
            )

        updated, execution_result, duplicate = self.repository.execute_once(
            remediation_id,
            execute,
        )
        return SlackApprovalResult(
            remediation_id=remediation_id,
            status=updated.status.value,
            approved=True,
            approved_value=updated.approved_value,
            reviewer_id=updated.reviewer_id or reviewer_id,
            reviewer_name=updated.reviewer_name or reviewer_name,
            source=updated.source or "slack",
            rejection_reason=updated.rejection_reason,
            idempotent=decision.idempotent or duplicate,
            live_authorized=True,
            execution_blocked=False,
            executed=updated.status == RemediationStatus.EXECUTED,
            pr_number=(
                execution_result.pr_number
                if execution_result is not None
                else updated.pr_number
            ),
            pr_url=(
                execution_result.pr_url
                if execution_result is not None
                else updated.pr_url
            ),
        )

    def _build_execution_request(self, record: RemediationRecord):
        reviewed_patch = apply_human_approval(
            patch_proposal=record.patch_proposal,
            candidate_value=record.candidate_value,
            decision=HumanApprovalDecision(
                approved=True,
                approved_value=record.approved_value,
                reviewer=record.reviewer_id or "",
                reason="Approved through verified Slack interaction.",
            ),
        )
        approved_manifest = render_approved_manifest(
            reviewed_patch=reviewed_patch,
            repository_root=self.repository_root,
        )
        pr_payload = build_pr_payload(reviewed_patch=reviewed_patch)
        github_gateway = validate_pr_payload_for_github(payload=pr_payload)
        github_request = build_github_pr_request(
            repository="stevvv2005/kubepilot",
            base_branch="main",
            payload=pr_payload,
            gateway=github_gateway,
        )
        commit_plan = build_git_commit_dry_run(
            approved_manifest=approved_manifest,
            pr_payload=pr_payload,
        )
        execution_gateway = validate_git_execution(
            commit_plan=commit_plan,
            pr_payload=pr_payload,
            github_gateway=github_gateway,
        )
        return build_git_execution_request(
            commit_plan=commit_plan,
            execution_gateway=execution_gateway,
            github_request=github_request,
        )

    @staticmethod
    def _result(
        decision: DecisionResult,
        *,
        live_authorized: bool,
        execution_blocked: bool,
    ) -> SlackApprovalResult:
        record = decision.record
        return SlackApprovalResult(
            remediation_id=record.remediation_id,
            status=record.status.value,
            approved=record.status in {
                RemediationStatus.APPROVED,
                RemediationStatus.EXECUTED,
            },
            approved_value=record.approved_value,
            reviewer_id=record.reviewer_id or "",
            reviewer_name=record.reviewer_name or "",
            source=record.source or "slack",
            rejection_reason=record.rejection_reason,
            idempotent=decision.idempotent,
            live_authorized=live_authorized,
            execution_blocked=execution_blocked,
            executed=record.status == RemediationStatus.EXECUTED,
            pr_number=record.pr_number,
            pr_url=record.pr_url,
        )
