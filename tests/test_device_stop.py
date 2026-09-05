import time
import unittest

from device_stop import (
    can_start_action,
    is_user_stop_result,
    keep_action_until_stop_finishes,
    should_log_as_error,
    should_send_device_stop,
    stops_for,
)


class StopMappingTests(unittest.TestCase):
    def test_calibration_sends_stop_calibration_not_goto(self):
        self.assertEqual(stops_for("Calibration"), ("stop_calibration",))
        self.assertNotIn("stop_goto", stops_for("Calibration"))

    def test_polar_sends_motors_only(self):
        self.assertEqual(stops_for("Polar Position"), ("stop_motors",))

    def test_autofocus_and_eq(self):
        self.assertEqual(stops_for("Auto Focus"), ("stop_autofocus",))
        self.assertEqual(stops_for("EQ Solving"), ("stop_eq",))

    def test_imaging_session_includes_calibration(self):
        keys = stops_for(stop_imaging=True)
        self.assertIn("stop_calibration", keys)
        self.assertIn("stop_astro_photo", keys)
        self.assertIn("stop_goto", keys)

    def test_idle_preview_does_not_need_device_stop(self):
        self.assertFalse(should_send_device_stop(False, None))
        self.assertFalse(should_send_device_stop(False, ""))
        self.assertTrue(should_send_device_stop(True, None))
        self.assertTrue(should_send_device_stop(False, "Calibration"))


class ActionGatingTests(unittest.TestCase):
    def test_cannot_start_calibration_while_polar_stop_runs(self):
        ok, reason = can_start_action(
            current_action="Polar Position",
            stop_in_progress=True,
        )
        self.assertFalse(ok)
        self.assertIn("stop", reason)

    def test_cannot_start_while_stop_thread_is_the_only_blocker(self):
        ok, reason = can_start_action(stop_in_progress=True)
        self.assertFalse(ok)
        self.assertIn("stop", reason)

    def test_can_start_when_idle(self):
        ok, reason = can_start_action()
        self.assertTrue(ok)
        self.assertIsNone(reason)

    def test_end_action_keeps_name_until_stop_finishes(self):
        self.assertTrue(
            keep_action_until_stop_finishes(True, "Polar Position", "Polar Position")
        )
        self.assertFalse(
            keep_action_until_stop_finishes(False, "Polar Position", "Polar Position")
        )


class SimulatedPolarThenCalibrationRace(unittest.TestCase):
    """Replay the 15:18 log: polar stop must still block calibration."""

    def test_log_sequence_cannot_start_calibration(self):
        current = "Polar Position"
        stop_in_progress = True
        polar_thread_alive = False
        ok, _ = can_start_action(
            current_action=current,
            stop_in_progress=stop_in_progress,
            action_thread_alive=polar_thread_alive,
        )
        self.assertFalse(ok)

        current = None
        ok, _ = can_start_action(
            current_action=current,
            stop_in_progress=True,
            action_thread_alive=False,
        )
        self.assertFalse(ok)


class StopLogNoiseTests(unittest.TestCase):
    def test_interrupt_and_timeout_are_not_errors(self):
        self.assertTrue(is_user_stop_result(-10))
        self.assertTrue(is_user_stop_result(-5))
        self.assertFalse(should_log_as_error(-10))
        self.assertFalse(should_log_as_error(-5, stopping=True))
        self.assertFalse(should_log_as_error(False, stopping=True))
        self.assertTrue(should_log_as_error(False, stopping=False))
        self.assertTrue(should_log_as_error(-11504))


class StopTimeoutContractTests(unittest.TestCase):
    def test_stop_timeout_is_far_below_websocket_default(self):
        import ast
        from pathlib import Path

        text = Path("dwarf_python_api/lib/websockets_utils.py").read_text(encoding="utf-8")
        tree = ast.parse(text)
        values = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                    values[target.id] = node.value.value
        self.assertEqual(values["gb_timeout"], 150)
        self.assertEqual(values["STOP_CMD_TIMEOUT"], 8)
        self.assertLess(values["STOP_CMD_TIMEOUT"], 20)

    def test_dwarf_utils_stop_calls_use_short_timeout(self):
        from pathlib import Path

        text = Path("dwarf_python_api/lib/dwarf_utils.py").read_text(encoding="utf-8")
        self.assertIn("timeout=STOP_CMD_TIMEOUT", text)
        for needle in (
            "CMD_ASTRO_STOP_CALIBRATION",
            "CMD_FOCUS_STOP_ASTRO_AUTO_FOCUS",
            "CMD_ASTRO_STOP_EQ_SOLVING",
            "CMD_STEP_MOTOR_STOP",
            "CMD_ASTRO_STOP_GOTO",
        ):
            self.assertIn(needle, text)
        self.assertGreaterEqual(text.count("timeout=STOP_CMD_TIMEOUT"), 7)

    def test_get_result_timeout_returns_before_150s(self):
        try:
            import asyncio
            from dwarf_python_api.lib.websockets_utils import ERROR_TIMEOUT, get_result_with_timeout
        except ImportError as exc:
            self.skipTest(f"dwarf_python_api import failed: {exc}")

        async def run():
            queue = asyncio.Queue()
            started = time.perf_counter()
            result = await get_result_with_timeout(queue, timeout=0.4)
            elapsed = time.perf_counter() - started
            return result, elapsed

        result, elapsed = asyncio.run(run())
        self.assertLess(elapsed, 2.0)
        self.assertEqual(result["code"], ERROR_TIMEOUT)


if __name__ == "__main__":
    unittest.main()
