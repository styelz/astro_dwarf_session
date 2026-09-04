"""Shared Tkinter/ttk theme for Astro Dwarf Scheduler."""

import configparser
import os
import sys
import tkinter as tk
from tkinter import ttk

DEFAULT_INI = "config.ini"
DEFAULT_MODE = "dark"

_FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "Arial"

PALETTES = {
    "dark": {
        "bg": "#1B1F2A",
        "card": "#252A38",
        "card_raised": "#2C3244",
        "border": "#3A4154",
        "fg": "#E8ECF4",
        "muted": "#9AA3B5",
        "input_bg": "#1F2433",
        "input_fg": "#E8ECF4",
        "select_bg": "#3D4F7C",
        "select_fg": "#FFFFFF",
        "accent": "#6EA8FE",
        "accent_fg": "#0B1220",
        "button_bg": "#32384A",
        "button_active": "#3D4458",
        "danger": "#E35D6A",
        "danger_fg": "#FFFFFF",
        "video_bg": "#141824",
        "tooltip_bg": "#2C3244",
        "tooltip_fg": "#E8ECF4",
        "log_error": "#E35D6A",
        "log_warning": "#E8A54B",
        "log_info": "#6EA8FE",
        "log_success": "#5DCA88",
        "log_default": "#E8ECF4",
        "status_todo": "#6EA8FE",
        "status_current": "#C084FC",
        "status_done": "#5DCA88",
        "status_error": "#E35D6A",
        "status_results": "#9AA3B5",
        "status_main": "#E8ECF4",
        "link": "#6EA8FE",
        "runtime": "#8BB4FF",
        "countdown": "#6EA8FE",
        "row_alt": "#2A3040",
        "tree_heading": "#2C3244",
    },
    "light": {
        "bg": "#C5CAD3",
        "card": "#D8DCE3",
        "card_raised": "#E0E3E9",
        "border": "#A8AFBB",
        "fg": "#1B2333",
        "muted": "#4A5363",
        "input_bg": "#E6E9EE",
        "input_fg": "#1B2333",
        "select_bg": "#C5D4F0",
        "select_fg": "#1B2333",
        "accent": "#3B6FE0",
        "accent_fg": "#FFFFFF",
        "button_bg": "#C8CDD6",
        "button_active": "#B4BAC6",
        "danger": "#C0392B",
        "danger_fg": "#FFFFFF",
        "video_bg": "#B4BAC6",
        "tooltip_bg": "#2A3140",
        "tooltip_fg": "#E8ECF4",
        "log_error": "#C0392B",
        "log_warning": "#A86A10",
        "log_info": "#2F5FC4",
        "log_success": "#1E8A4C",
        "log_default": "#1B2333",
        "status_todo": "#2F6FED",
        "status_current": "#7C3AED",
        "status_done": "#1E8A4C",
        "status_error": "#C0392B",
        "status_results": "#4A5363",
        "status_main": "#1B2333",
        "link": "#2F5FC4",
        "runtime": "#26447A",
        "countdown": "#0078D7",
        "row_alt": "#CED3DB",
        "tree_heading": "#C8CDD6",
    },
}

STATUS_KEYS = {
    "ToDo": "status_todo",
    "Current": "status_current",
    "Done": "status_done",
    "Error": "status_error",
    "Results": "status_results",
    "main": "status_main",
}

fonts = {
    "heading": (_FONT_FAMILY, 12, "bold"),
    "subheading": (_FONT_FAMILY, 10, "bold"),
    "body": (_FONT_FAMILY, 10),
    "hint": (_FONT_FAMILY, 9, "italic"),
    "log": ("Segoe UI Emoji", 10) if sys.platform == "win32" else (_FONT_FAMILY, 10),
}

spacing = {
    "pad": 12,
    "gap": 8,
    "card": 12,
}

mode = DEFAULT_MODE
palette = PALETTES[DEFAULT_MODE].copy()

_TTK_CLASSES = {
    "TFrame", "TLabel", "TButton", "TCheckbutton", "TRadiobutton",
    "TEntry", "TCombobox", "TNotebook", "TScrollbar", "Treeview",
    "TLabelframe", "TProgressbar", "TSeparator", "TSizegrip",
    "TMenubutton", "TSpinbox", "TPanedwindow", "DateEntry",
}


def load_appearance():
    """Read appearance from the default config.ini [UI] section."""
    config = configparser.ConfigParser()
    if os.path.exists(DEFAULT_INI):
        config.read(DEFAULT_INI)
    value = config.get("UI", "appearance", fallback=DEFAULT_MODE).strip().lower()
    return value if value in PALETTES else DEFAULT_MODE


def save_appearance(appearance):
    """Persist appearance in the default config.ini [UI] section."""
    if appearance not in PALETTES:
        appearance = DEFAULT_MODE
    config = configparser.ConfigParser()
    if os.path.exists(DEFAULT_INI):
        config.read(DEFAULT_INI)
    if not config.has_section("UI"):
        config.add_section("UI")
    config.set("UI", "appearance", appearance)
    with open(DEFAULT_INI, "w") as handle:
        config.write(handle)


def status_color(name):
    """Return the themed color for a session pipeline state."""
    key = STATUS_KEYS.get(name, "status_main")
    return palette.get(key, palette["fg"])


def apply_theme(root, appearance=None):
    """Apply ttk styles and restyle leftover tk widgets."""
    global mode, palette
    if appearance is None:
        appearance = load_appearance()
    if appearance not in PALETTES:
        appearance = DEFAULT_MODE
    mode = appearance
    palette.clear()
    palette.update(PALETTES[mode])

    p = palette
    try:
        root.configure(bg=p["bg"])
    except tk.TclError:
        pass
    for option, value in (
        ("highlightthickness", 0),
        ("highlightbackground", p["bg"]),
        ("highlightcolor", p["bg"]),
        ("bd", 0),
    ):
        try:
            root.configure(**{option: value})
        except tk.TclError:
            pass

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=p["bg"], foreground=p["fg"], font=fonts["body"])
    style.configure("TFrame", background=p["bg"], borderwidth=0, relief="flat")
    style.configure("Card.TFrame", background=p["card"], borderwidth=0, relief="flat")
    style.configure("TitleBar.TFrame", background=p["card"], borderwidth=0, relief="flat")
    style.configure("TitleBar.TLabel", background=p["card"], foreground=p["fg"], font=fonts["heading"])
    style.configure("TLabel", background=p["bg"], foreground=p["fg"], font=fonts["body"])
    style.configure("Card.TLabel", background=p["card"], foreground=p["fg"], font=fonts["body"])
    style.configure("Heading.TLabel", background=p["card"], foreground=p["fg"], font=fonts["heading"])
    style.configure("Subheading.TLabel", background=p["card"], foreground=p["fg"], font=fonts["subheading"])
    style.configure("Muted.TLabel", background=p["card"], foreground=p["muted"], font=fonts["hint"])
    style.configure("Link.TLabel", background=p["card"], foreground=p["link"], font=(_FONT_FAMILY, 10, "underline"))

    style.configure(
        "TButton",
        background=p["button_bg"],
        foreground=p["fg"],
        bordercolor=p["border"],
        lightcolor=p["button_bg"],
        darkcolor=p["border"],
        focusthickness=1,
        focuscolor=p["accent"],
        padding=(10, 6),
        font=fonts["body"],
    )
    style.map(
        "TButton",
        background=[("active", p["button_active"]), ("disabled", p["card"])],
        foreground=[("disabled", p["muted"])],
    )
    style.configure(
        "Accent.TButton",
        background=p["accent"],
        foreground=p["accent_fg"],
        bordercolor=p["accent"],
        lightcolor=p["accent"],
        darkcolor=p["accent"],
        padding=(10, 6),
        font=fonts["body"],
    )
    style.map("Accent.TButton", background=[("active", p["countdown"]), ("disabled", p["card"])])
    style.configure(
        "Danger.TButton",
        background=p["danger"],
        foreground=p["danger_fg"],
        bordercolor=p["danger"],
        lightcolor=p["danger"],
        darkcolor=p["danger"],
        padding=(10, 6),
        font=fonts["body"],
    )
    style.map("Danger.TButton", background=[("active", p["status_error"]), ("disabled", p["card"])])
    style.configure("Compact.TButton", padding=(6, 2), font=fonts["body"])
    style.configure(
        "CompactAccent.TButton",
        background=p["accent"],
        foreground=p["accent_fg"],
        bordercolor=p["accent"],
        lightcolor=p["accent"],
        darkcolor=p["accent"],
        padding=(6, 2),
        font=fonts["body"],
    )
    style.map("CompactAccent.TButton", background=[("active", p["countdown"]), ("disabled", p["card"])])

    style.configure("TCheckbutton", background=p["card"], foreground=p["fg"], font=fonts["body"])
    style.map("TCheckbutton", background=[("active", p["card"])], foreground=[("disabled", p["muted"])])
    style.configure("TRadiobutton", background=p["card"], foreground=p["fg"], font=fonts["body"])
    style.map("TRadiobutton", background=[("active", p["card"])], foreground=[("disabled", p["muted"])])

    style.configure(
        "TEntry",
        fieldbackground=p["input_bg"],
        foreground=p["input_fg"],
        insertcolor=p["fg"],
        bordercolor=p["border"],
        lightcolor=p["border"],
        darkcolor=p["border"],
        padding=4,
    )
    style.map("TEntry", fieldbackground=[("disabled", p["card"])], foreground=[("disabled", p["muted"])])

    style.configure(
        "TCombobox",
        fieldbackground=p["input_bg"],
        background=p["button_bg"],
        foreground=p["input_fg"],
        arrowcolor=p["fg"],
        bordercolor=p["border"],
        lightcolor=p["border"],
        darkcolor=p["border"],
        padding=4,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", p["input_bg"]), ("disabled", p["card"])],
        foreground=[("disabled", p["muted"])],
        background=[("readonly", p["button_bg"])],
    )

    style.layout("TNotebook.Tab", [])
    style.layout("TNotebook", [("Notebook.client", {"sticky": "nswe"})])
    style.configure(
        "TNotebook",
        background=p["bg"],
        borderwidth=0,
        relief="flat",
        tabmargins=(0, 0, 0, 0),
        padding=0,
        lightcolor=p["bg"],
        darkcolor=p["bg"],
        bordercolor=p["bg"],
    )

    style.configure(
        "TScrollbar",
        background=p["button_bg"],
        troughcolor=p["card"],
        bordercolor=p["card"],
        arrowcolor=p["muted"],
        lightcolor=p["card"],
        darkcolor=p["card"],
        arrowsize=11,
        relief="flat",
        borderwidth=0,
    )
    style.map(
        "TScrollbar",
        background=[("active", p["button_active"]), ("pressed", p["border"])],
        arrowcolor=[("active", p["fg"])],
    )
    style.configure(
        "Treeview",
        background=p["input_bg"],
        fieldbackground=p["input_bg"],
        foreground=p["fg"],
        bordercolor=p["border"],
        rowheight=24,
        font=fonts["body"],
    )
    style.configure(
        "Treeview.Heading",
        background=p["tree_heading"],
        foreground=p["fg"],
        font=fonts["subheading"],
        bordercolor=p["border"],
    )
    style.map(
        "Treeview",
        background=[("selected", p["select_bg"])],
        foreground=[("selected", p["select_fg"])],
    )
    style.map("Treeview.Heading", background=[("active", p["button_active"])])

    try:
        root.option_add("*TCombobox*Listbox.background", p["input_bg"])
        root.option_add("*TCombobox*Listbox.foreground", p["input_fg"])
        root.option_add("*TCombobox*Listbox.selectBackground", p["select_bg"])
        root.option_add("*TCombobox*Listbox.selectForeground", p["select_fg"])
        root.option_add("*TCombobox*Listbox.font", fonts["body"])
    except tk.TclError:
        pass

    _walk_tk_widgets(root)
    return palette


def style_log_text(widget):
    """Apply palette colors to a log Text widget and its level tags."""
    p = palette
    try:
        widget.configure(
            bg=p["input_bg"],
            fg=p["log_default"],
            insertbackground=p["fg"],
            selectbackground=p["select_bg"],
            selectforeground=p["select_fg"],
            highlightthickness=0,
            borderwidth=0,
            font=fonts["log"],
        )
        widget.tag_config("error", foreground=p["log_error"])
        widget.tag_config("warning", foreground=p["log_warning"])
        widget.tag_config("info", foreground=p["log_info"])
        widget.tag_config("success", foreground=p["log_success"])
        widget.tag_config("default", foreground=p["log_default"])
        # Legacy named tags used by older log calls
        widget.tag_config("red", foreground=p["log_error"])
        widget.tag_config("orange", foreground=p["log_warning"])
        widget.tag_config("gray", foreground=p["muted"])
        widget.tag_config("blue", foreground=p["log_info"])
        widget.tag_config("green", foreground=p["log_success"])
        widget.tag_config("black", foreground=p["log_default"])
    except tk.TclError:
        pass


def style_date_entry(widget):
    """Best-effort theming for tkcalendar DateEntry / Calendar."""
    p = palette
    try:
        widget.configure(
            background=p["card"],
            foreground=p["fg"],
            headersbackground=p["card_raised"],
            headersforeground=p["fg"],
            selectbackground=p["select_bg"],
            selectforeground=p["select_fg"],
            weekendbackground=p["input_bg"],
            weekendforeground=p["muted"],
            othermonthforeground=p["muted"],
            othermonthbackground=p["card"],
            othermonthweforeground=p["muted"],
            normalbackground=p["input_bg"],
            normalforeground=p["fg"],
        )
    except tk.TclError:
        pass


def _walk_tk_widgets(widget):
    _style_tk_widget(widget)
    try:
        children = widget.winfo_children()
    except tk.TclError:
        return
    for child in children:
        _walk_tk_widgets(child)


def _style_tk_widget(widget):
    try:
        cls = widget.winfo_class()
    except tk.TclError:
        return
    if cls in _TTK_CLASSES:
        if cls == "DateEntry":
            style_date_entry(widget)
        return

    p = palette
    role = getattr(widget, "_theme_role", None)
    keep_fg = getattr(widget, "_theme_keep_fg", False)

    try:
        if role == "video":
            widget.configure(bg=p["video_bg"], fg=p["muted"])
            return
        if role == "log":
            style_log_text(widget)
            return
        if role == "titlebar":
            try:
                widget.configure(bg=p["card"])
            except tk.TclError:
                pass
            try:
                widget.configure(fg=p["fg"])
            except tk.TclError:
                pass
            return
        if role == "card_rim":
            widget.configure(bg=p["border"])
            return
        if role == "tabbar":
            widget.configure(bg=p["bg"], highlightbackground=p["bg"])
            return
        if role == "tab":
            selected = getattr(widget, "_tab_selected", False)
            widget.configure(bg=p["bg"], fg=p["fg"] if selected else p["muted"])
            return
        if role == "tab_underline":
            selected = getattr(widget, "_tab_selected", False)
            widget.configure(bg=p["accent"] if selected else p["bg"])
            return
        if cls in ("Frame", "Labelframe", "Toplevel"):
            widget.configure(bg=p["bg"])
        elif cls == "Label":
            opts = {"bg": p["card"] if _parent_is_card(widget) else p["bg"]}
            if not keep_fg:
                opts["fg"] = p["fg"]
            widget.configure(**opts)
        elif cls == "Button":
            widget.configure(
                bg=p["button_bg"],
                fg=p["fg"],
                activebackground=p["button_active"],
                activeforeground=p["fg"],
                highlightbackground=p["border"],
            )
        elif cls == "Entry":
            widget.configure(
                bg=p["input_bg"],
                fg=p["input_fg"],
                insertbackground=p["fg"],
                selectbackground=p["select_bg"],
                selectforeground=p["select_fg"],
                highlightbackground=p["border"],
                relief="flat",
            )
        elif cls == "Checkbutton":
            widget.configure(
                bg=p["card"] if _parent_is_card(widget) else p["bg"],
                fg=p["fg"],
                activebackground=p["card"],
                activeforeground=p["fg"],
                selectcolor=p["input_bg"],
                highlightbackground=p["bg"],
            )
        elif cls == "Radiobutton":
            widget.configure(
                bg=p["card"],
                fg=p["fg"],
                activebackground=p["card"],
                selectcolor=p["input_bg"],
            )
        elif cls == "Text":
            widget.configure(
                bg=p["input_bg"],
                fg=p["fg"],
                insertbackground=p["fg"],
                selectbackground=p["select_bg"],
                selectforeground=p["select_fg"],
                highlightthickness=0,
                borderwidth=0,
            )
        elif cls == "Listbox":
            widget.configure(
                bg=p["input_bg"],
                fg=p["fg"],
                selectbackground=p["select_bg"],
                selectforeground=p["select_fg"],
                highlightthickness=0,
                borderwidth=0,
                activestyle="none",
            )
        elif cls == "Canvas":
            canvas_bg = (
                p["card"]
                if role == "card" or _parent_is_card(widget)
                else p["bg"]
            )
            widget.configure(
                bg=canvas_bg,
                highlightthickness=0,
                highlightbackground=canvas_bg,
            )
        elif cls == "Scrollbar":
            widget.configure(
                bg=p["button_bg"],
                troughcolor=p["bg"],
                activebackground=p["button_active"],
                highlightbackground=p["bg"],
            )
    except tk.TclError:
        pass


def _parent_is_card(widget):
    try:
        parent = widget.nametowidget(widget.winfo_parent())
        return getattr(parent, "_theme_role", None) == "card" or parent.winfo_class() == "TFrame"
    except (tk.TclError, KeyError):
        return False
