import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from video_preview import (
    RTSP_FIRST_FRAME_TIMEOUT,
    RTSP_SOCKET_TIMEOUT_US,
    find_ffmpeg,
    rtsp_raw_ffmpeg_command,
    should_enter_live_preview_mode,
    should_open_camera_on_preview_event,
    should_start_preview_on_lens_toggle,
    split_ppm_frame,
)


class FfmpegCommandTests(unittest.TestCase):
    def test_rtsp_command_is_uncompressed_ppm(self):
        cmd = rtsp_raw_ffmpeg_command("ffmpeg", "rtsp://192.168.1.1/ch0/stream0", "tcp")
        self.assertIn("ppm", cmd)
        self.assertNotIn("mjpeg", cmd)
        self.assertNotIn("-q:v", cmd)
        self.assertIn("scale=1280:-2", cmd)
        self.assertNotIn("fps=", "".join(cmd))
        self.assertIn("+nobuffer+discardcorrupt", cmd)
        self.assertEqual(cmd[cmd.index("-probesize") + 1], "512k")
        self.assertEqual(cmd[cmd.index("-analyzeduration") + 1], "500000")

    def test_socket_timeout_outlasts_tele_keyframe_gap(self):
        cmd = rtsp_raw_ffmpeg_command("ffmpeg", "rtsp://192.168.1.1/ch0/stream0", "tcp")
        timeout_us = int(cmd[cmd.index("-timeout") + 1])
        self.assertGreaterEqual(timeout_us, 12_000_000)
        self.assertEqual(timeout_us, int(RTSP_SOCKET_TIMEOUT_US))
        self.assertGreaterEqual(RTSP_FIRST_FRAME_TIMEOUT, 12)


class FindFfmpegTests(unittest.TestCase):
    _CLEAR_FFMPEG_ENV = {
        "ASTRO_DWARF_FFMPEG": "",
        "FFMPEG_BINARY": "",
        "IMAGEIO_FFMPEG_EXE": "",
    }

    def test_uses_explicit_env_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            ffmpeg = Path(tmp) / "ffmpeg.exe"
            ffmpeg.write_bytes(b"fake")
            env = dict(self._CLEAR_FFMPEG_ENV, ASTRO_DWARF_FFMPEG=str(ffmpeg))
            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch("video_preview.shutil.which", return_value=None):
                    self.assertEqual(Path(find_ffmpeg()).resolve(), ffmpeg.resolve())

    def test_finds_ffmpeg_next_to_frozen_exe(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe_dir = Path(tmp)
            exe = exe_dir / "astro_dwarf_session_UI.exe"
            ffmpeg = exe_dir / "ffmpeg.exe"
            exe.write_bytes(b"app")
            ffmpeg.write_bytes(b"ffmpeg")
            with mock.patch.object(sys, "frozen", True, create=True):
                with mock.patch.object(sys, "executable", str(exe)):
                    with mock.patch("video_preview.shutil.which", return_value=None):
                        with mock.patch.dict(os.environ, self._CLEAR_FFMPEG_ENV, clear=False):
                            self.assertEqual(Path(find_ffmpeg()).resolve(), ffmpeg.resolve())


class LensSwitchPolicyTests(unittest.TestCase):
    def test_lens_switch_does_not_open_camera(self):
        self.assertFalse(
            should_open_camera_on_preview_event(
                live_mode=False, lens_switch=True, stream_up=True
            )
        )
        self.assertFalse(
            should_open_camera_on_preview_event(
                live_mode=False, lens_switch=True, stream_up=False
            )
        )

    def test_first_live_opens_camera_only_if_stream_is_down(self):
        self.assertTrue(
            should_open_camera_on_preview_event(
                live_mode=True, lens_switch=False, stream_up=False
            )
        )
        self.assertFalse(
            should_open_camera_on_preview_event(
                live_mode=True, lens_switch=False, stream_up=True
            )
        )

    def test_dwarf3_does_not_open_camera_after_photo_mode(self):
        self.assertFalse(
            should_open_camera_on_preview_event(
                live_mode=True, lens_switch=False, stream_up=False, rtsp_live=True
            )
        )

    def test_first_live_enters_photo_mode_even_if_stream_looks_up(self):
        self.assertTrue(
            should_enter_live_preview_mode(live_mode=True, lens_switch=False)
        )
        self.assertFalse(
            should_enter_live_preview_mode(live_mode=True, lens_switch=True)
        )

    def test_lens_toggle_restarts_even_if_preview_has_stopped(self):
        self.assertTrue(
            should_start_preview_on_lens_toggle(
                connected=True, busy=False, clicks_blocked=False
            )
        )
        self.assertFalse(
            should_start_preview_on_lens_toggle(
                connected=False, busy=False, clicks_blocked=False
            )
        )


class PpmSplitTests(unittest.TestCase):
    def test_splits_complete_frame(self):
        pixels = bytes([10, 20, 30, 40, 50, 60, 70, 80, 90, 11, 12, 13])
        frame = b"P6\n2 2\n255\n" + pixels
        got, rest = split_ppm_frame(frame + b"P6 leftover")
        self.assertEqual(got, frame)
        self.assertEqual(rest, b"P6 leftover")

    def test_incomplete_frame_waits(self):
        header = b"P6\n2 2\n255\n"
        got, rest = split_ppm_frame(header + b"\x01\x02")
        self.assertIsNone(got)
        self.assertTrue(rest.startswith(b"P6"))

    def test_skips_junk_before_magic(self):
        pixels = bytes(12)
        frame = b"P6\n2 2\n255\n" + pixels
        got, rest = split_ppm_frame(b"xxxx" + frame)
        self.assertEqual(got, frame)
        self.assertEqual(rest, b"")

    def test_splits_bytearray_without_copying_incomplete_buffer(self):
        pixels = bytes(12)
        frame = b"P6\n2 2\n255\n" + pixels
        buf = bytearray(frame + b"rest")
        got, rest = split_ppm_frame(buf)
        self.assertEqual(bytes(got), frame)
        self.assertEqual(bytes(rest), b"rest")
