from pathlib import Path
from typing import Any, Dict

import yaml


def read_manifest(path: str) -> Dict[str, Any]:
    """
    Read a Kubernetes YAML manifest from disk.

    This function is read-only:
    - it does not modify the file
    - it does not apply anything to Kubernetes
    - it only returns the parsed YAML content
    """

    manifest_path = Path(path)

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")

    if not manifest_path.is_file():
        raise ValueError(f"Manifest path is not a file: {path}")

    with manifest_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Manifest must contain a YAML object: {path}")

    return data
