import subprocess
from dataclasses import dataclass
from typing import List


ALLOWED_COMMANDS = {"get", "describe", "logs"}


@dataclass(frozen=True)
class CommandResult:
    command: List[str]
    stdout: str
    stderr: str
    returncode: int


def run_kubectl(args: List[str]) -> CommandResult:
    """
    Execute a read-only kubectl command.

    Allowed operations:
    - get
    - describe
    - logs

    Any write operation is rejected.
    """

    if not args:
        raise ValueError("kubectl arguments cannot be empty")

    operation = args[0]

    if operation not in ALLOWED_COMMANDS:
        raise ValueError(
            f"kubectl operation '{operation}' is not allowed. "
            f"Allowed operations: {sorted(ALLOWED_COMMANDS)}"
        )

    command = ["kubectl", *args]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    return CommandResult(
        command=command,
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )

import json

from agent.sre_agent.diagnostic import IncidentContext


def get_pod_incident_context(
    namespace: str,
    pod_name: str,
    container_name: str,
) -> IncidentContext:
    """
    Read pod state from Kubernetes and convert it into IncidentContext.
    """

    result = run_kubectl([
        "get",
        "pod",
        pod_name,
        "-n",
        namespace,
        "-o",
        "json",
    ])

    if result.returncode != 0:
        raise RuntimeError(
            f"Unable to read pod '{pod_name}': {result.stderr.strip()}"
        )

    pod = json.loads(result.stdout)

    container_statuses = pod.get("status", {}).get("containerStatuses", [])

    target_status = next(
        (
            status
            for status in container_statuses
            if status.get("name") == container_name
        ),
        None,
    )

    if target_status is None:
        raise ValueError(
            f"Container '{container_name}' was not found in pod '{pod_name}'."
        )

    state = target_status.get("state", {})
    last_state = target_status.get("lastState", {})

    waiting_reason = state.get("waiting", {}).get("reason")

    raw_terminated_reason = (
    state.get("terminated", {}).get("reason")
    or last_state.get("terminated", {}).get("reason")
    )

    terminated_reason = (
       raw_terminated_reason
       if raw_terminated_reason not in {None, "", "Unknown", "Completed"}
       else None
    )

    restart_count = target_status.get("restartCount", 0)

    conditions = pod.get("status", {}).get("conditions", [])

    readiness_failed = any(
        condition.get("type") == "Ready"
        and condition.get("status") == "False"
        for condition in conditions
    )

    return IncidentContext(
        namespace=namespace,
        pod_name=pod_name,
        container_name=container_name,
        waiting_reason=waiting_reason,
        terminated_reason=terminated_reason,
        restart_count=restart_count,
        readiness_failed=readiness_failed,
    )
