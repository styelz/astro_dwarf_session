"""Shared Tkinter/ttk theme for Astro Dwarf Scheduler."""

import configparser
import ctypes
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

# Each appearance defines only the core tokens below. Everything else (log
# colors, session status colors, links, countdowns) is derived in
# _derive_palette so a status color can never drift between two call sites.
#
# Semantic colors come in pairs: `<name>` is a fill used behind `on_<name>`
# text, and `<name>_text` is the higher-contrast variant for colored text on a
# normal background. Using a fill color as text is what made light mode look
# washed out, so the two roles are kept separate.
_CORE_PALETTES = {
    "dark": {
        "bg": "#1D1D1B",
        "card": "#292927",
        "card_raised": "#31312F",
        "border": "#484846",
        "border_strong": "#5A5A57",
        "fg": "#E8E8E4",
        "muted": "#A4A49C",
        "input_bg": "#222220",
        "log_bg": "#222220",
        "input_fg": "#E8E8E4",
        "select_bg": "#6EA8FE",
        "select_fg": "#121211",
        "accent": "#6EA8FE",
        "accent_fg": "#121211",
        "button_bg": "#353533",
        "button_active": "#40403E",
        "hover_mix": "#FFFFFF",
        "success": "#5DCA88",
        "on_success": "#10130F",
        "success_text": "#6ED89A",
        "warning": "#E8A54B",
        "on_warning": "#121211",
        "warning_text": "#F0B563",
        "danger": "#E35D6A",
        "on_danger": "#FFFFFF",
        "danger_text": "#F07C86",
        "info": "#6EA8FE",
        "on_info": "#121211",
        "info_text": "#8FBEFF",
        "progress": "#C084FC",
        "on_progress": "#121211",
        "progress_text": "#CDA0FD",
        "video_bg": "#151513",
        "tooltip_bg": "#31312F",
        "tooltip_fg": "#E8E8E4",
        "runtime": "#C5C5C0",
        "row_alt": "#181816",
        "tree_heading": "#31312F",
    },
    "light": {
        "bg": "#C8C8C8",
        "card": "#D9D9D9",
        "card_raised": "#E2E2E2",
        "border": "#ADADAD",
        "border_strong": "#979797",
        "fg": "#1E1E1E",
        "muted": "#5A5A5A",
        "input_bg": "#E9E9E9",
        "log_bg": "#EFEFEF",
        "input_fg": "#1E1E1E",
        "select_bg": "#3B6FE0",
        "select_fg": "#FFFFFF",
        "accent": "#3B6FE0",
        "accent_fg": "#FFFFFF",
        "button_bg": "#CBCBCB",
        "button_active": "#B6B6B6",
        "hover_mix": "#FFFFFF",
        "success": "#1E8A4C",
        "on_success": "#FFFFFF",
        "success_text": "#1E8A4C",
        "warning": "#A86A10",
        "on_warning": "#FFFFFF",
        "warning_text": "#A86A10",
        "danger": "#C0392B",
        "on_danger": "#FFFFFF",
        "danger_text": "#C0392B",
        "info": "#3B6FE0",
        "on_info": "#FFFFFF",
        "info_text": "#2F5FC4",
        "progress": "#7C3AED",
        "on_progress": "#FFFFFF",
        "progress_text": "#7C3AED",
        "video_bg": "#B3B3B3",
        "tooltip_bg": "#2A2A2A",
        "tooltip_fg": "#E8E8E8",
        "runtime": "#3A3A3A",
        "row_alt": "#CECECE",
        "tree_heading": "#CBCBCB",
    },
    # Redlight stays on a single red hue and encodes meaning through brightness,
    # so nothing on screen can leak white or orange light. A pure-red ramp has a
    # very narrow luminance range, so filled controls use a dark fill with bright
    # red text rather than the reverse -- that is the only way to get readable
    # contrast without a brighter, dark-adaptation-destroying block of color.
    "redlight": {
        "bg": "#0A0000",
        "card": "#140000",
        "card_raised": "#1C0000",
        "border": "#6B0000",
        "border_strong": "#8F0000",
        "fg": "#C20000",
        "muted": "#7A0000",
        "input_bg": "#100000",
        "log_bg": "#100000",
        "input_fg": "#C20000",
        "select_bg": "#7A0000",
        "select_fg": "#E00000",
        "accent": "#9B0000",
        "accent_fg": "#0A0000",
        "button_bg": "#220000",
        "button_active": "#330000",
        "hover_mix": "#E00000",
        "success": "#220000",
        "on_success": "#700000",
        "success_text": "#700000",
        "warning": "#220000",
        "on_warning": "#A00000",
        "warning_text": "#A00000",
        "danger": "#B00000",
        "on_danger": "#0A0000",
        "danger_text": "#D00000",
        "info": "#220000",
        "on_info": "#9B0000",
        "info_text": "#9B0000",
        "progress": "#220000",
        "on_progress": "#C20000",
        "progress_text": "#C20000",
        "video_bg": "#050000",
        "tooltip_bg": "#1C0000",
        "tooltip_fg": "#C20000",
        "runtime": "#A00000",
        "row_alt": "#080000",
        "tree_heading": "#1C0000",
    },
}

# Domain name -> semantic role. Log levels and session pipeline states are the
# app's own vocabulary, so they stay as names, but each one resolves to a single
# semantic role rather than carrying its own hex value per appearance.
_DERIVED_TOKENS = {
    "log_error": "danger_text",
    "log_warning": "warning_text",
    "log_info": "info_text",
    "log_success": "success_text",
    "log_default": "fg",
    "status_todo": "info_text",
    "status_current": "progress_text",
    "status_done": "success_text",
    "status_error": "danger_text",
    "status_results": "muted",
    "status_main": "fg",
    "link": "info_text",
    "countdown": "info_text",
}


def _derive_palette(core):
    resolved = dict(core)
    for alias, source in _DERIVED_TOKENS.items():
        resolved[alias] = core[source]
    return resolved


PALETTES = {name: _derive_palette(core) for name, core in _CORE_PALETTES.items()}

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

# One 4px scale drives every gap in the app. Named roles below map onto it so
# call sites ask for a role ("row", "gutter") rather than picking a number.
spacing = {
    "xs": 2,
    "sm": 4,
    "md": 8,
    "lg": 12,
    "xl": 16,
    "pad": 12,        # page margin around a tab's content
    "gap": 8,         # generic gap between sibling controls
    "card": 12,       # card inner padding
    "gutter": 8,      # between adjacent cards
    "row": 4,         # vertical rhythm between form rows
    "label_gap": 8,   # between a field label and its control
    "section": 8,     # below a section header
}

# Component padding. Buttons and fields share a vertical value so a button next
# to an entry lines up without per-call-site nudging.
CONTROL_PADDING = (12, 6)
COMPACT_PADDING = (8, 3)
FIELD_PADDING = (6, 4)

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
    values = {"appearance": appearance}
    if appearance in ("dark", "light"):
        values["day_appearance"] = appearance
    _write_ui_values(**values)


def load_day_appearance():
    """Last light/dark theme, used when leaving Redlight."""
    value = _ui_config().get("UI", "day_appearance", fallback="").strip().lower()
    if value in ("dark", "light"):
        return value
    current = load_appearance()
    return current if current in ("dark", "light") else DEFAULT_MODE


APPEARANCE_ORDER = ("dark", "light", "redlight")


def next_appearance():
    """Cycle Dark → Light → Redlight → Dark."""
    current = load_appearance()
    try:
        index = APPEARANCE_ORDER.index(current)
    except ValueError:
        index = 0
    return APPEARANCE_ORDER[(index + 1) % len(APPEARANCE_ORDER)]


def apply_ui_appearance(root, appearance):
    """Save, apply, and refresh window chrome after a theme change."""
    if appearance not in PALETTES:
        appearance = DEFAULT_MODE
    save_appearance(appearance)
    apply_theme(root, appearance)
    if hasattr(root, "_apply_custom_chrome"):
        root._apply_custom_chrome()
    if hasattr(root, "overview_refresh") and callable(root.overview_refresh):
        try:
            root.overview_refresh()
        except tk.TclError:
            pass
    if hasattr(root, "update_session_counts") and callable(root.update_session_counts):
        try:
            root.update_session_counts()
        except tk.TclError:
            pass
    var = getattr(root, "appearance_var", None)
    if var is not None and var.get() != appearance:
        root._syncing_appearance = True
        try:
            var.set(appearance)
        finally:
            root._syncing_appearance = False
    return appearance


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


def _mix_hex(color, other, amount):
    color = str(color).lstrip("#")
    other = str(other).lstrip("#")
    channels = []
    for index in (0, 2, 4):
        base = int(color[index:index + 2], 16)
        mix = int(other[index:index + 2], 16)
        channels.append(max(0, min(255, int(base + (mix - base) * amount))))
    return "#{:02X}{:02X}{:02X}".format(*channels)


def _hover_fill(color, appearance):
    """Lighten a fill toward the palette's own highlight anchor.

    Redlight anchors on bright red instead of white so hover cannot introduce
    green or blue light.
    """
    anchor = palette.get("hover_mix", "#FFFFFF")
    return _mix_hex(color, anchor, 0.22 if appearance == "light" else 0.28)


def _pressed_fill(color, appearance):
    return _mix_hex(color, "#000000", 0.18 if appearance == "light" else 0.22)


def _colored_button_fill(fill, appearance):
    """Redlight filled buttons use a dimmer red than the shared accent token."""
    if appearance != "redlight":
        return fill
    return _mix_hex(fill, "#000000", 0.42)


def _configure_colored_button(style, name, fill, fg, appearance, padding=CONTROL_PADDING, disabled_bg=None):
    """Clam needs lightcolor/darkcolor mapped or hover never shows on filled buttons."""
    hover = _hover_fill(fill, appearance)
    pressed = _pressed_fill(fill, appearance)
    disabled = disabled_bg if disabled_bg is not None else palette["card"]
    style.configure(
        name,
        background=fill,
        foreground=fg,
        bordercolor=fill,
        lightcolor=fill,
        darkcolor=fill,
        padding=padding,
        font=fonts["body"],
    )
    style.map(
        name,
        background=[("disabled", disabled), ("pressed", pressed), ("active", hover)],
        lightcolor=[("disabled", disabled), ("pressed", pressed), ("active", hover)],
        darkcolor=[("disabled", disabled), ("pressed", pressed), ("active", hover)],
        bordercolor=[("disabled", palette["border"]), ("pressed", pressed), ("active", hover)],
        foreground=[("disabled", palette["muted"])],
    )


def _configure_toggle(style, widget_class, p):
    """Theme checkbox/radio indicators instead of leaving the clam white box."""
    style.configure(
        widget_class,
        background=p["card"],
        foreground=p["fg"],
        font=fonts["body"],
        indicatorbackground=p["input_bg"],
        indicatorforeground=p["accent_fg"],
        upperbordercolor=p["border"],
        lowerbordercolor=p["border"],
        focuscolor=p["accent"],
        focusthickness=1,
    )
    style.map(
        widget_class,
        background=[("active", p["card"])],
        foreground=[("disabled", p["muted"])],
        indicatorbackground=[
            ("disabled", "selected", p["muted"]),
            ("disabled", p["card"]),
            ("pressed", p["button_active"]),
            ("active", "selected", p["countdown"]),
            ("selected", p["accent"]),
            ("active", p["card_raised"]),
        ],
        indicatorforeground=[
            ("disabled", p["muted"]),
            ("selected", p["accent_fg"]),
            ("!selected", p["input_fg"]),
        ],
        upperbordercolor=[
            ("disabled", p["border"]),
            ("selected", p["accent"]),
            ("active", p["accent"]),
        ],
        lowerbordercolor=[
            ("disabled", p["border"]),
            ("selected", p["accent"]),
            ("active", p["accent"]),
        ],
    )


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

    # Secondary (default) buttons are deliberately quiet: a fill only a step off
    # the card, a flat 1px rim, and no bevel. Weight comes from the border on
    # hover instead of a brighter fill, so a row of them cannot out-shout the
    # one accent button on the same card.
    style.configure(
        "TButton",
        background=p["button_bg"],
        foreground=p["fg"],
        bordercolor=p["border"],
        lightcolor=p["button_bg"],
        darkcolor=p["button_bg"],
        focusthickness=1,
        focuscolor=p["accent"],
        padding=CONTROL_PADDING,
        font=fonts["body"],
        anchor="center",
    )
    style.map(
        "TButton",
        background=[("disabled", p["card"]), ("pressed", p["border"]), ("active", p["button_active"])],
        lightcolor=[("disabled", p["card"]), ("pressed", p["border"]), ("active", p["button_active"])],
        darkcolor=[("disabled", p["card"]), ("pressed", p["border"]), ("active", p["button_active"])],
        bordercolor=[("disabled", p["border"]), ("active", p["border_strong"])],
        foreground=[("disabled", p["muted"])],
    )
    _configure_colored_button(
        style, "Accent.TButton", _colored_button_fill(p["accent"], appearance), p["accent_fg"], appearance
    )
    _configure_colored_button(
        style, "Danger.TButton", _colored_button_fill(p["danger"], appearance), p["on_danger"], appearance
    )
    _configure_colored_button(style, "Success.TButton", p["success"], p["on_success"], appearance)
    # Wait is a status readout rendered as a button, so it must not react to hover.
    style.configure(
        "Wait.TButton",
        background=p["warning"],
        foreground=p["on_warning"],
        bordercolor=p["warning"],
        lightcolor=p["warning"],
        darkcolor=p["warning"],
        padding=CONTROL_PADDING,
        font=fonts["body"],
        anchor="center",
    )
    style.map(
        "Wait.TButton",
        background=[("disabled", p["warning"]), ("active", p["warning"])],
        lightcolor=[("disabled", p["warning"]), ("active", p["warning"])],
        darkcolor=[("disabled", p["warning"]), ("active", p["warning"])],
        foreground=[("disabled", p["on_warning"])],
    )
    style.configure("Compact.TButton", padding=COMPACT_PADDING, font=fonts["body"], anchor="center")
    _configure_colored_button(
        style,
        "CompactAccent.TButton",
        _colored_button_fill(p["accent"], appearance),
        p["accent_fg"],
        appearance,
        padding=COMPACT_PADDING,
    )
    _configure_colored_button(
        style,
        "CompactDanger.TButton",
        _colored_button_fill(p["danger"], appearance),
        p["on_danger"],
        appearance,
        padding=COMPACT_PADDING,
    )
    style.configure(
        "CompactWait.TButton",
        background=p["warning"],
        foreground=p["on_warning"],
        bordercolor=p["warning"],
        lightcolor=p["warning"],
        darkcolor=p["warning"],
        padding=COMPACT_PADDING,
        font=fonts["body"],
        anchor="center",
    )
    style.map(
        "CompactWait.TButton",
        background=[("disabled", p["warning"]), ("active", p["warning"])],
        lightcolor=[("disabled", p["warning"]), ("active", p["warning"])],
        darkcolor=[("disabled", p["warning"]), ("active", p["warning"])],
        foreground=[("disabled", p["on_warning"])],
    )

    _configure_toggle(style, "TCheckbutton", p)
    _configure_toggle(style, "TRadiobutton", p)

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
        padding=FIELD_PADDING,
        font=fonts["body"],
    )
    style.map(
        "TEntry",
        fieldbackground=[
            ("disabled", p["card"]),
            ("readonly", p["input_bg"]),
        ],
        foreground=[
            ("disabled", p["muted"]),
            ("readonly", p["input_fg"]),
        ],
        selectbackground=[
            ("readonly", p["input_bg"]),
            ("!focus", p["input_bg"]),
            ("focus", p["select_bg"]),
        ],
        selectforeground=[
            ("readonly", p["input_fg"]),
            ("!focus", p["input_fg"]),
            ("focus", p["select_fg"]),
        ],
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
        padding=FIELD_PADDING,
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
        padding=FIELD_PADDING,
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
        "TNotebook.Tab",
        background=p["bg"],
        foreground=p["fg"],
        lightcolor=p["bg"],
        darkcolor=p["bg"],
        bordercolor=p["bg"],
        padding=0,
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
    install_disabled_pointer(root)
    apply_native_frame_colors(root, appearance)
    try:
        if root.winfo_class() == "Toplevel":
            root.after_idle(lambda w=root, a=appearance: theme_window_frame(w, a))
    except tk.TclError:
        pass
    return palette


def _colorref(hex_color):
    value = (hex_color or "#000000").lstrip("#")
    if len(value) != 6:
        value = "000000"
    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    return red | (green << 8) | (blue << 16)


def win32_hwnd(window):
    """Outer Win32 HWND for a Tk window, or 0 when unavailable."""
    if sys.platform != "win32":
        return 0
    try:
        inner = int(window.winfo_id())
    except (tk.TclError, TypeError, ValueError):
        return 0
    user32 = ctypes.windll.user32
    try:
        root_hwnd = user32.GetAncestor(inner, 2)  # GA_ROOT
        if root_hwnd:
            return root_hwnd
    except Exception:
        pass
    try:
        parent = user32.GetParent(inner)
    except Exception:
        parent = 0
    return parent or inner


class _WinMargins(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]


def apply_native_frame_colors(window, appearance=None):
    """Match the Windows caption/border remnant to the current theme.

    After the native title bar is removed, DWM still paints a 1px top strip
    using the default light caption color. That strip is invisible in light
    mode and shows up as a light sliver in dark mode unless it is recolored.
    """
    if sys.platform != "win32":
        return
    if appearance is None:
        appearance = mode
    hwnd = win32_hwnd(window)
    if not hwnd:
        return
    try:
        dwm = ctypes.windll.dwmapi
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
    except Exception:
        return

    frame = palette.get("card", "#1B1F2A")
    dark = ctypes.c_int(0 if appearance == "light" else 1)
    for attribute in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE
        try:
            dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(dark), ctypes.sizeof(dark))
        except Exception:
            pass

    caption = ctypes.c_int(_colorref(frame))
    border = ctypes.c_int(_colorref(palette.get("border", frame)))
    text = ctypes.c_int(_colorref(palette.get("fg", "#E8ECF4")))
    try:
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption), ctypes.sizeof(caption))  # DWMWA_CAPTION_COLOR
        dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border), ctypes.sizeof(border))  # DWMWA_BORDER_COLOR
        dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text), ctypes.sizeof(text))  # DWMWA_TEXT_COLOR
    except Exception:
        pass

    try:
        margins = _WinMargins(0, 0, 0, 0)
        dwm.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
    except Exception:
        pass

    try:
        brush = gdi32.CreateSolidBrush(_colorref(frame))
        if ctypes.sizeof(ctypes.c_void_p) == 8:
            user32.SetClassLongPtrW(hwnd, -10, brush)  # GCLP_HBRBACKGROUND
        else:
            user32.SetClassLongW(hwnd, -10, brush)
        previous = getattr(window, "_frame_brush", None)
        window._frame_brush = brush
        if previous:
            gdi32.DeleteObject(previous)
    except Exception:
        pass

    try:
        user32.RedrawWindow(hwnd, None, None, 0x0401)
    except Exception:
        pass


def theme_window_frame(window, appearance=None):
    """Color a dialog's Tk highlight and Windows frame to the active palette."""
    if appearance is None:
        appearance = mode
    p = palette
    for option, value in (
        ("bg", p["bg"]),
        ("highlightthickness", 1),
        ("highlightbackground", p["border"]),
        ("highlightcolor", p["border"]),
        ("bd", 0),
        ("relief", "flat"),
    ):
        try:
            window.configure(**{option: value})
        except tk.TclError:
            pass
    apply_native_frame_colors(window, appearance)
    if sys.platform != "win32":
        return
    hwnd = win32_hwnd(window)
    if not hwnd:
        return
    try:
        user32 = ctypes.windll.user32
        gwl_exstyle = -20
        ws_ex_clientedge = 0x00000200
        ws_ex_staticedge = 0x00020000
        style = user32.GetWindowLongW(hwnd, gwl_exstyle)
        new_style = style & ~ws_ex_clientedge & ~ws_ex_staticedge
        if new_style != style:
            user32.SetWindowLongW(hwnd, gwl_exstyle, new_style)
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0027)  # SWP_NOMOVE|NOSIZE|NOZORDER|FRAMECHANGED
        apply_native_frame_colors(window, appearance)
    except Exception:
        pass


_INPUT_SELECTION_INSTALLED = False
_EDITABLE_CLASSES = {"TEntry", "TCombobox", "Entry", "TSpinbox"}
_BACKGROUND_CLASSES = {
    "TFrame", "Frame", "TLabel", "Label", "Toplevel", "Canvas",
    "TNotebook", "Labelframe",
}
# Clickable controls that should show the platform "not allowed" cursor when
# they cannot be used. Tk's `no` cursor is the circle-with-slash on Windows.
_POINTER_CLASSES = {
    "TButton", "Button", "TCheckbutton", "Checkbutton",
    "TRadiobutton", "Radiobutton", "TMenubutton", "Menubutton",
}
FORBIDDEN_CURSOR_CANDIDATES = ("no", "circle", "X_cursor")


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


def _widget_containing(root, x, y):
    """Return the widget at screen coords, or None for Tk-only popdowns."""
    try:
        return root.winfo_containing(x, y)
    except (KeyError, tk.TclError):
        # ttk Combobox list windows are named "popdown" in Tk but are not
        # registered in Python's children map, so nametowidget raises KeyError.
        return None


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


def forbidden_cursor_name(widget=None):
    """Platform cursor for a control that cannot be clicked.

    Windows maps Tk's `no` cursor to the circle-with-slash (IDC_NO).
    """
    probe = None
    if widget is not None:
        try:
            probe = widget.nametowidget(".")
        except tk.TclError:
            probe = widget
    if probe is None:
        try:
            probe = tk._get_default_root()
        except Exception:
            probe = None
    cached = getattr(probe, "_forbidden_cursor_name", None) if probe is not None else None
    if cached:
        return cached
    for name in FORBIDDEN_CURSOR_CANDIDATES:
        if probe is None:
            return name
        try:
            previous = str(probe.cget("cursor") or "")
        except tk.TclError:
            previous = ""
        try:
            probe.configure(cursor=name)
            probe.configure(cursor=previous)
            probe._forbidden_cursor_name = name
            return name
        except tk.TclError:
            try:
                probe.configure(cursor=previous)
            except tk.TclError:
                pass
    if probe is not None:
        probe._forbidden_cursor_name = ""
    return ""


def control_is_unclickable(widget):
    """True when a button-like control should not accept clicks."""
    if widget is None or isinstance(widget, str):
        return False
    try:
        cls = widget.winfo_class()
    except tk.TclError:
        return False
    if cls not in _POINTER_CLASSES:
        return False
    if getattr(widget, "_pointer_blocked", False):
        return True
    instate = getattr(widget, "instate", None)
    if callable(instate):
        try:
            return bool(instate(["disabled"]))
        except tk.TclError:
            pass
    try:
        return str(widget.cget("state")).lower() == "disabled"
    except tk.TclError:
        return False


def _sync_widget_pointer(widget):
    """Keep a control's cursor in sync with whether it can be clicked."""
    if widget is None or isinstance(widget, str):
        return
    try:
        cls = widget.winfo_class()
    except tk.TclError:
        return
    if cls not in _POINTER_CLASSES:
        return
    blocked = control_is_unclickable(widget)
    forbidden = forbidden_cursor_name(widget)
    try:
        current = str(widget.cget("cursor") or "")
    except tk.TclError:
        return
    if blocked:
        if current != forbidden:
            widget._pointer_restored_cursor = current
        if current != forbidden:
            try:
                widget.configure(cursor=forbidden)
            except tk.TclError:
                pass
        return
    restored = getattr(widget, "_pointer_restored_cursor", None)
    if restored is None:
        restored = "" if current == forbidden else current
    widget._pointer_restored_cursor = restored
    if current != restored:
        try:
            widget.configure(cursor=restored)
        except tk.TclError:
            pass


def set_pointer_blocked(widget, blocked):
    """Mark a control unclickable without changing ttk disabled styling."""
    if widget is None:
        return
    widget._pointer_blocked = bool(blocked)
    _sync_widget_pointer(widget)


def refresh_disabled_pointer(root):
    """Update the forbidden cursor for the control currently under the pointer."""
    if root is None:
        return
    try:
        x, y = root.winfo_pointerxy()
        widget = _widget_containing(root, x, y)
        top = widget.winfo_toplevel() if widget is not None else root.winfo_toplevel()
    except (tk.TclError, KeyError):
        return
    blocked = control_is_unclickable(widget)
    if getattr(top, "_forbidden_pointer_active", None) != blocked:
        top._forbidden_pointer_active = blocked
        cursor = forbidden_cursor_name(top) if blocked else ""
        try:
            top.configure(cursor=cursor)
        except tk.TclError:
            pass
    if widget is not None:
        _sync_widget_pointer(widget)


def install_disabled_pointer(root):
    """Show the not-allowed cursor over button-like controls that cannot be clicked."""
    try:
        app = root.nametowidget(".")
    except tk.TclError:
        app = root
    if getattr(app, "_disabled_pointer_installed", False):
        return
    app._disabled_pointer_installed = True
    forbidden_cursor_name(app)
    _patch_widget_pointer_configure()

    def on_enter(event):
        widget = _widget_from_event(event, app)
        _sync_widget_pointer(widget)
        refresh_disabled_pointer(app)

    def on_motion(_event):
        refresh_disabled_pointer(app)

    for class_name in _POINTER_CLASSES:
        app.bind_class(class_name, "<Enter>", on_enter, add="+")
    app.bind_all("<Motion>", on_motion, add="+")


_POINTER_CONFIGURE_PATCHED = False


def _patch_widget_pointer_configure():
    """Keep the forbidden cursor in sync whenever a control's state changes."""
    global _POINTER_CONFIGURE_PATCHED
    if _POINTER_CONFIGURE_PATCHED:
        return
    _POINTER_CONFIGURE_PATCHED = True

    def wrap(cls):
        original = cls.configure

        def configure(self, cnf=None, **kw):
            if isinstance(cnf, str) and not kw:
                return original(self, cnf)
            result = original(self, cnf, **kw)
            keys = kw
            if isinstance(cnf, dict):
                keys = {**cnf, **kw}
            if keys and "state" in keys:
                _sync_widget_pointer(self)
            return result

        cls.configure = configure
        cls.config = configure

    wrap(ttk.Widget)
    wrap(tk.Button)
    wrap(tk.Checkbutton)
    wrap(tk.Radiobutton)

    def wrap_init(cls):
        original = cls.__init__

        def init(self, *args, **kwargs):
            original(self, *args, **kwargs)
            _sync_widget_pointer(self)

        cls.__init__ = init

    for widget_cls in (
        ttk.Button, ttk.Checkbutton, ttk.Radiobutton, ttk.Menubutton,
        tk.Button, tk.Checkbutton, tk.Radiobutton,
    ):
        wrap_init(widget_cls)


def style_log_text(widget):
    """Apply palette colors to a log Text widget and its level tags."""
    p = palette
    try:
        widget.configure(
            bg=p["log_bg"],
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


def style_text(widget, tone=None):
    """Apply palette colors to a plain Text panel.

    `tone` picks a semantic text color (e.g. "danger") for panels whose whole
    content carries a status; omit it for normal body text.
    """
    p = palette
    foreground = p.get(f"{tone}_text", p["fg"]) if tone else p["fg"]
    try:
        widget.configure(
            bg=p["input_bg"],
            fg=foreground,
            insertbackground=p["fg"],
            selectbackground=p["select_bg"],
            selectforeground=p["select_fg"],
            highlightthickness=0,
            borderwidth=0,
            font=fonts["body"],
        )
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
        _sync_widget_pointer(widget)
        return

    p = palette
    role = getattr(widget, "_theme_role", None)
    keep_fg = getattr(widget, "_theme_keep_fg", False)
    _apply_widget_font(widget, role)

    try:
        if role == "video":
            widget.configure(bg=p["video_bg"], fg=p["muted"])
            return
        if role == "video_overlay":
            try:
                widget.configure(
                    bg=p["card"],
                    highlightbackground=p["border"],
                    highlightcolor=p["border"],
                )
            except tk.TclError:
                try:
                    widget.configure(bg=p["card"])
                except tk.TclError:
                    pass
            try:
                widget.configure(fg=p["fg"])
            except tk.TclError:
                pass
            redraw = getattr(widget, "_redraw_theme", None)
            if callable(redraw):
                redraw()
            return
        if role == "log":
            style_log_text(widget)
            return
        if role == "titlebar":
            try:
                widget.configure(bg=p["card"], highlightthickness=0, highlightbackground=p["card"], bd=0)
            except tk.TclError:
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
            widget.configure(bg=p["bg"], highlightthickness=0, highlightbackground=p["bg"], bd=0)
            return
        if role == "tab":
            selected = getattr(widget, "_tab_selected", False)
            widget.configure(
                bg=p["bg"],
                fg=p["fg"] if selected else p["muted"],
                highlightthickness=0,
                highlightbackground=p["bg"],
                bd=0,
            )
            # The tab owns its own font/padding (hover bolds the label), so let it
            # restate them after the generic font pass above.
            repaint = getattr(widget, "_tab_repaint", None)
            if callable(repaint):
                repaint()
            return
        if role == "tab_underline":
            selected = getattr(widget, "_tab_selected", False)
            widget.configure(bg=p["accent"] if selected else p["bg"], highlightthickness=0, bd=0)
            return
        if role == "status":
            folder = getattr(widget, "_status_folder", None)
            widget.configure(bg=p["card"], fg=status_color(folder) if folder else p["fg"])
            return
        if role == "theme_toggle":
            redraw = getattr(widget, "redraw", None)
            if callable(redraw):
                redraw()
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
                selectcolor=p["accent"],
                highlightbackground=p["bg"],
            )
        elif cls == "Radiobutton":
            widget.configure(
                bg=p["card"],
                fg=p["fg"],
                activebackground=p["card"],
                selectcolor=p["accent"],
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
            text_id = getattr(widget, "_text_id", None)
            if text_id is not None:
                fill = p["accent"] if keep_fg else p["fg"]
                widget._fg = fill
                widget.itemconfig(text_id, fill=fill)
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
        if getattr(parent, "_theme_role", None) == "card":
            return True
        try:
            return str(parent.cget("style") or "") == "Card.TFrame"
        except tk.TclError:
            return False
    except (tk.TclError, KeyError):
        return False
