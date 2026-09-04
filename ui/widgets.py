"""Reusable themed layout helpers."""

import ctypes
import sys
import threading
import tkinter as tk
from tkinter import ttk

from ui.theme import fonts, palette, spacing, status_color


VIDEO_ASPECT = 16 / 9


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def card(parent, padding=None):
    """Raised content card with a 1px rim. Returns (outer, inner)."""
    if padding is None:
        padding = spacing["card"]
    rim = tk.Frame(parent, bg=palette["border"], highlightthickness=0, bd=0)
    rim._theme_role = "card_rim"
    outer = ttk.Frame(rim, style="Card.TFrame")
    outer.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
    inner = ttk.Frame(outer, style="Card.TFrame")
    inner.pack(fill=tk.BOTH, expand=True, padx=padding, pady=padding)
    outer._theme_role = "card"
    inner._theme_role = "card"
    return rim, inner


def section_header(parent, text):
    label = ttk.Label(parent, text=text, style="Heading.TLabel")
    return label


def hint_label(parent, text):
    return ttk.Label(parent, text=text, style="Muted.TLabel")


class ScrollingLabel(tk.Canvas):
    """Single-line status text that eases back and forth to reveal overflow."""

    def __init__(self, parent, text="", **kwargs):
        fg = kwargs.pop("fg", palette["accent"])
        font = kwargs.pop("font", fonts["body"])
        bg = kwargs.pop("bg", palette["card"])
        kwargs.pop("anchor", None)
        kwargs.pop("justify", None)
        super().__init__(
            parent,
            highlightthickness=0,
            highlightbackground=bg,
            bd=0,
            bg=bg,
            height=1,
            **kwargs
        )
        self._fg = fg
        self._font = font
        self._theme_font = "body"
        self._text = text or ""
        self._x = 4.0
        self._direction = -1
        self._pause = 50
        self._job = None
        self._text_id = self.create_text(
            self._x, 1, text=self._text, anchor="w", fill=fg, font=font
        )
        self.bind("<Configure>", self._on_resize)
        self._sync_height()
        self._job = self.after(80, self._tick)

    def _sync_height(self):
        bbox = self.bbox(self._text_id)
        if bbox:
            height = max(bbox[3] - bbox[1] + 4, 18)
        else:
            height = 18
        if int(self.cget("height") or 0) != height:
            self.configure(height=height)
        self._center_y()

    def _center_y(self):
        height = int(self.cget("height") or 18)
        x = self.coords(self._text_id)[0] if self.coords(self._text_id) else self._x
        self.coords(self._text_id, x, height // 2)

    def _on_resize(self, _event=None):
        self._center_y()

    def _reset_scroll(self):
        self._x = 4.0
        self._direction = -1
        self._pause = 50
        self.coords(self._text_id, self._x, int(self.cget("height") or 18) // 2)

    def config(self, cnf=None, **kwargs):
        return self.configure(cnf, **kwargs)

    def configure(self, cnf=None, **kwargs):
        if isinstance(cnf, str) and not kwargs:
            return self.cget(cnf)
        if cnf and isinstance(cnf, dict):
            kwargs = {**cnf, **kwargs}
        if "text" in kwargs:
            new_text = kwargs.pop("text") or ""
            old_prefix = (self._text or "")[:24]
            self._text = new_text
            self.itemconfigure(self._text_id, text=self._text)
            if old_prefix != (self._text or "")[:24]:
                self._reset_scroll()
            self._sync_height()
        if "fg" in kwargs:
            self._fg = kwargs.pop("fg")
            self.itemconfigure(self._text_id, fill=self._fg)
        if "font" in kwargs:
            self._font = kwargs.pop("font")
            self.itemconfigure(self._text_id, font=self._font)
            self._sync_height()
        if "bg" in kwargs:
            bg = kwargs["bg"]
            kwargs.setdefault("highlightbackground", bg)
        if kwargs:
            return super().configure(**kwargs)
        return None

    def cget(self, key):
        if key == "text":
            return self._text
        if key == "fg":
            return self._fg
        if key == "font":
            return self._font
        return super().cget(key)

    def _tick(self):
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        bbox = self.bbox(self._text_id)
        width = max(self.winfo_width(), 1)
        text_w = (bbox[2] - bbox[0]) if bbox else 0
        height = int(self.cget("height") or 18)
        start_x = 4.0
        end_x = float(width - 4 - text_w)
        if not self._text or text_w <= width - 8:
            self._x = start_x
            self._direction = -1
            self.coords(self._text_id, self._x, height // 2)
        elif self._pause > 0:
            self._pause -= 1
            self.coords(self._text_id, self._x, height // 2)
        else:
            self._x += self._direction * 0.35
            if self._x <= end_x:
                self._x = end_x
                self._direction = 1
                self._pause = 50
            elif self._x >= start_x:
                self._x = start_x
                self._direction = -1
                self._pause = 50
            self.coords(self._text_id, self._x, height // 2)
        self._job = self.after(16, self._tick)


def status_label(parent, folder, count=0):
    """Compact session-count chip. Uses a tk.Label so fg can stay custom."""
    color = status_color(folder)
    label = tk.Label(
        parent,
        text=f" {folder}: {count}",
        fg=color,
        bg=palette["card"],
        font=fonts["body"],
    )
    label._theme_keep_fg = True
    label._theme_role = "status"
    label._theme_font = "body"
    return label


def form_row(parent, row, label_text, widget, label_width=22, pady=4):
    label = ttk.Label(parent, text=label_text, width=label_width, style="Card.TLabel", anchor="e")
    label.grid(row=row, column=0, sticky="e", padx=(0, 8), pady=pady)
    widget.grid(row=row, column=1, sticky="ew", pady=pady)
    parent.grid_columnconfigure(1, weight=1)
    return label, widget


class SearchableCombobox(ttk.Frame):
    """Entry plus in-window dropdown list that filters or fetches as you type."""

    def __init__(
        self,
        parent,
        values=(),
        textvariable=None,
        height=10,
        empty_message="No matches",
        fetch_values=None,
        on_select=None,
        min_query_length=0,
        search_delay_ms=350,
        **kwargs
    ):
        super().__init__(parent, style="Card.TFrame", **kwargs)
        self._all_values = [str(value) for value in values]
        self._filtered = list(self._all_values)
        self._var = textvariable if textvariable is not None else tk.StringVar()
        self._height = height
        self._empty_message = empty_message
        self._fetch_values = fetch_values
        self._on_select = on_select
        self._min_query_length = min_query_length
        self._search_delay_ms = search_delay_ms
        self._popup = None
        self._listbox = None
        self._close_bind = None
        self._configure_bind = None
        self._ignore_click = False
        self._fetch_job = None
        self._fetch_token = 0
        self._nav_keys = {"Up", "Down", "Return", "KP_Enter", "Escape", "Tab"}

        self.columnconfigure(0, weight=1)
        self._entry = ttk.Entry(self, textvariable=self._var)
        self._entry.grid(row=0, column=0, sticky="ew")
        self._arrow = ttk.Button(
            self, text="▾", width=2, command=self.toggle_popup, takefocus=False, style="Compact.TButton"
        )
        self._arrow.grid(row=0, column=1, sticky="ns", padx=(2, 0))

        self._entry.bind("<KeyRelease>", self._on_keyrelease)
        self._entry.bind("<Down>", self._on_arrow_down)
        self._entry.bind("<Up>", self._on_arrow_up)
        self._entry.bind("<Return>", self._on_enter)
        self._entry.bind("<KP_Enter>", self._on_enter)
        self._entry.bind("<Escape>", self._on_escape)
        self.bind("<Destroy>", self._on_destroy)

    @property
    def values(self):
        return list(self._all_values)

    @values.setter
    def values(self, values):
        self._all_values = [str(value) for value in values]
        self._filtered = list(self._all_values)
        if self._popup_open():
            self._fill_listbox()

    def get(self):
        return self._var.get()

    def set(self, value):
        self._var.set(value)

    def toggle_popup(self):
        if self._popup_open():
            self._close_popup()
            return
        self._ignore_click = True
        self._open_popup()
        self._refresh_list(self._var.get(), searching=bool(self._fetch_values))
        self._entry.focus_set()
        self.after_idle(self._clear_ignore_click)

    def _clear_ignore_click(self):
        self._ignore_click = False

    def _popup_open(self):
        return self._popup is not None and self._popup.winfo_exists()

    def _on_keyrelease(self, event):
        if event.keysym in self._nav_keys:
            return
        self._refresh_list(self._var.get(), searching=bool(self._fetch_values))

    def _on_arrow_down(self, _event=None):
        if not self._popup_open():
            self.toggle_popup()
            return "break"
        self._move_selection(1)
        return "break"

    def _on_arrow_up(self, _event=None):
        if not self._popup_open():
            self.toggle_popup()
            return "break"
        self._move_selection(-1)
        return "break"

    def _on_enter(self, _event=None):
        if self._popup_open() and self._filtered:
            self._commit_selection()
            return "break"
        self._close_popup()
        return "break"

    def _on_escape(self, _event=None):
        if self._popup_open():
            self._close_popup()
            return "break"
        return None

    def _on_destroy(self, _event=None):
        self._close_popup()

    def _refresh_list(self, query, searching=False):
        if searching:
            self._schedule_fetch(query)
            return
        self._filtered = self._matching_values(query)
        self._open_popup()
        self._fill_listbox()

    def _schedule_fetch(self, query):
        if self._fetch_job is not None:
            try:
                self.after_cancel(self._fetch_job)
            except tk.TclError:
                pass
        self._open_popup()
        trimmed = (query or "").strip()
        if len(trimmed) < self._min_query_length:
            self._filtered = []
            self._fill_listbox(message=f"Type at least {self._min_query_length} characters to search")
            return
        self._filtered = []
        self._fill_listbox(message="Searching...")
        self._fetch_job = self.after(self._search_delay_ms, lambda: self._start_fetch(trimmed))

    def _start_fetch(self, query):
        self._fetch_token += 1
        token = self._fetch_token

        def worker():
            try:
                results = list(self._fetch_values(query) or [])
            except Exception:
                results = []
            try:
                self.after(0, lambda: self._apply_fetched(token, results))
            except tk.TclError:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _apply_fetched(self, token, results):
        if token != self._fetch_token:
            return
        self._all_values = [str(item) for item in results]
        self._filtered = list(self._all_values)
        if not self._popup_open():
            self._open_popup()
        self._fill_listbox()

    def _open_popup(self):
        if self._popup_open():
            self._position_popup()
            return
        colors = palette
        root = self.winfo_toplevel()
        popup = tk.Frame(root, bg=colors["border"], highlightthickness=0, bd=0)
        popup._theme_role = "card_rim"
        inner = tk.Frame(popup, bg=colors["input_bg"], highlightthickness=0, bd=0)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        inner._theme_role = "card"

        listbox = tk.Listbox(
            inner,
            height=self._height,
            activestyle="none",
            exportselection=False,
            takefocus=0,
            font=fonts["body"],
            bg=colors["input_bg"],
            fg=colors["input_fg"],
            selectbackground=colors["select_bg"],
            selectforeground=colors["select_fg"],
            highlightthickness=0,
            bd=0,
            relief="flat",
        )
        scrollbar = ttk.Scrollbar(inner, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        listbox.bind("<ButtonRelease-1>", lambda _e: self._commit_selection())
        listbox.bind("<Double-Button-1>", lambda _e: self._commit_selection())

        self._popup = popup
        self._listbox = listbox
        self._position_popup()
        popup.lift()
        self._close_bind = root.bind("<Button-1>", self._on_global_click, add="+")
        self._configure_bind = root.bind("<Configure>", self._on_root_configure, add="+")

    def _on_root_configure(self, _event=None):
        if self._popup_open():
            self._position_popup()

    def _position_popup(self):
        if not self._popup_open():
            return
        self.update_idletasks()
        root = self.winfo_toplevel()
        width = max(self.winfo_width(), 240)
        rows = max(len(self._filtered), 1)
        height = min(self._height, rows) * 22 + 8
        height = max(min(height, 280), 72)
        x = self.winfo_rootx() - root.winfo_rootx()
        y = self.winfo_rooty() - root.winfo_rooty() + self.winfo_height()
        root_h = root.winfo_height()
        if y + height > root_h - 8:
            above = self.winfo_rooty() - root.winfo_rooty() - height
            if above >= 8:
                y = above
        self._popup.place(x=x, y=y, width=width, height=height)
        self._popup.lift()

    def _fill_listbox(self, message=None):
        if not self._popup_open():
            return
        self._listbox.delete(0, tk.END)
        if self._filtered:
            self._listbox.insert(tk.END, *self._filtered)
            current = (self._var.get() or "").strip()
            try:
                index = self._filtered.index(current)
            except ValueError:
                index = 0
            self._listbox.selection_clear(0, tk.END)
            self._listbox.selection_set(index)
            self._listbox.activate(index)
            self._listbox.see(index)
        else:
            self._listbox.insert(tk.END, message or self._empty_message)
            self._listbox.selection_clear(0, tk.END)
        self._position_popup()

    def _matching_values(self, query):
        raw = (query or "").strip().lower().replace("_", " ")
        if not raw:
            return list(self._all_values)
        starts = []
        city_starts = []
        contains = []
        for name in self._all_values:
            lower = name.lower()
            spaced = lower.replace("_", " ").replace("/", " ")
            city = lower.rsplit("/", 1)[-1].replace("_", " ")
            if lower.startswith(raw) or spaced.startswith(raw):
                starts.append(name)
            elif city.startswith(raw):
                city_starts.append(name)
            elif raw in spaced or raw in lower:
                contains.append(name)
        return starts + city_starts + contains

    def _move_selection(self, step):
        if not self._popup_open() or not self._filtered:
            return
        size = self._listbox.size()
        if size <= 0:
            return
        current = self._listbox.curselection()
        index = int(current[0]) if current else -1 if step > 0 else size
        index = max(0, min(size - 1, index + step))
        self._listbox.selection_clear(0, tk.END)
        self._listbox.selection_set(index)
        self._listbox.activate(index)
        self._listbox.see(index)

    def _commit_selection(self):
        if not self._popup_open() or not self._filtered:
            self._close_popup()
            return
        current = self._listbox.curselection()
        if not current:
            self._close_popup()
            return
        value = self._listbox.get(current[0])
        if value in (self._empty_message, "Searching...") or value.startswith("Type at least"):
            return
        self._var.set(value)
        self._close_popup()
        self._entry.icursor(tk.END)
        if self._on_select:
            self._on_select(value)

    def _on_global_click(self, event):
        if self._ignore_click or not self._popup_open():
            return
        widget = event.widget
        if widget in (self, self._entry, self._arrow, self._listbox, self._popup):
            return
        try:
            if str(widget).startswith(str(self._popup)) or str(widget).startswith(str(self)):
                return
        except tk.TclError:
            pass
        x, y = event.x_root, event.y_root
        if self._point_in(self, x, y) or self._point_in(self._popup, x, y):
            return
        self._close_popup()

    def _close_popup(self):
        root = None
        try:
            root = self.winfo_toplevel()
        except tk.TclError:
            pass
        if self._close_bind and root is not None:
            try:
                root.unbind("<Button-1>", self._close_bind)
            except tk.TclError:
                pass
        if self._configure_bind and root is not None:
            try:
                root.unbind("<Configure>", self._configure_bind)
            except tk.TclError:
                pass
        self._close_bind = None
        self._configure_bind = None
        if self._popup is not None:
            try:
                self._popup.place_forget()
                self._popup.destroy()
            except tk.TclError:
                pass
        self._popup = None
        self._listbox = None

    @staticmethod
    def _point_in(widget, x, y):
        try:
            if not widget.winfo_exists():
                return False
            left = widget.winfo_rootx()
            top = widget.winfo_rooty()
            return left <= x <= left + widget.winfo_width() and top <= y <= top + widget.winfo_height()
        except tk.TclError:
            return False


def panel_host(parent, padx=12, pady=12):
    """Host frame for responsive card layouts."""
    host = ttk.Frame(parent)
    host.pack(fill="both", expand=True, padx=padx, pady=pady)
    return host


def add_panel(host, padding=None):
    """Create a card for a panel host. Returns (outer, inner)."""
    return card(host, padding=padding)


def configure_panel_layout(host, rows, min_two_col_width=980):
    """Lay out cards as one or two columns based on available width.

    `rows` is a list of row definitions, where each row contains one or two
    card rim widgets returned by `card()` / `add_panel()`. Only rows that the
    caller explicitly groups into pairs are shown in two columns.
    """
    ordered_cards = [panel for row in rows for panel in row]

    def place_cards(use_two_columns):
        for row_index in range(max(len(rows), len(ordered_cards))):
            host.grid_rowconfigure(row_index, weight=0)
        for column in (0, 1):
            host.grid_columnconfigure(column, weight=0, uniform="")
        for panel in ordered_cards:
            panel.grid_forget()

        if use_two_columns:
            host.grid_columnconfigure(0, weight=1, uniform="panel")
            host.grid_columnconfigure(1, weight=1, uniform="panel")
            for row_index, row in enumerate(rows):
                if len(row) == 2:
                    row[0].grid(row=row_index, column=0, sticky="nsew", padx=(0, 4), pady=(0, 8))
                    row[1].grid(row=row_index, column=1, sticky="nsew", padx=(4, 0), pady=(0, 8))
                elif len(row) == 1:
                    row[0].grid(row=row_index, column=0, columnspan=2, sticky="nsew", pady=(0, 8))
        else:
            host.grid_columnconfigure(0, weight=1)
            for row_index, panel in enumerate(ordered_cards):
                panel.grid(row=row_index, column=0, sticky="nsew", pady=(0, 8))

    def refresh_layout(_event=None):
        try:
            use_two_columns = host.winfo_width() >= min_two_col_width
        except tk.TclError:
            return
        place_cards(use_two_columns)

    host.bind("<Configure>", refresh_layout)
    host.after_idle(refresh_layout)


def title_bar(parent, title, on_minimize, on_maximize, on_close):
    """In-app title bar with window controls. Returns (bar, maximize_button)."""
    bar = tk.Frame(parent, bg=palette["card"], highlightthickness=0, bd=0)
    bar._theme_role = "titlebar"
    title_label = tk.Label(
        bar, text=title, bg=palette["card"], fg=palette["fg"], font=fonts["heading"], bd=0
    )
    title_label._theme_role = "titlebar"
    title_label._theme_font = "heading"
    title_label.pack(side="left", padx=14, pady=8)

    close_btn = _chrome_button(bar, "✕", on_close, danger=True)
    close_btn.pack(side="right")
    max_btn = _chrome_button(bar, "□", on_maximize)
    max_btn.pack(side="right")
    min_btn = _chrome_button(bar, "–", on_minimize)
    min_btn.pack(side="right")

    def start_move(event):
        if getattr(parent, "state", lambda: "normal")() == "zoomed":
            return
        parent._drag_x = event.x_root
        parent._drag_y = event.y_root
        hwnd = _toplevel_hwnd(parent)
        parent._drag_hwnd = hwnd
        if hwnd:
            rect = _WinRect()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            parent._win_x = rect.left
            parent._win_y = rect.top
        else:
            parent._win_x = parent.winfo_x()
            parent._win_y = parent.winfo_y()

    def do_move(event):
        if getattr(parent, "state", lambda: "normal")() == "zoomed":
            return
        if not hasattr(parent, "_drag_x"):
            return
        x = parent._win_x + (event.x_root - parent._drag_x)
        y = parent._win_y + (event.y_root - parent._drag_y)
        hwnd = getattr(parent, "_drag_hwnd", 0)
        if hwnd:
            ctypes.windll.user32.SetWindowPos(hwnd, 0, x, y, 0, 0, 0x0015)
            return
        parent.geometry(f"+{x}+{y}")

    for widget in (bar, title_label):
        widget.bind("<Button-1>", start_move)
        widget.bind("<B1-Motion>", do_move)
        widget.bind("<Double-Button-1>", lambda event: on_maximize())

    return bar, max_btn


def _chrome_button(parent, text, command, danger=False):
    button = tk.Label(
        parent,
        text=text,
        width=4,
        font=fonts["body"],
        bg=palette["card"],
        fg=palette["fg"],
        cursor="hand2",
    )
    button._theme_role = "titlebar"
    button._theme_font = "body"

    def on_enter(_event):
        if danger:
            button.configure(bg=palette["danger"], fg=palette["danger_fg"])
        else:
            button.configure(bg=palette["button_active"], fg=palette["fg"])

    def on_leave(_event):
        button.configure(bg=palette["card"], fg=palette["fg"])

    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)
    button.bind("<Button-1>", lambda _event: command())
    return button


class _WinRect(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def _toplevel_hwnd(window):
    if sys.platform != "win32":
        return 0
    try:
        return ctypes.windll.user32.GetParent(window.winfo_id())
    except Exception:
        return 0


def hide_native_titlebar(window):
    """Remove OS caption so in-app minimize/close controls can replace it."""
    window.update_idletasks()
    if sys.platform != "win32":
        window.overrideredirect(True)
        return
    try:
        hwnd = _toplevel_hwnd(window)
        if not hwnd:
            return
        gwl_style = -16
        ws_caption = 0x00C00000
        ws_dlgframe = 0x00400000
        ws_border = 0x00800000
        ws_thickframe = 0x00040000
        swp_nomove = 0x0002
        swp_nosize = 0x0001
        swp_nozorder = 0x0004
        swp_framechanged = 0x0020
        style = ctypes.windll.user32.GetWindowLongW(hwnd, gwl_style)
        new_style = (style & ~(ws_caption | ws_dlgframe | ws_border)) | ws_thickframe
        if style == new_style:
            return
        ctypes.windll.user32.SetWindowLongW(hwnd, gwl_style, new_style)
        try:
            policy = ctypes.c_int(2)  # DWMNCRP_ENABLED
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(policy), ctypes.sizeof(policy))
        except Exception:
            pass
        ctypes.windll.user32.SetWindowPos(
            hwnd, 0, 0, 0, 0, 0,
            swp_nomove | swp_nosize | swp_nozorder | swp_framechanged,
        )
    except Exception:
        window.overrideredirect(True)


def tab_bar(parent, items, on_select, initial=None):
    """Custom equal-height tab strip. items is [(id, label), ...]."""
    bar = tk.Frame(parent, bg=palette["bg"], highlightthickness=0, bd=0)
    bar._theme_role = "tabbar"
    buttons = {}
    underlines = {}

    def select(tab_id, notify=True):
        for tid, button in buttons.items():
            active = tid == tab_id
            button._tab_selected = active
            button.configure(fg=palette["fg"] if active else palette["muted"], bg=palette["bg"])
            line = underlines[tid]
            line._tab_selected = active
            line.configure(bg=palette["accent"] if active else palette["bg"])
        if notify:
            on_select(tab_id)

    for tab_id, label in items:
        cell = tk.Frame(bar, bg=palette["bg"], highlightthickness=0, bd=0)
        cell._theme_role = "tabbar"
        cell.pack(side="left")
        button = tk.Label(
            cell,
            text=label,
            bg=palette["bg"],
            fg=palette["muted"],
            font=fonts["body"],
            padx=16,
            pady=10,
            cursor="hand2",
            bd=0,
        )
        button._theme_role = "tab"
        button._theme_font = "body"
        button._tab_selected = False
        button.pack()
        line = tk.Frame(cell, height=2, bg=palette["bg"], highlightthickness=0, bd=0)
        line._theme_role = "tab_underline"
        line._tab_selected = False
        line.pack(fill="x")
        button.bind("<Button-1>", lambda _event, tid=tab_id: select(tid))
        buttons[tab_id] = button
        underlines[tab_id] = line

    if initial is None and items:
        initial = items[0][0]
    if initial is not None:
        select(initial, notify=False)
    bar.select = select
    return bar


def install_mousewheel(root):
    """Scroll the widget under the pointer (canvas, log, list, or table)."""
    if getattr(root, "_mousewheel_installed", False):
        return
    root._mousewheel_installed = True

    def _scrollable(widget):
        while widget is not None:
            try:
                cls = widget.winfo_class()
            except tk.TclError:
                return None
            if cls in ("Canvas", "Text", "Listbox", "Treeview"):
                return widget
            try:
                parent = widget.winfo_parent()
                if not parent or parent == ".":
                    return None
                widget = widget.nametowidget(parent)
            except (tk.TclError, KeyError):
                return None
        return None

    def _has_vertical_overflow(widget):
        try:
            first, last = widget.yview()
        except (tk.TclError, AttributeError, TypeError, ValueError):
            return False
        return first > 0.0 or last < 1.0

    def _on_mousewheel(event):
        try:
            widget = root.winfo_containing(event.x_root, event.y_root)
        except tk.TclError:
            return
        target = _scrollable(widget)
        if target is None:
            return
        if not _has_vertical_overflow(target):
            return "break"
        if getattr(event, "num", None) == 4:
            steps = -1
        elif getattr(event, "num", None) == 5:
            steps = 1
        else:
            delta = getattr(event, "delta", 0)
            if not delta:
                return
            steps = int(-delta / 120)
            if steps == 0:
                steps = -1 if delta > 0 else 1
        try:
            target.yview_scroll(steps, "units")
        except tk.TclError:
            return
        return "break"

    root.bind_all("<MouseWheel>", _on_mousewheel)
    root.bind_all("<Button-4>", _on_mousewheel)
    root.bind_all("<Button-5>", _on_mousewheel)
    root.bind_class("TCombobox", "<MouseWheel>", _on_mousewheel)
    root.bind_class("TCombobox", "<Button-4>", _on_mousewheel)
    root.bind_class("TCombobox", "<Button-5>", _on_mousewheel)
