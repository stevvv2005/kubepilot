from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Callable, Optional, Protocol, TypeVar
from uuid import uuid4

from agent.sre_agent.candidate_value import CandidateValue
from agent.sre_agent.patch_proposal import PatchProposal


class RemediationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"


@dataclass(frozen=True)
class AuditEntry:
    event: str
    remediation_id: str
    timestamp: str
    metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class RemediationRecord:
    remediation_id: str
    patch_proposal: PatchProposal
    candidate_value: CandidateValue
    namespace: str
    pod_name: str
    container_name: str
    diagnosis: str
    evidence: tuple[str, ...]
    created_at: str
    status: RemediationStatus = RemediationStatus.PENDING
    approved_value: Optional[str] = None
    reviewer_id: Optional[str] = None
    reviewer_name: Optional[str] = None
    decision_timestamp: Optional[str] = None
    source: Optional[str] = None
    rejection_reason: Optional[str] = None
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None


@dataclass(frozen=True)
class DecisionResult:
    record: RemediationRecord
    idempotent: bool


class UnknownRemediationError(LookupError):
    pass


class InvalidRemediationTransitionError(RuntimeError):
    pass


T = TypeVar("T")


class ApprovalRepository(Protocol):
    def create(self, record: RemediationRecord) -> RemediationRecord:
        ...

    def get(self, remediation_id: str) -> RemediationRecord:
        ...

    def decide(
        self,
        *,
        remediation_id: str,
        approved: bool,
        approved_value: Optional[str],
        reviewer_id: str,
        reviewer_name: str,
        rejection_reason: Optional[str],
        audit_metadata: tuple[tuple[str, str], ...] = (),
    ) -> DecisionResult:
        ...

    def execute_once(
        self,
        remediation_id: str,
        operation: Callable[[], T],
    ) -> tuple[RemediationRecord, Optional[T], bool]:
        ...

    def record_audit(
        self,
        event: str,
        remediation_id: str,
        metadata: tuple[tuple[str, str], ...] = (),
    ) -> None:
        ...

    def audit_entries(self) -> tuple[AuditEntry, ...]:
        ...


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_remediation_id() -> str:
    return f"rem_{uuid4().hex}"


class InMemoryApprovalRepository:
    """Thread-safe demo repository with atomic decision/execution guards."""

    def __init__(self) -> None:
        self._records: dict[str, RemediationRecord] = {}
        self._audit: list[AuditEntry] = []
        self._lock = RLock()

    def create(self, record: RemediationRecord) -> RemediationRecord:
        with self._lock:
            if record.remediation_id in self._records:
                return self._records[record.remediation_id]
            self._records[record.remediation_id] = record
            self._append_audit("remediation_created", record.remediation_id)
            return record

    def get(self, remediation_id: str) -> RemediationRecord:
        with self._lock:
            try:
                return self._records[remediation_id]
            except KeyError as exc:
                raise UnknownRemediationError(
                    "Unknown remediation_id."
                ) from exc

    def decide(
        self,
        *,
        remediation_id: str,
        approved: bool,
        approved_value: Optional[str],
        reviewer_id: str,
        reviewer_name: str,
        rejection_reason: Optional[str],
        audit_metadata: tuple[tuple[str, str], ...] = (),
    ) -> DecisionResult:
        with self._lock:
            record = self.get(remediation_id)
            desired = (
                RemediationStatus.APPROVED
                if approved
                else RemediationStatus.REJECTED
            )

            if record.status == desired or (
                approved and record.status == RemediationStatus.EXECUTED
            ):
                self._append_audit(
                    "duplicate_callback_blocked",
                    remediation_id,
                    audit_metadata,
                )
                return DecisionResult(record=record, idempotent=True)

            if record.status != RemediationStatus.PENDING:
                self._append_audit(
                    "invalid_transition_blocked",
                    remediation_id,
                    audit_metadata,
                )
                raise InvalidRemediationTransitionError(
                    f"Cannot change remediation from {record.status.value} "
                    f"to {desired.value}."
                )

            updated = replace(
                record,
                status=desired,
                approved_value=approved_value if approved else None,
                reviewer_id=reviewer_id,
                reviewer_name=reviewer_name,
                decision_timestamp=utc_now(),
                source="slack",
                rejection_reason=(None if approved else rejection_reason),
            )
            self._records[remediation_id] = updated
            self._append_audit(
                "approval_recorded" if approved else "rejection_recorded",
                remediation_id,
                audit_metadata,
            )
            return DecisionResult(record=updated, idempotent=False)

    def execute_once(
        self,
        remediation_id: str,
        operation: Callable[[], T],
    ) -> tuple[RemediationRecord, Optional[T], bool]:
        # The lock intentionally spans the external operation. This simple local
        # repository trades throughput for an atomic no-duplicate-PR guarantee.
        with self._lock:
            record = self.get(remediation_id)
            if record.status == RemediationStatus.EXECUTED:
                self._append_audit(
                    "duplicate_execution_blocked",
                    remediation_id,
                )
                return record, None, True
            if record.status != RemediationStatus.APPROVED:
                raise InvalidRemediationTransitionError(
                    "Only an approved remediation may be executed."
                )

            self._append_audit("github_execution_authorized", remediation_id)
            try:
                result = operation()
            except Exception:
                self._append_audit("github_execution_failed", remediation_id)
                raise

            updated = replace(
                record,
                status=RemediationStatus.EXECUTED,
                pr_number=getattr(result, "pr_number", None),
                pr_url=getattr(result, "pr_url", None),
            )
            self._records[remediation_id] = updated
            self._append_audit("pr_created", remediation_id)
            return updated, result, False

    def record_audit(
        self,
        event: str,
        remediation_id: str,
        metadata: tuple[tuple[str, str], ...] = (),
    ) -> None:
        with self._lock:
            self._append_audit(event, remediation_id, metadata)

    def audit_entries(self) -> tuple[AuditEntry, ...]:
        with self._lock:
            return tuple(self._audit)

    def _append_audit(
        self,
        event: str,
        remediation_id: str,
        metadata: tuple[tuple[str, str], ...] = (),
    ) -> None:
        self._audit.append(
            AuditEntry(
                event=event,
                remediation_id=remediation_id,
                timestamp=utc_now(),
                metadata=metadata,
            )
        )
