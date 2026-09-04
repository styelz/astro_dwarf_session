"""Resolve the product version for packaging scripts."""

import os
import re
from pathlib import Path

_CHANGELOG_HEADING = re.compile(r"^## \[([^\]]+)\]", re.MULTILINE)
_TWO_PART = re.compile(r"^\d+\.\d+$")
_THREE_PART = re.compile(r"^\d+\.\d+\.\d+$")


def _normalize(raw: str) -> str:
    version = raw.strip().lstrip("vV").strip()
    if _TWO_PART.fullmatch(version):
        version = f"{version}.0"
    if not _THREE_PART.fullmatch(version):
        raise ValueError(
            f"Invalid version '{raw}'. Expected digits.digits.digits (e.g. 1.7.7)."
        )
    return version


def _version_from_changelog(changelog_path: Path) -> str:
    text = changelog_path.read_text(encoding="utf-8")
    match = _CHANGELOG_HEADING.search(text)
    if not match:
        raise ValueError(f"No version heading found in {changelog_path}")
    return _normalize(match.group(1))


def get_app_version() -> str:
    env_version = os.environ.get("APP_VERSION", "").strip()
    if env_version:
        return _normalize(env_version)

    changelog_path = Path(__file__).resolve().parent / "CHANGELOG.md"
    return _version_from_changelog(changelog_path)
