import os
from pathlib import Path

from agent.finops_agent.git_execution_request import (
    FinOpsGitExecutionRequest,
)
from agent.finops_agent.github_execution_gateway import (
    validate_github_execution,
)
from agent.finops_agent.github_pr_executor import (
    execute_github_pr_request,
)
from agent.finops_agent.github_rest_client import (
    GitHubRESTClient,
    GitHubRESTConfig,
)


REPOSITORY = "stevvv2005/kubepilot"
BASE_BRANCH = "main"
HEAD_BRANCH = "fix/finops-live-validation"

TARGET_FILE = (
    "agent/tests/fixtures/"
    "github-live-validation.txt"
)


def main() -> None:
    token = os.getenv(
        "GITHUB_TOKEN",
        "",
    ).strip()

    live_authorized = (
        os.getenv(
            "KUBEPILOT_GITHUB_LIVE_AUTHORIZED",
            "",
        )
        .strip()
        .lower()
        == "true"
    )

    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN is not configured."
        )

    if not live_authorized:
        raise RuntimeError(
            "GitHub live execution is not authorized."
        )

    repository_root = Path(
        __file__
    ).resolve().parent.parent

    target_path = (
        repository_root
        / TARGET_FILE
    )

    if not target_path.exists():
        raise RuntimeError(
            f"Validation fixture not found: "
            f"{TARGET_FILE}"
        )

    current_content = (
        target_path.read_text(
            encoding="utf-8",
        )
        .rstrip()
    )

    validation_content = (
        current_content
        + "\n\n"
        + (
            "GitHub live execution validated through "
            "KubePilot controlled PR workflow.\n"
        )
    )

    request = FinOpsGitExecutionRequest(
        repository=REPOSITORY,
        base_branch=BASE_BRANCH,
        head_branch=HEAD_BRANCH,
        target_file=TARGET_FILE,
        commit_message=(
            "test(github): validate controlled "
            "live PR execution"
        ),
        rendered_yaml=validation_content,
        pr_title=(
            "test(github): validate controlled "
            "live PR execution"
        ),
        pr_body=(
            "## KubePilot GitHub Live Validation\n\n"
            "This Pull Request validates the controlled "
            "GitHub execution path.\n\n"
            "### Scope\n\n"
            "- Creates a dedicated `fix/finops-*` branch\n"
            "- Updates only the validation fixture\n"
            "- Creates a GitHub commit\n"
            "- Creates a Pull Request\n"
            "- Does not merge automatically\n"
            "- Does not modify Kubernetes\n"
            "- Does not run kubectl apply/patch/delete\n\n"
            "This PR is for integration validation only."
        ),
        create_branch=True,
        write_file=True,
        create_commit=True,
        push_branch=True,
        create_pr=True,
        authorized=True,
        performs_write=False,
    )

    gateway = validate_github_execution(
        request=request,
        live_authorized=live_authorized,
    )

    print(
        f"gateway.allowed="
        f"{gateway.allowed}"
    )

    print(
        f"gateway.ready_to_execute="
        f"{gateway.ready_to_execute}"
    )

    print(
        f"gateway.performs_cluster_write="
        f"{gateway.performs_cluster_write}"
    )

    if not gateway.allowed:
        raise RuntimeError(
            f"GitHub execution rejected: "
            f"{gateway.reason}"
        )

    if not gateway.ready_to_execute:
        raise RuntimeError(
            "GitHub gateway is not ready."
        )

    client = GitHubRESTClient(
        config=GitHubRESTConfig(
            token=token,
        )
    )

    result = execute_github_pr_request(
        request=request,
        client=client,
        live_authorized=live_authorized,
    )

    print()
    print("GitHub live execution result")
    print("----------------------------")

    print(
        f"repository="
        f"{result.repository}"
    )

    print(
        f"base_branch="
        f"{result.base_branch}"
    )

    print(
        f"head_branch="
        f"{result.head_branch}"
    )

    print(
        f"target_file="
        f"{result.target_file}"
    )

    print(
        f"commit_sha="
        f"{result.commit_sha}"
    )

    print(
        f"pr_number="
        f"{result.pr_number}"
    )

    print(
        f"pr_url="
        f"{result.pr_url}"
    )

    print(
        f"executed="
        f"{result.executed}"
    )

    print(
        f"performs_cluster_write="
        f"{result.performs_cluster_write}"
    )


if __name__ == "__main__":
    main()