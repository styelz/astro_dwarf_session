"""Resolve the product version for apps and packaging scripts."""

import os
import re
import sys
import tempfile
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


def _candidate_dirs():
    seen = set()

    def add(path):
        try:
            resolved = Path(path).resolve()
        except Exception:
            return
        if resolved in seen:
            return
        seen.add(resolved)
        yield resolved

    yield from add(Path(__file__).resolve().parent)

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        yield from add(exe_dir)
        yield from add(exe_dir / "lib")
        # py2app: Contents/MacOS/<exe> -> Contents/Resources
        yield from add(exe_dir.parent / "Resources")
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            yield from add(meipass)


def get_app_version() -> str:
    env_version = os.environ.get("APP_VERSION", "").strip()
    if env_version:
        return _normalize(env_version)

    last_error = None
    for directory in _candidate_dirs():
        version_file = directory / "VERSION"
        if version_file.is_file():
            try:
                return _normalize(version_file.read_text(encoding="utf-8").splitlines()[0])
            except Exception as exc:
                last_error = exc

        changelog = directory / "CHANGELOG.md"
        if changelog.is_file():
            try:
                return _version_from_changelog(changelog)
            except Exception as exc:
                last_error = exc

    if last_error:
        raise last_error
    raise ValueError("Unable to determine app version from VERSION or CHANGELOG.md")


def packaged_version_files():
    """Data files to ship with frozen builds so runtime version lookup works."""
    version_path = Path(tempfile.mkdtemp()) / "VERSION"
    version_path.write_text(get_app_version() + "\n", encoding="utf-8")
    files = [(str(version_path), "VERSION")]
    changelog = Path(__file__).resolve().parent / "CHANGELOG.md"
    if changelog.is_file():
        files.append((str(changelog), "CHANGELOG.md"))
    return files
