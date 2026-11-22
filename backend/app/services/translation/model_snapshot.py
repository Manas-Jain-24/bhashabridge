"""Verify operator-provisioned Hugging Face snapshots before loading them."""

import hashlib
import json
import re
from pathlib import Path

from app.core.config import settings


def sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def model_snapshot(checkpoint: str) -> tuple[str, str | None, dict]:
    if settings.APP_ENV != "production":
        return checkpoint, None, {}
    manifest = settings.MODEL_MANIFEST
    if not manifest or sha256(manifest) != settings.MODEL_MANIFEST_SHA256:
        raise ValueError("No verified offline model manifest is available")
    entry = json.loads(manifest.read_text(encoding="utf-8"))["models"][checkpoint]
    base = manifest.parent.resolve()
    root = (base / entry["directory"]).resolve()
    if root == base or not root.is_relative_to(base) or not root.is_dir():
        raise ValueError("Model directory must be below the manifest directory")
    if not re.fullmatch(r"[a-f0-9]{40}", entry["revision"]):
        raise ValueError("Model revision must be a commit SHA")
    expected = entry["sha256"]
    files = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("Model files must be regular files")
        if path.is_file():
            files[path.relative_to(root).as_posix()] = path
    if (
        not expected
        or files.keys() != expected.keys()
        or not any(path.suffix == ".safetensors" for path in files.values())
    ):
        raise ValueError(
            "Model file list differs from the manifest or safe weights are missing"
        )
    for name, path in files.items():
        if sha256(path) != expected[name]:
            raise ValueError("Model file checksum mismatch")
        if path.suffix == ".json" and path.name in {
            "config.json",
            "tokenizer_config.json",
        }:
            mapping = json.loads(path.read_text(encoding="utf-8")).get("auto_map") or {}
            if "--" in json.dumps(mapping):
                raise ValueError("Model code must be in the verified snapshot")
    return str(root), entry["revision"], {"local_files_only": True}
