"""Live-preview helpers: uncompressed RTSP frames, no extra JPEG encode."""

PREVIEW_WIDTH = 1280
# Dwarf 3 tele (ch0) HEVC does not emit a decodable frame for ~12s after connect.
# Socket idle timeout must be longer than that keyframe gap.
RTSP_SOCKET_TIMEOUT_US = "30000000"
RTSP_FIRST_FRAME_TIMEOUT = 45


def should_open_camera_on_preview_event(*, live_mode, lens_switch, stream_up):
    """Open the camera for first live entry, not when only switching RTSP URL.

    Both Dwarf 3 channels already publish (ch0 tele, ch1 wide). OPEN TELE PHOTO
    on a lens click is unnecessary and can reset the encoder mid-connect.
    """
    if lens_switch:
        return False
    return bool(live_mode) and not stream_up


def should_start_preview_on_lens_toggle(*, connected, busy, clicks_blocked):
    """Restart preview on a lens click even if the previous pull has stopped."""
    return bool(connected) and not busy and not clicks_blocked


def rtsp_raw_ffmpeg_command(ffmpeg, url, transport, width=PREVIEW_WIDTH):
    """Decode RTSP to scaled uncompressed PPM frames on stdout.

    Do not use the fps filter here: Dwarf RTSP timestamps are often unusable,
    so fps= would drop every frame even when VLC plays the same URL.
    """
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-fflags",
        "nobuffer",
        "-flags",
        "low_delay",
        "-rtsp_transport",
        transport,
        "-timeout",
        RTSP_SOCKET_TIMEOUT_US,
        "-i",
        url,
        "-an",
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
