"""Live-preview helpers: uncompressed RTSP frames, no extra JPEG encode."""

import os
import shutil
import sys
from pathlib import Path

PREVIEW_WIDTH = 1280
# Dwarf 3 tele (ch0) HEVC does not emit a decodable frame for ~12s after connect.
# Socket idle timeout must be longer than that keyframe gap.
RTSP_SOCKET_TIMEOUT_US = "30000000"
RTSP_FIRST_FRAME_TIMEOUT = 45
# Wait for RTSP/HTTP to bind after photo mode before starting ffmpeg.
STREAM_PORT_WAIT = 12
PREVIEW_FRAME_INTERVAL = 0.05


def should_enter_live_preview_mode(*, live_mode, lens_switch):
    """GO LIVE + photo mode on first live entry, not when only switching lens."""
    return bool(live_mode) and not lens_switch


def should_open_camera_on_preview_event(*, live_mode, lens_switch, stream_up, rtsp_live=False):
    """OPEN CAMERA is Dwarf II only. Dwarf 3/Mini photo mode already starts RTSP.

    Both Dwarf 3 channels already publish (ch0 tele, ch1 wide). OPEN TELE PHOTO
    can hang after photo mode and can reset the encoder mid-connect.
    """
    if rtsp_live or lens_switch:
        return False
    return bool(live_mode) and not stream_up


def should_start_preview_on_lens_toggle(*, connected, busy, clicks_blocked):
    """Restart preview on a lens click even if the previous pull has stopped."""
    return bool(connected) and not busy and not clicks_blocked


def find_ffmpeg():
    """Return a usable ffmpeg executable, including one shipped with the app.

    Frozen Windows builds do not put the install folder on PATH, and Python 3.12
    no longer lets shutil.which() find ffmpeg.exe in the current directory.
    """
    for env_name in ("ASTRO_DWARF_FFMPEG", "FFMPEG_BINARY", "IMAGEIO_FFMPEG_EXE"):
        value = os.environ.get(env_name, "").strip().strip('"')
        if not value:
            continue
        path = Path(value)
        if path.is_file():
            return str(path)
        found = shutil.which(value)
        if found:
            return found

    names = ("ffmpeg.exe", "ffmpeg") if os.name == "nt" else ("ffmpeg",)
    seen = set()
    for directory in _ffmpeg_candidate_dirs():
        try:
            resolved = directory.resolve()
        except Exception:
            continue
        if resolved in seen or not resolved.is_dir():
            continue
        seen.add(resolved)
        for name in names:
            candidate = resolved / name
            if candidate.is_file():
                return str(candidate)

    return shutil.which("ffmpeg") or (
        shutil.which("ffmpeg.exe") if os.name == "nt" else None
    )


def _ffmpeg_candidate_dirs():
    dirs = []
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        dirs.extend((exe_dir, exe_dir / "ffmpeg", exe_dir / "bin", exe_dir / "lib"))
        if sys.platform == "darwin":
            dirs.append(exe_dir.parent / "Resources")
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            dirs.append(Path(meipass))
    else:
        root = Path(__file__).resolve().parent
        dirs.extend((root, root / "vendor" / "ffmpeg", root / "ffmpeg", root / "bin"))

    if os.name == "nt":
        dirs.extend(_windows_ffmpeg_dirs())
    else:
        dirs.extend(
            (
                Path("/opt/homebrew/bin"),
                Path("/usr/local/bin"),
                Path("/usr/bin"),
            )
        )
    return dirs


def _windows_ffmpeg_dirs():
    local = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    program_data = os.environ.get("ProgramData", r"C:\ProgramData")
    home = Path.home()
    dirs = [
        Path(r"C:\ffmpeg\bin"),
        Path(program_files) / "ffmpeg" / "bin",
        Path(program_files_x86) / "ffmpeg" / "bin",
        Path(program_data) / "chocolatey" / "bin",
        home / "scoop" / "shims",
        home / "scoop" / "apps" / "ffmpeg" / "current" / "bin",
    ]
    if local:
        dirs.append(Path(local) / "Microsoft" / "WinGet" / "Links")
    dirs.extend(_windows_registry_path_dirs())
    return dirs


def _windows_registry_path_dirs():
    try:
        import winreg
    except ImportError:
        return []

    dirs = []
    keys = (
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        (winreg.HKEY_CURRENT_USER, "Environment"),
    )
    for root, subkey in keys:
        try:
            with winreg.OpenKey(root, subkey) as handle:
                value, _ = winreg.QueryValueEx(handle, "Path")
        except OSError:
            continue
        dirs.extend(Path(part) for part in str(value).split(os.pathsep) if part.strip())
    return dirs


def rtsp_raw_ffmpeg_command(ffmpeg, url, transport, width=PREVIEW_WIDTH):
    """Decode RTSP to scaled uncompressed PPM frames on stdout.

    Low-delay flags match the faster Dwarf live path: small probe window so
    ffmpeg starts decoding instead of analysing, TCP first like VLC, then PPM
    so this app does not re-encode JPEG. Do not use the fps filter: Dwarf RTSP
    timestamps are often unusable, so fps= would drop every frame.
    """
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-an",
        "-fflags",
        "+nobuffer+discardcorrupt",
        "-flags",
        "low_delay",
        "-probesize",
        "512k",
        "-analyzeduration",
        "500000",
        "-rtsp_transport",
        transport,
        "-timeout",
        RTSP_SOCKET_TIMEOUT_US,
        "-i",
        url,
        "-vf",
        f"scale={width}:-2",
        "-f",
        "image2pipe",
        "-vcodec",
        "ppm",
        "pipe:1",
    ]


def split_ppm_frame(data):
    """Return (one_ppm_frame, remainder) or (None, data) if incomplete."""
    start = data.find(b"P6")
    if start == -1:
        return None, b""
    if start:
        data = data[start:]
    index = 2
    width, index = _ppm_read_int(data, index)
    if width is None:
        return None, data
    height, index = _ppm_read_int(data, index)
    if height is None:
        return None, data
    maxval, index = _ppm_read_int(data, index)
    if maxval is None:
        return None, data
    if index >= len(data):
        return None, data
    index += 1
    sample_bytes = 2 if maxval > 255 else 1
    payload = width * height * 3 * sample_bytes
    end = index + payload
    if len(data) < end:
        return None, data
    return data[:end], data[end:]


def _ppm_read_int(data, index):
    while index < len(data):
        byte = data[index]
        if byte == 35:
            newline = data.find(b"\n", index)
            if newline == -1:
                return None, 0
            index = newline + 1
            continue
        if byte in b" \t\r\n":
            index += 1
            continue
        break
    else:
        return None, 0
    start = index
    while index < len(data) and 48 <= data[index] <= 57:
        index += 1
    if index == start or index == len(data):
        return None, 0
    return int(data[start:index]), index
