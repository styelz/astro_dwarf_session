"""Download a Windows ffmpeg.exe to ship with frozen GUI builds."""

from __future__ import annotations

import os
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

VENDOR_DIR = Path(__file__).resolve().parent / "vendor" / "ffmpeg"
VENDOR_EXE = VENDOR_DIR / "ffmpeg.exe"

DOWNLOAD_URLS = (
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-lgpl.zip",
)
USER_AGENT = "AstroDwarfSession-build"
MIN_EXE_BYTES = 1_000_000


def bundled_ffmpeg_exe():
    """Return vendor/ffmpeg/ffmpeg.exe, downloading it on Windows if needed."""
    if _usable_vendor_exe():
        return VENDOR_EXE
    if sys.platform != "win32":
        return None

    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    last_error = None
    for url in DOWNLOAD_URLS:
        try:
            print(f"Downloading ffmpeg from {url}")
            _download_ffmpeg_exe(url, VENDOR_EXE)
            if _usable_vendor_exe():
                print(f"Bundled ffmpeg at {VENDOR_EXE}")
                return VENDOR_EXE
        except Exception as exc:
            last_error = exc
            print(f"ffmpeg download failed: {exc}")

    raise RuntimeError(
        "Could not download ffmpeg.exe for the Windows build. "
        f"Place a copy at {VENDOR_EXE}."
    ) from last_error


def _usable_vendor_exe():
    try:
        return VENDOR_EXE.is_file() and VENDOR_EXE.stat().st_size >= MIN_EXE_BYTES
    except OSError:
        return False


def _download_ffmpeg_exe(url, dest):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    tmp_zip = None
    try:
        with urlopen(request, timeout=300) as response:
            tmp_zip = _write_temp_zip(response)
        name = _ffmpeg_member_name(tmp_zip)
        dest_tmp = dest.with_suffix(".download")
        with zipfile.ZipFile(tmp_zip) as archive, archive.open(name) as src:
            with open(dest_tmp, "wb") as out:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
        os.replace(dest_tmp, dest)
    finally:
        if tmp_zip:
            try:
                os.unlink(tmp_zip)
            except OSError:
                pass


def _write_temp_zip(response):
    handle = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    try:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
        handle.close()
        return handle.name
    except Exception:
        handle.close()
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise


def _ffmpeg_member_name(zip_path):
    with zipfile.ZipFile(zip_path) as archive:
        names = [
            name
            for name in archive.namelist()
            if Path(name).name.lower() == "ffmpeg.exe" and not name.endswith("/")
        ]
    if not names:
        raise RuntimeError(f"No ffmpeg.exe found in {zip_path}")
    names.sort(key=lambda name: (0 if "/bin/" in name.replace("\\", "/").lower() else 1, len(name)))
    return names[0]
