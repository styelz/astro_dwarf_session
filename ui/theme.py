"""Shared Tkinter/ttk theme for Astro Dwarf Scheduler."""

import configparser
import os
import sys
import tkinter as tk
from tkinter import ttk

DEFAULT_INI = "config.ini"
DEFAULT_MODE = "dark"

DEFAULT_FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "Arial"
DEFAULT_FONT_SIZES = {
    "heading": 12,
    "body": 10,
    "hint": 9,
}
FONT_SIZE_RANGES = {
    "heading": (10, 36),
    "body": (8, 24),
    "hint": (7, 18),
}

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
        "select_bg": "#6EA8FE",
        "select_fg": "#0B1220",
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
        "row_alt": "#161A24",
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
        "select_bg": "#3B6FE0",
        "select_fg": "#FFFFFF",
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

font_family = DEFAULT_FONT_FAMILY
font_sizes = DEFAULT_FONT_SIZES.copy()
fonts = {
    "heading": (DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZES["heading"], "bold"),
    "subheading": (DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZES["body"], "bold"),
    "body": (DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZES["body"]),
    "hint": (DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZES["hint"], "italic"),
    "log": ("Segoe UI Emoji", DEFAULT_FONT_SIZES["body"]) if sys.platform == "win32" else (DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZES["body"]),
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


def _ui_config():
    config = configparser.ConfigParser()
    if os.path.exists(DEFAULT_INI):
        config.read(DEFAULT_INI)
    return config


def _write_ui_values(**values):
    config = _ui_config()
    if not config.has_section("UI"):
        config.add_section("UI")
    for key, value in values.items():
        config.set("UI", key, str(value))
    with open(DEFAULT_INI, "w") as handle:
        config.write(handle)


def load_appearance():
    """Read appearance from the default config.ini [UI] section."""
    value = _ui_config().get("UI", "appearance", fallback=DEFAULT_MODE).strip().lower()
    return value if value in PALETTES else DEFAULT_MODE


def save_appearance(appearance):
    """Persist appearance in the default config.ini [UI] section."""
    if appearance not in PALETTES:
        appearance = DEFAULT_MODE
    _write_ui_values(appearance=appearance)


def _clamp_font_size(value, role):
    default = DEFAULT_FONT_SIZES[role]
    lo, hi = FONT_SIZE_RANGES[role]
    try:
        size = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, size))


def _log_font_family(family):
    if sys.platform == "win32" and family in ("Segoe UI", "Segoe UI Variable"):
        return "Segoe UI Emoji"
    return family


def rebuild_fonts(family=None, sizes=None):
    """Update the shared fonts dict in place so existing imports stay valid."""
    global font_family
    if family:
        font_family = family
    if sizes:
        for role, value in sizes.items():
            if role in font_sizes:
                font_sizes[role] = _clamp_font_size(value, role)
    heading = font_sizes["heading"]
    body = font_sizes["body"]
    hint = font_sizes["hint"]
    fonts["heading"] = (font_family, heading, "bold")
    fonts["subheading"] = (font_family, body, "bold")
    fonts["body"] = (font_family, body)
    fonts["hint"] = (font_family, hint, "italic")
    fonts["log"] = (_log_font_family(font_family), body)
    return fonts


def load_font_settings():
    """Read font family and sizes from the default config.ini [UI] section."""
    config = _ui_config()
    family = config.get("UI", "font_family", fallback=DEFAULT_FONT_FAMILY).strip() or DEFAULT_FONT_FAMILY
    return {
        "family": family,
        "heading": _clamp_font_size(config.get("UI", "heading_size", fallback=str(DEFAULT_FONT_SIZES["heading"])), "heading"),
        "body": _clamp_font_size(config.get("UI", "font_size", fallback=str(DEFAULT_FONT_SIZES["body"])), "body"),
        "hint": _clamp_font_size(config.get("UI", "hint_size", fallback=str(DEFAULT_FONT_SIZES["hint"])), "hint"),
    }


def save_font_settings(family, heading=None, body=None, hint=None):
    """Persist font settings in the default config.ini [UI] section."""
    current = load_font_settings()
    family = (family or current["family"]).strip() or DEFAULT_FONT_FAMILY
    heading = _clamp_font_size(heading if heading is not None else current["heading"], "heading")
    body = _clamp_font_size(body if body is not None else current["body"], "body")
    hint = _clamp_font_size(hint if hint is not None else current["hint"], "hint")
    _write_ui_values(
        font_family=family,
        heading_size=heading,
        font_size=body,
        hint_size=hint,
    )
    rebuild_fonts(family, {"heading": heading, "body": body, "hint": hint})
    return load_font_settings()


def available_font_families(root=None):
    """Installed font families, skipping vertical/@ duplicates."""
    import tkinter.font as tkfont
    names = []
    seen = set()
    try:
        families = tkfont.families(root)
    except tk.TclError:
        families = ()
    for name in families:
        if not name or name.startswith("@") or name.startswith("."):
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
    names.sort(key=str.lower)
    return names


def _body_font_size():
    try:
        return abs(int(fonts["body"][1]))
    except (TypeError, ValueError, IndexError):
        return DEFAULT_FONT_SIZES["body"]


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
    loaded_fonts = load_font_settings()
    rebuild_fonts(loaded_fonts["family"], {
        "heading": loaded_fonts["heading"],
        "body": loaded_fonts["body"],
        "hint": loaded_fonts["hint"],
    })

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
    style.configure("Link.TLabel", background=p["card"], foreground=p["link"], font=(font_family, _body_font_size(), "underline"))

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
        selectbackground=p["select_bg"],
        selectforeground=p["select_fg"],
        focusthickness=1,
        focuscolor=p["accent"],
        padding=4,
        font=fonts["body"],
    )
    style.map(
        "TEntry",
        fieldbackground=[("disabled", p["card"])],
        foreground=[("disabled", p["muted"])],
        selectbackground=[("!focus", p["input_bg"]), ("focus", p["select_bg"])],
        selectforeground=[("!focus", p["input_fg"]), ("focus", p["select_fg"])],
        bordercolor=[("focus", p["accent"])],
        lightcolor=[("focus", p["accent"])],
        darkcolor=[("focus", p["accent"])],
    )

    style.configure(
        "TCombobox",
        fieldbackground=p["input_bg"],
        background=p["button_bg"],
        foreground=p["input_fg"],
        arrowcolor=p["fg"],
        bordercolor=p["border"],
        lightcolor=p["border"],
        darkcolor=p["border"],
        selectbackground=p["select_bg"],
        selectforeground=p["select_fg"],
        focusthickness=1,
        focuscolor=p["accent"],
        padding=4,
        font=fonts["body"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[
            ("disabled", p["card"]),
            ("readonly", "focus", p["input_bg"]),
            ("readonly", p["input_bg"]),
            ("focus", p["input_bg"]),
        ],
        foreground=[
            ("disabled", p["muted"]),
            ("readonly", "focus", p["input_fg"]),
            ("readonly", p["input_fg"]),
        ],
        background=[("readonly", p["button_bg"]), ("active", p["button_active"])],
        arrowcolor=[("disabled", p["muted"]), ("active", p["accent"])],
        selectbackground=[
            ("!focus", p["input_bg"]),
            ("readonly", "!focus", p["input_bg"]),
            ("focus", p["select_bg"]),
            ("readonly", p["select_bg"]),
        ],
        selectforeground=[
            ("!focus", p["input_fg"]),
            ("readonly", "!focus", p["input_fg"]),
            ("focus", p["select_fg"]),
            ("readonly", p["select_fg"]),
        ],
        bordercolor=[("focus", p["accent"])],
        lightcolor=[("focus", p["accent"])],
        darkcolor=[("focus", p["accent"])],
    )

    style.configure(
        "TSpinbox",
        fieldbackground=p["input_bg"],
        foreground=p["input_fg"],
        insertcolor=p["fg"],
        bordercolor=p["border"],
        lightcolor=p["border"],
        darkcolor=p["border"],
        arrowcolor=p["fg"],
        selectbackground=p["select_bg"],
        selectforeground=p["select_fg"],
        padding=4,
        font=fonts["body"],
    )
    style.map(
        "TSpinbox",
        fieldbackground=[("disabled", p["card"])],
        foreground=[("disabled", p["muted"])],
        selectbackground=[("!focus", p["input_bg"]), ("focus", p["select_bg"])],
        selectforeground=[("!focus", p["input_fg"]), ("focus", p["select_fg"])],
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
        lightcolor=p["input_bg"],
        darkcolor=p["input_bg"],
        rowheight=max(22, int(_body_font_size() * 2.2) + 2),
        font=fonts["body"],
        relief="flat",
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background=p["tree_heading"],
        foreground=p["fg"],
        font=fonts["subheading"],
        bordercolor=p["border"],
        lightcolor=p["tree_heading"],
        darkcolor=p["tree_heading"],
        relief="flat",
        borderwidth=0,
    )
    try:
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    except tk.TclError:
        pass
    style.map(
        "Treeview",
        background=_treeview_color_map(style, "background", p["select_bg"]),
        foreground=_treeview_color_map(style, "foreground", p["select_fg"]),
    )
    style.map(
        "Treeview.Heading",
        background=[("active", p["button_active"])],
        foreground=[("active", p["fg"])],
    )
    try:
        style.configure("DateEntry", **(style.configure("TCombobox") or {}))
        combo_maps = style.map("TCombobox") or {}
        if combo_maps:
            style.map("DateEntry", **combo_maps)
    except tk.TclError:
        pass

    try:
        root.option_add("*TCombobox*Listbox.background", p["input_bg"])
        root.option_add("*TCombobox*Listbox.foreground", p["input_fg"])
        root.option_add("*TCombobox*Listbox.selectBackground", p["select_bg"])
        root.option_add("*TCombobox*Listbox.selectForeground", p["select_fg"])
        root.option_add("*TCombobox*Listbox.font", fonts["body"])
        root.option_add("*Entry.selectBackground", p["select_bg"])
        root.option_add("*Entry.selectForeground", p["select_fg"])
        root.option_add("*Text.selectBackground", p["select_bg"])
        root.option_add("*Text.selectForeground", p["select_fg"])
        root.option_add("*Listbox.background", p["input_bg"])
        root.option_add("*Listbox.foreground", p["fg"])
        root.option_add("*Listbox.selectBackground", p["select_bg"])
        root.option_add("*Listbox.selectForeground", p["select_fg"])
        root.option_add("*Listbox.activeBackground", p["select_bg"])
        root.option_add("*Listbox.activeForeground", p["select_fg"])
        root.option_add("*Listbox.font", fonts["body"])
        root.option_add("*Text.background", p["input_bg"])
        root.option_add("*Text.foreground", p["fg"])
    except tk.TclError:
        pass

    _walk_tk_widgets(root)
    _install_input_selection_behavior(root)
    return palette


_INPUT_SELECTION_INSTALLED = False
_EDITABLE_CLASSES = {"TEntry", "TCombobox", "Entry", "TSpinbox"}
_BACKGROUND_CLASSES = {
    "TFrame", "Frame", "TLabel", "Label", "Toplevel", "Canvas",
    "TNotebook", "Labelframe",
}


def style_treeview_rows(treeview):
    """Stripe unselected rows and force a distinct selected color.

    Windows ttk lets item tags override style.map, so selection must also be a tag.
    """
    p = palette
    try:
        treeview.tag_configure("even", background=p["input_bg"], foreground=p["fg"])
        treeview.tag_configure("odd", background=p["row_alt"], foreground=p["fg"])
        treeview.tag_configure("selected_row", background=p["select_bg"], foreground=p["select_fg"])
    except tk.TclError:
        pass


def sync_treeview_selection(treeview):
    """Keep the selected_row tag in sync so selected items stay visually distinct."""
    try:
        selected = set(treeview.selection())
        for item in treeview.get_children(""):
            tags = [tag for tag in treeview.item(item, "tags") if tag in ("even", "odd")]
            if item in selected:
                tags.append("selected_row")
            treeview.item(item, tags=tuple(tags))
    except tk.TclError:
        pass


def _treeview_color_map(style, option, selected_value):
    """Keep selected colors and drop the Windows Tk override that forces light rows."""
    filtered = []
    try:
        current = style.map("Treeview", query_opt=option)
    except tk.TclError:
        current = []
    for elm in current:
        if not elm:
            continue
        if elm[0] == "selected" or elm[:2] == ("!disabled", "!selected"):
            continue
        filtered.append(elm)
    return [("selected", selected_value)] + filtered


def _clear_text_selection(widget):
    if widget is None or isinstance(widget, str):
        return
    try:
        widget.selection_clear()
    except (tk.TclError, AttributeError):
        try:
            widget.tag_remove("sel", "1.0", "end")
        except (tk.TclError, AttributeError):
            pass


def _widget_from_event(event, root):
    widget = getattr(event, "widget", None)
    if widget is None:
        return None
    if isinstance(widget, str):
        try:
            return root.nametowidget(widget)
        except (KeyError, tk.TclError):
            return None
    return widget


def _is_in_date_popup(widget):
    """True when the click is on a DateEntry drop-down calendar."""
    current = widget
    for _ in range(30):
        if current is None:
            return False
        if type(current).__name__ == "Calendar":
            return True
        try:
            if isinstance(current, tk.Toplevel):
                for child in current.winfo_children():
                    if type(child).__name__ == "Calendar":
                        return True
        except tk.TclError:
            pass
        try:
            parent = current.winfo_parent()
            if not parent:
                return False
            current = current.nametowidget(parent)
        except (tk.TclError, KeyError):
            return False
    return False


def close_date_entry_popups(root):
    """Hide any open DateEntry calendars (they are floating Toplevels)."""
    found = []

    def walk(widget):
        if type(widget).__name__ == "DateEntry":
            found.append(widget)
        try:
            for child in widget.winfo_children():
                walk(child)
        except tk.TclError:
            pass

    try:
        walk(root)
    except tk.TclError:
        return
    for entry in found:
        top = getattr(entry, "_top_cal", None)
        if top is None:
            continue
        try:
            if top.winfo_ismapped():
                top.withdraw()
                entry.state(["!pressed"])
        except tk.TclError:
            pass


def _install_input_selection_behavior(root):
    """Clear field highlighting when focus leaves, including clicks on blank UI."""
    global _INPUT_SELECTION_INSTALLED
    if _INPUT_SELECTION_INSTALLED:
        return
    _INPUT_SELECTION_INSTALLED = True

    def on_focus_out(event):
        _clear_text_selection(_widget_from_event(event, root))

    for class_name in _EDITABLE_CLASSES:
        root.bind_class(class_name, "<FocusOut>", on_focus_out, add="+")

    def on_background_click(event):
        widget = _widget_from_event(event, root)
        if widget is None:
            return
        if _is_in_date_popup(widget) or type(widget).__name__ == "DateEntry":
            return
        close_date_entry_popups(root)
        try:
            clicked_class = widget.winfo_class()
        except tk.TclError:
            return
        if clicked_class in _EDITABLE_CLASSES:
            return
        try:
            focused = widget.focus_get()
        except tk.TclError:
            return
        if focused is None or isinstance(focused, str):
            return
        try:
            if focused.winfo_class() not in _EDITABLE_CLASSES:
                return
        except tk.TclError:
            return
        _clear_text_selection(focused)
        if clicked_class in _BACKGROUND_CLASSES:
            try:
                widget.winfo_toplevel().focus_set()
            except tk.TclError:
                pass

    root.bind_all("<Button-1>", on_background_click, add="+")


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


def style_listbox(widget):
    """Apply palette colors to a tk.Listbox, even if some options are unsupported."""
    p = palette
    try:
        widget.configure(bg=p["input_bg"], fg=p["fg"])
    except tk.TclError:
        pass
    for key, value in (
        ("selectbackground", p["select_bg"]),
        ("selectforeground", p["select_fg"]),
        ("highlightthickness", 0),
        ("highlightbackground", p["input_bg"]),
        ("borderwidth", 0),
        ("relief", "flat"),
        ("activestyle", "none"),
        ("activebackground", p["select_bg"]),
        ("activeforeground", p["select_fg"]),
        ("font", fonts["body"]),
    ):
        try:
            widget.configure({key: value})
        except tk.TclError:
            pass


def style_date_entry(widget):
    """Best-effort theming for tkcalendar DateEntry / Calendar."""
    p = palette
    colors = {
        "background": p["card"],
        "foreground": p["fg"],
        "headersbackground": p["card_raised"],
        "headersforeground": p["fg"],
        "selectbackground": p["select_bg"],
        "selectforeground": p["select_fg"],
        "weekendbackground": p["input_bg"],
        "weekendforeground": p["muted"],
        "othermonthforeground": p["muted"],
        "othermonthbackground": p["card"],
        "othermonthweforeground": p["muted"],
        "othermonthwebackground": p["card"],
        "normalbackground": p["input_bg"],
        "normalforeground": p["fg"],
        "bordercolor": p["border"],
        "disabledbackground": p["card"],
        "disabledforeground": p["muted"],
        "font": fonts["body"],
    }
    targets = [widget]
    calendar = getattr(widget, "_calendar", None)
    if calendar is not None and calendar is not widget:
        targets.append(calendar)
    for target in targets:
        try:
            target.configure(**colors)
        except tk.TclError:
            for key, value in colors.items():
                try:
                    target.configure(**{key: value})
                except tk.TclError:
                    pass
    top = getattr(widget, "_top_cal", None)
    if top is not None:
        try:
            top.configure(bg=p["card"], highlightbackground=p["border"])
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
    if cls == "DateEntry" or type(widget).__name__ == "DateEntry":
        style_date_entry(widget)
        return
    if cls == "Treeview":
        style_treeview_rows(widget)
        sync_treeview_selection(widget)
        return
    if cls in _TTK_CLASSES:
        return

    p = palette
    role = getattr(widget, "_theme_role", None)
    keep_fg = getattr(widget, "_theme_keep_fg", False)
    _apply_widget_font(widget, role)

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
            style_listbox(widget)
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


def _apply_widget_font(widget, role=None):
    font_key = getattr(widget, "_theme_font", None)
    if not font_key:
        if role == "log":
            font_key = "log"
        elif role in ("titlebar", "tab", "status", "video"):
            font_key = "body"
        else:
            try:
                cls = widget.winfo_class()
            except tk.TclError:
                return
            if cls in ("Label", "Button", "Entry", "Text", "Listbox"):
                font_key = "body"
            else:
                return
    if font_key not in fonts:
        return
    try:
        widget.configure(font=fonts[font_key])
    except tk.TclError:
        pass


def _parent_is_card(widget):
    try:
        parent = widget.nametowidget(widget.winfo_parent())
        return getattr(parent, "_theme_role", None) == "card" or parent.winfo_class() == "TFrame"
    except (tk.TclError, KeyError):
        return False
