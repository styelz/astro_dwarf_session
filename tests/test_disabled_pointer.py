import unittest

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover
    tk = None

from unittest.mock import patch

from ui.theme import (
    control_is_unclickable,
    forbidden_cursor_name,
    install_disabled_pointer,
    refresh_disabled_pointer,
    set_pointer_blocked,
)


@unittest.skipIf(tk is None, "tkinter is required")
class DisabledPointerTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("no display")
        self.root.withdraw()
        install_disabled_pointer(self.root)

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_forbidden_cursor_is_the_platform_not_allowed_symbol(self):
        name = forbidden_cursor_name(self.root)
        self.assertIn(name, ("no", "circle", "X_cursor"))

    def test_disabled_button_is_unclickable(self):
        button = ttk.Button(self.root, text="Calibrate", state=tk.DISABLED)
        self.assertTrue(control_is_unclickable(button))
        self.assertEqual(str(button.cget("cursor")), forbidden_cursor_name(self.root))
        button.configure(state=tk.NORMAL)
        self.assertFalse(control_is_unclickable(button))
        self.assertNotEqual(str(button.cget("cursor")), forbidden_cursor_name(self.root))
        button.configure(state=tk.DISABLED)
        self.assertEqual(str(button.cget("cursor")), forbidden_cursor_name(self.root))

    def test_blocked_button_keeps_enabled_style(self):
        button = ttk.Button(self.root, text="Yes", style="Accent.TButton")
        button.configure(state=tk.NORMAL)
        set_pointer_blocked(button, True)
        self.assertTrue(control_is_unclickable(button))
        self.assertEqual(str(button.cget("state")), "normal")
        self.assertEqual(str(button.cget("style")), "Accent.TButton")
        self.assertEqual(str(button.cget("cursor")), forbidden_cursor_name(self.root))
        set_pointer_blocked(button, False)
        self.assertFalse(control_is_unclickable(button))
        self.assertEqual(str(button.cget("state")), "normal")
        self.assertEqual(str(button.cget("style")), "Accent.TButton")
        self.assertNotEqual(str(button.cget("cursor")), forbidden_cursor_name(self.root))

    def test_refresh_ignores_combobox_popdown(self):
        with patch.object(self.root, "winfo_containing", side_effect=KeyError("popdown")):
            refresh_disabled_pointer(self.root)
