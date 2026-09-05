import unittest

try:
    import tkinter as tk
except Exception:  # pragma: no cover
    tk = None

from ui.widgets import (
    VIDEO_ASPECT,
    OVERLAY_TOOLTIPS,
    VideoHoverOverlay,
    fit_image_in_box,
    largest_rect_for_aspect,
    stretch_image_to_box,
    work_area_rect,
)


class AspectGeometryTests(unittest.TestCase):
    def test_fits_wide_work_area(self):
        width, height = largest_rect_for_aspect(1920, 1200)
        self.assertEqual(width / height, VIDEO_ASPECT)
        self.assertEqual((width, height), (1920, 1080))

    def test_fits_tall_work_area(self):
        width, height = largest_rect_for_aspect(1600, 1200)
        self.assertAlmostEqual(width / height, VIDEO_ASPECT, places=5)
        self.assertLessEqual(width, 1600)
        self.assertLessEqual(height, 1200)

    def test_exact_16_by_9(self):
        self.assertEqual(largest_rect_for_aspect(1280, 720), (1280, 720))


class FitImageTests(unittest.TestCase):
    def setUp(self):
        try:
            from PIL import Image
        except Exception:
            self.skipTest("Pillow is required")
        self.Image = Image

    def test_output_matches_box_and_letterbox_keeps_source_aspect(self):
        image = self.Image.new("RGB", (320, 180), (10, 20, 30))
        fill = (1, 2, 3)
        fitted = fit_image_in_box(image, 640, 640, fill)
        self.assertEqual(fitted.size, (640, 640))
        self.assertEqual(fitted.getpixel((0, 0)), fill)
        self.assertEqual(fitted.getpixel((320, 10)), fill)
        self.assertEqual(fitted.getpixel((320, 320)), (10, 20, 30))

    def test_matching_size_keeps_source_pixels(self):
        image = self.Image.new("RGB", (640, 360), (10, 20, 30))
        fitted = fit_image_in_box(image, 640, 360, (1, 2, 3))
        self.assertEqual(fitted.size, (640, 360))
        self.assertEqual(fitted.getpixel((0, 0)), (10, 20, 30))
        self.assertIs(fitted, image)


    def test_stretch_fills_box_without_letterbox(self):
        image = self.Image.new("RGB", (320, 180), (10, 20, 30))
        stretched = stretch_image_to_box(image, 640, 640)
        self.assertEqual(stretched.size, (640, 640))
        self.assertEqual(stretched.getpixel((0, 0)), (10, 20, 30))
        self.assertEqual(stretched.getpixel((639, 639)), (10, 20, 30))


@unittest.skipIf(tk is None, "tkinter is required")
class OverlayHoverTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("no display")
        self.root.geometry("400x240")
        self.host = tk.Frame(self.root, width=320, height=180, bg="#000000")
        self.host.pack_propagate(False)
        self.host.pack()
        self.clicked = []
        self.overlay = VideoHoverOverlay(
            self.host,
            {
                "maximize": lambda: self.clicked.append("maximize"),
                "fullscreen": lambda: self.clicked.append("fullscreen"),
            },
            visible_kinds=("maximize", "fullscreen"),
            idle_hide_ms=3000,
        )
        self.root.update()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_overlay_is_hidden_until_hover(self):
        self.assertFalse(self.overlay.bar.winfo_ismapped())
        self.overlay.show()
        self.root.update_idletasks()
        self.assertTrue(self.overlay.bar.winfo_ismapped())
        self.overlay.hide()
        self.root.update_idletasks()
        self.assertFalse(self.overlay.bar.winfo_ismapped())

    def test_enter_shows_fullscreen_and_maximize_buttons(self):
        self.host.event_generate("<Enter>")
        self.root.update_idletasks()
        self.assertTrue(self.overlay.bar.winfo_ismapped())
        self.assertIn("fullscreen", self.overlay.buttons)
        self.assertIn("maximize", self.overlay.buttons)
        self.assertNotIn("restore", self.overlay.buttons)

    def test_lens_icon_shows_bottom_right_on_hover(self):
        clicked = []
        overlay = VideoHoverOverlay(
            self.host,
            {
                "maximize": lambda: None,
                "fullscreen": lambda: None,
                "lens": lambda: clicked.append("lens"),
            },
            visible_kinds=("maximize", "fullscreen", "lens"),
        )
        self.root.update()
        self.assertFalse(overlay.bottom_bar.winfo_ismapped())
        overlay.show()
        self.root.update_idletasks()
        self.assertTrue(overlay.bottom_bar.winfo_ismapped())
        self.assertIn("lens", overlay.buttons)
        self.assertGreaterEqual(overlay.bottom_bar.winfo_y(), overlay.bar.winfo_y())
        overlay.buttons["lens"].event_generate("<Button-1>")
        self.root.update()
        self.assertEqual(clicked, ["lens"])
        overlay.hide()
        self.root.update_idletasks()
        self.assertFalse(overlay.bottom_bar.winfo_ismapped())
        overlay.destroy()

    def test_overlay_buttons_are_separate(self):
        self.overlay.show()
        self.root.update()
        fullscreen = self.overlay.buttons["fullscreen"]
        maximize = self.overlay.buttons["maximize"]
        self.assertGreaterEqual(int(fullscreen.cget("highlightthickness")), 1)
        self.assertGreaterEqual(int(maximize.cget("highlightthickness")), 1)
        self.assertEqual(int(self.overlay.bar.cget("highlightthickness")), 0)
        padx = fullscreen.pack_info()["padx"]
        if isinstance(padx, (tuple, list)):
            gap = int(padx[0])
        else:
            gap = int(str(padx).replace("(", "").split(",")[0])
        self.assertGreaterEqual(gap, 4)
        self.assertGreater(fullscreen.winfo_x(), maximize.winfo_x() + maximize.winfo_width())

    def test_maximize_button_is_left_of_fullscreen(self):
        self.overlay.show()
        self.root.update()
        maximize = self.overlay.buttons["maximize"]
        fullscreen = self.overlay.buttons["fullscreen"]
        self.assertLess(maximize.winfo_x(), fullscreen.winfo_x())

    def test_icons_differ_for_maximize_and_fullscreen(self):
        fullscreen = self.overlay.buttons["fullscreen"]
        maximize = self.overlay.buttons["maximize"]
        self.assertGreater(len(fullscreen.find_all()), 0)
        self.assertGreater(len(maximize.find_all()), 0)
        self.assertNotEqual(len(fullscreen.find_all()), len(maximize.find_all()))
        self.assertLessEqual(int(fullscreen.cget("width")), 24)

    def test_attach_tooltips(self):
        attached = []

        class FakeTip:
            def __init__(self, widget, text):
                attached.append((widget, text))

        handles = self.overlay.attach_tooltips(FakeTip)
        self.assertEqual(len(handles), 2)
        texts = {text for _widget, text in attached}
        self.assertEqual(texts, {OVERLAY_TOOLTIPS["fullscreen"], OVERLAY_TOOLTIPS["maximize"]})

    def test_icon_click_runs_command(self):
        self.overlay.show()
        self.root.update()
        self.assertTrue(self.overlay.bar.winfo_ismapped())
        self.overlay.buttons["fullscreen"].event_generate("<Button-1>")
        self.overlay.buttons["maximize"].event_generate("<Button-1>")
        self.root.update()
        self.assertEqual(self.clicked, ["fullscreen", "maximize"])

    def test_work_area_has_positive_size(self):
        x, y, width, height = work_area_rect(self.root)
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)
        view_w, view_h = largest_rect_for_aspect(width, height)
        self.assertAlmostEqual(view_w / view_h, VIDEO_ASPECT, places=4)

    def test_idle_hides_buttons_until_mouse_moves(self):
        self.overlay.show()
        self.root.update_idletasks()
        self.assertTrue(self.overlay.bar.winfo_ismapped())
        self.overlay._on_idle_timeout()
        self.root.update_idletasks()
        self.assertFalse(self.overlay.bar.winfo_ismapped())
        self.host.event_generate("<Motion>", x=40, y=40)
        self.root.update_idletasks()
        self.assertTrue(self.overlay.bar.winfo_ismapped())

    def test_motion_resets_idle_hide(self):
        self.overlay.idle_hide_ms = 3000
        self.overlay.show()
        self.overlay._arm_idle_hide()
        first_job = self.overlay._idle_job
        self.assertIsNotNone(first_job)
        self.host.event_generate("<Motion>", x=20, y=20)
        self.root.update_idletasks()
        self.assertIsNotNone(self.overlay._idle_job)
        self.assertNotEqual(self.overlay._idle_job, first_job)
        self.assertTrue(self.overlay.bar.winfo_ismapped())

    def test_can_show_false_blocks_overlay(self):
        self.overlay.can_show = lambda: False
        self.overlay.show()
        self.root.update_idletasks()
        self.assertFalse(self.overlay.bar.winfo_ismapped())
        self.host.event_generate("<Enter>")
        self.root.update_idletasks()
        self.assertFalse(self.overlay.bar.winfo_ismapped())

    def test_disabled_overlay_does_not_run_expand_commands(self):
        self.overlay.enabled = False
        self.overlay.show()
        self.root.update()
        self.overlay.buttons["fullscreen"].event_generate("<Button-1>")
        self.assertEqual(self.clicked, [])

    def test_disconnect_hides_overlay_and_blocks_clicks(self):
        self.overlay.show()
        self.root.update()
        self.assertTrue(self.overlay.bar.winfo_ismapped())
        self.overlay.can_show = lambda: False
        self.overlay.enabled = True
        self.overlay.hide()
        self.overlay._cancel_idle()
        self.root.update_idletasks()
        self.assertFalse(self.overlay.bar.winfo_ismapped())
        self.host.event_generate("<Enter>")
        self.host.event_generate("<Motion>", x=40, y=40)
        self.root.update_idletasks()
        self.assertFalse(self.overlay.bar.winfo_ismapped())
        self.overlay.buttons["fullscreen"].event_generate("<Button-1>")
        self.overlay.buttons["maximize"].event_generate("<Button-1>")
        self.assertEqual(self.clicked, [])

    def test_restore_still_runs_when_tools_inactive(self):
        restored = []
        overlay = VideoHoverOverlay(
            self.host,
            {
                "restore": lambda: restored.append("restore"),
                "fullscreen": lambda: restored.append("fs"),
            },
            visible_kinds=("restore", "fullscreen"),
        )
        overlay.enabled = False
        overlay._run("fullscreen")
        overlay._run("restore")
        self.assertEqual(restored, ["restore"])
