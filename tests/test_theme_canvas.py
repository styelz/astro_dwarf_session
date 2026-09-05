import unittest

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover
    tk = None

from ui.theme import apply_theme, palette
from ui.widgets import card


@unittest.skipIf(tk is None, "tkinter is required")
class ThemeCanvasTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("no display")
        self.root.withdraw()
        apply_theme(self.root, "dark")

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_page_canvas_keeps_window_background(self):
        page = ttk.Frame(self.root)
        canvas = tk.Canvas(page, highlightthickness=0, bg=palette["bg"], bd=0)
        apply_theme(self.root, "dark")
        self.assertEqual(str(canvas.cget("bg")).lower(), palette["bg"].lower())

    def test_canvas_inside_card_keeps_card_background(self):
        _rim, inner = card(self.root)
        canvas = tk.Canvas(inner, highlightthickness=0, bg=palette["card"], bd=0)
        apply_theme(self.root, "dark")
        self.assertEqual(str(canvas.cget("bg")).lower(), palette["card"].lower())
