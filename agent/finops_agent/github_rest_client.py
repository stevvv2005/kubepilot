import base64
import json
from dataclasses import dataclass
from typing import Callable
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class GitHubRESTConfig:
    token: str
    api_url: str = "https://api.github.com"
    timeout_seconds: float = 10.0


class GitHubRESTClient:
    """
    Minimal GitHub REST client used by the
    controlled FinOps GitOps execution path.

    This client can write to GitHub.
    It never writes directly to Kubernetes.
    """

    def __init__(
        self,
        *,
        config: GitHubRESTConfig,
        opener: Callable = urlopen,
    ):
        token = config.token.strip()

        if not token:
            raise ValueError(
                "GitHub token is required."
            )

        self._config = config
        self._token = token
        self._opener = opener

    def _request(
        self,
        *,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> dict:
        url = (
            self._config.api_url.rstrip("/")
            + path
        )

        data = None

        if payload is not None:
            data = json.dumps(
                payload
            ).encode("utf-8")

        request = Request(
            url=url,
            data=data,
            method=method,
            headers={
                "Accept": (
                    "application/vnd.github+json"
                ),
                "Authorization": (
                    f"Bearer {self._token}"
                ),
                "X-GitHub-Api-Version": (
                    "2022-11-28"
                ),
                "User-Agent": "kubepilot",
                "Content-Type": (
                    "application/json"
                ),
            },
        )

        try:
            response = self._opener(
                request,
                timeout=(
                    self._config
                    .timeout_seconds
                ),
            )

            raw = response.read()

        except HTTPError as exc:
            raise RuntimeError(
                "GitHub API request failed "
                f"with HTTP {exc.code}."
            ) from exc

        if not raw:
            return {}

        payload = json.loads(
            raw.decode("utf-8")
        )

        if not isinstance(payload, dict):
            raise RuntimeError(
                "GitHub API returned an "
                "unexpected response."
            )

        return payload

    def get_branch_sha(
        self,
        *,
        repository: str,
        branch: str,
    ) -> str:
        repository = repository.strip()
        branch = branch.strip()

        if not repository:
            raise ValueError(
                "Repository is required."
            )

        if not branch:
            raise ValueError(
                "Branch is required."
            )

        encoded_branch = quote(
            branch,
            safe="",
        )

        payload = self._request(
            method="GET",
            path=(
                f"/repos/{repository}/git/ref/"
                f"heads/{encoded_branch}"
            ),
        )

        sha = (
            payload
            .get("object", {})
            .get("sha")
        )

        if not isinstance(sha, str):
            raise RuntimeError(
                "GitHub branch SHA is missing."
            )

        if not sha.strip():
            raise RuntimeError(
                "GitHub branch SHA is empty."
            )

        return sha

    def create_branch(
        self,
        *,
        repository: str,
        branch: str,
        source_sha: str,
    ) -> None:
        if not branch.startswith(
            "fix/finops-"
        ):
            raise ValueError(
                "GitHub branch is outside "
                "the FinOps branch policy."
            )

        if not source_sha.strip():
            raise ValueError(
                "Source SHA is required."
            )

        self._request(
            method="POST",
            path=(
                f"/repos/{repository}/git/refs"
            ),
            payload={
                "ref": (
                    f"refs/heads/{branch}"
                ),
                "sha": source_sha,
            },
        )

    def _get_file_sha(
        self,
        *,
        repository: str,
        branch: str,
        path: str,
    ) -> str:
        encoded_path = quote(
            path,
            safe="/",
        )

        encoded_branch = quote(
            branch,
            safe="",
        )

        payload = self._request(
            method="GET",
            path=(
                f"/repos/{repository}/contents/"
                f"{encoded_path}"
                f"?ref={encoded_branch}"
            ),
        )

        sha = payload.get("sha")

        if not isinstance(sha, str):
            raise RuntimeError(
                "GitHub file SHA is missing."
            )

        if not sha.strip():
            raise RuntimeError(
                "GitHub file SHA is empty."
            )

        return sha

    def update_file(
        self,
        *,
        repository: str,
        branch: str,
        path: str,
        content: str,
        message: str,
    ) -> str:
        if not branch.startswith(
            "fix/finops-"
        ):
            raise ValueError(
                "GitHub branch is outside "
                "the FinOps branch policy."
            )

        if not path.strip():
            raise ValueError(
                "Target file is required."
            )

        if not content.strip():
            raise ValueError(
                "File content is required."
            )

        if not message.strip():
            raise ValueError(
                "Commit message is required."
            )

        file_sha = self._get_file_sha(
            repository=repository,
            branch=branch,
            path=path,
        )

        encoded_content = (
            base64.b64encode(
                content.encode("utf-8")
            )
            .decode("ascii")
        )

        encoded_path = quote(
            path,
            safe="/",
        )

        payload = self._request(
            method="PUT",
            path=(
                f"/repos/{repository}/contents/"
                f"{encoded_path}"
            ),
            payload={
                "message": message,
                "content": encoded_content,
                "branch": branch,
                "sha": file_sha,
            },
        )

        commit_sha = (
            payload
            .get("commit", {})
            .get("sha")
        )

        if not isinstance(
            commit_sha,
            str,
        ):
            raise RuntimeError(
                "GitHub commit SHA is missing."
            )

        if not commit_sha.strip():
            raise RuntimeError(
                "GitHub commit SHA is empty."
            )

        return commit_sha

    def create_pull_request(
        self,
        *,
        repository: str,
        base_branch: str,
        head_branch: str,
        title: str,
        body: str,
    ) -> tuple[int, str]:
        if not head_branch.startswith(
            "fix/finops-"
        ):
            raise ValueError(
                "GitHub PR head branch is outside "
                "the FinOps branch policy."
            )

        if head_branch == base_branch:
            raise ValueError(
                "GitHub PR head branch must "
                "differ from base branch."
            )

        payload = self._request(
            method="POST",
            path=(
                f"/repos/{repository}/pulls"
            ),
            payload={
                "title": title,
                "body": body,
                "head": head_branch,
                "base": base_branch,
            },
        )

        number = payload.get("number")
        html_url = payload.get("html_url")

        if not isinstance(number, int):
            raise RuntimeError(
                "GitHub PR number is missing."
            )

        if not isinstance(html_url, str):
            raise RuntimeError(
                "GitHub PR URL is missing."
            )

        return number, html_url