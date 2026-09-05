import unittest

from video_preview import (
    RTSP_FIRST_FRAME_TIMEOUT,
    RTSP_SOCKET_TIMEOUT_US,
    rtsp_raw_ffmpeg_command,
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

    def test_socket_timeout_outlasts_tele_keyframe_gap(self):
        cmd = rtsp_raw_ffmpeg_command("ffmpeg", "rtsp://192.168.1.1/ch0/stream0", "tcp")
        timeout_us = int(cmd[cmd.index("-timeout") + 1])
        self.assertGreaterEqual(timeout_us, 12_000_000)
        self.assertEqual(timeout_us, int(RTSP_SOCKET_TIMEOUT_US))
        self.assertGreaterEqual(RTSP_FIRST_FRAME_TIMEOUT, 12)


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
