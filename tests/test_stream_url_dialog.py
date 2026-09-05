import gc
import unittest

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover
    tk = None


def _local_stringvar_entry(parent, url):
    url_var = tk.StringVar(value=url)
    entry = ttk.Entry(parent, textvariable=url_var)
    entry.configure(state="readonly")
    return entry


def _inserted_entry(parent, url):
    entry = ttk.Entry(parent)
    entry.insert(0, url)
    entry.configure(state="readonly")
    return entry


@unittest.skipIf(tk is None, "tkinter is required")
class StreamUrlEntryTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("no display")
        self.root.withdraw()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_local_stringvar_is_cleared_when_dialog_builder_returns(self):
        url = "rtsp://192.168.1.42/ch0/stream0"
        entry = _local_stringvar_entry(self.root, url)
        self.root.update_idletasks()
        gc.collect()
        self.root.update_idletasks()
        self.assertEqual(entry.get(), "")

    def test_inserted_readonly_url_stays_visible(self):
        url = "rtsp://192.168.1.42/ch0/stream0"
        entry = _inserted_entry(self.root, url)
        self.root.update_idletasks()
        gc.collect()
        self.root.update_idletasks()
        self.assertEqual(entry.get(), url)
