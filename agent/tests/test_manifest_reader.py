from pathlib import Path

import pytest

from agent.sre_agent.manifest_reader import read_manifest


def test_read_manifest_returns_yaml_object(tmp_path: Path):
    manifest = tmp_path / "pod.yaml"
    manifest.write_text(
        """
apiVersion: v1
kind: Pod
metadata:
  name: demo
spec:
  containers:
    - name: app
      image: nginx:1.27
""".strip(),
        encoding="utf-8",
    )

    data = read_manifest(str(manifest))

    assert data["kind"] == "Pod"
    assert data["metadata"]["name"] == "demo"
    assert data["spec"]["containers"][0]["image"] == "nginx:1.27"


def test_read_manifest_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        read_manifest("does-not-exist.yaml")


def test_read_manifest_rejects_non_mapping_yaml(tmp_path: Path):
    manifest = tmp_path / "invalid.yaml"
    manifest.write_text(
        """
- one
- two
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        read_manifest(str(manifest))
