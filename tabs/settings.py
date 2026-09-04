import configparser
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser
import pytz

from geopy.geocoders import Nominatim
from geopy.geocoders import Photon
from timezonefinder import TimezoneFinder
from geopy.exc import GeocoderInsufficientPrivileges
from astro_dwarf_scheduler import BASE_DIR
from ui.theme import (
    apply_theme,
    available_font_families,
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZES,
    FONT_SIZE_RANGES,
    load_appearance,
    load_font_settings,
    palette,
    save_appearance,
    save_font_settings,
)
from ui.widgets import card, section_header, hint_label, SearchableCombobox

# Import for exposure and gain dropdown values
from dwarf_python_api.lib.data_utils import allowed_exposures, allowed_gains, allowed_exposuresD3, allowed_gainsD3
from dwarf_python_api.lib.data_wide_utils import allowed_wide_exposuresD3, allowed_wide_gainsD3
from dwarf_python_api.lib.data_utils import allowed_exposuresMini
from dwarf_python_api.lib.data_wide_utils import allowed_wide_gainsMini

import sys
import os

# Import DWARF_IP from config.py
DWARF_IP_CURRENT = ""
try:
    from config import DWARF_IP
    DWARF_IP_CURRENT = DWARF_IP
except ImportError:
    DWARF_IP = "192.168.88.1"  # Default fallback value

CONFIG_INI_FILE = 'config.ini'

def update_exposure_gain_options(device_type, exposure_dropdown, gain_dropdown):
    """Update the exposure and gain options based on the selected device type."""    
    # Helper function to get available names
    def get_available_names(instance):
        return [entry["name"] for entry in instance.values]
    
    if device_type == "Dwarf II":
        available_exposure_names = get_available_names(allowed_exposures)
        available_gain_names = get_available_names(allowed_gains)
        exposure_dropdown['values'] = list(reversed(available_exposure_names))
        gain_dropdown['values'] = available_gain_names
    elif device_type == "Dwarf 3 Tele Lens":
        available_exposure_namesD3 = get_available_names(allowed_exposuresD3)
        available_gain_namesD3 = get_available_names(allowed_gainsD3)
        exposure_dropdown['values'] = list(reversed(available_exposure_namesD3))
        gain_dropdown['values'] = available_gain_namesD3
    elif device_type == "Dwarf 3 Wide Lens":
        available_wide_exposure_namesD3 = get_available_names(allowed_wide_exposuresD3)
        available_wide_gains_namesD3 = get_available_names(allowed_wide_gainsD3)
        exposure_dropdown['values'] = list(reversed(available_wide_exposure_namesD3))
        gain_dropdown['values'] = available_wide_gains_namesD3
    elif device_type == "Dwarf Mini Tele Lens":
        available_exposure_namesMini = get_available_names(allowed_exposuresMini)
        available_gain_namesMini = get_available_names(allowed_gainsD3)
        exposure_dropdown['values'] = list(reversed(available_exposure_namesMini))
        gain_dropdown['values'] = available_gain_namesMini
    elif device_type == "Dwarf Mini Wide Lens":
        available_wide_exposure_namesMini = get_available_names(allowed_wide_exposuresD3)
        available_wide_gains_namesMini = get_available_names(allowed_wide_gainsMini)
        exposure_dropdown['values'] = list(reversed(available_wide_exposure_namesMini))
        gain_dropdown['values'] = available_wide_gains_namesMini
    else:
        exposure_dropdown['values'] = []
        gain_dropdown['values'] = []

def get_config_ini_file():
    """Get the appropriate INI file for the current configuration"""
    try:
        from astro_dwarf_scheduler import get_current_config_ini_file
        return get_current_config_ini_file()
    except ImportError:
        return CONFIG_INI_FILE

def get_lat_long_and_timezone(address, agent = 1):
    try:
        # Initialize the geolocator with Nominatim
        if agent == 1:
            geolocator = Nominatim(user_agent="geoapiAstroSession")
        else: 
            geolocator = Photon(user_agent="geoapiAstroSession")

        #Get location based on the address
        location = geolocator.geocode(address)
        if not location:
            return None, None, None
        latitude = getattr(location, 'latitude', None)
        longitude = getattr(location, 'longitude', None)
        if latitude is None or longitude is None:
            return None, None, None
        # Get the timezone using TimezoneFinder
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lat=latitude, lng=longitude)
        return latitude, longitude, timezone_str

    except GeocoderInsufficientPrivileges as e:
        print(f"Error: {e} - You do not have permission to access this resource.")
        # Attempt to switch agent and retry
        if agent == 1:
            print("Switching to Photon geocoder for the next attempt.")
            return get_lat_long_and_timezone(address, agent=2)  # Retry with the second agent
        else:
            messagebox.showinfo("Error", "Can't found your location data!")
            return None, None, None
    except Exception as e:
        print(f"Error: {e}")
        # Attempt to switch agent and retry
        if agent == 1:
            print("Switching to Photon geocoder for the next attempt.")
            return get_lat_long_and_timezone(address, agent=2)  # Retry with the second agent
        else:
            messagebox.showinfo("Error", "Can't found your location data!")
            return None, None, None

def search_place_suggestions(query, agent=1):
    """Return [(address, latitude, longitude), ...] for the address search list."""
    text = (query or "").strip()
    if len(text) < 2:
        return []
    try:
        if agent == 1:
            geolocator = Nominatim(user_agent="geoapiAstroSession")
        else:
            geolocator = Photon(user_agent="geoapiAstroSession")
        results = geolocator.geocode(text, exactly_one=False, limit=8) or []
        places = []
        seen = set()
        for location in results:
            address = getattr(location, "address", None) or str(location)
            latitude = getattr(location, "latitude", None)
            longitude = getattr(location, "longitude", None)
            if not address or latitude is None or longitude is None or address in seen:
                continue
            seen.add(address)
            places.append((address, latitude, longitude))
        return places
    except GeocoderInsufficientPrivileges:
        if agent == 1:
            return search_place_suggestions(query, agent=2)
        return []
    except Exception:
        if agent == 1:
            return search_place_suggestions(query, agent=2)
        return []

def find_location(settings_vars):
    try:
        latitude, longitude, timezone_str = get_lat_long_and_timezone(settings_vars["address"].get())

        if latitude and longitude and timezone_str:
            settings_vars["latitude"].set(latitude)
            settings_vars["longitude"].set(longitude)
            settings_vars["timezone"].set(timezone_str)
        else:
            print("Location or timezone could not be determined.")
            messagebox.showinfo("Error", "Can't found your location data!")
    except Exception as e:
        print(f"Error: {e}")
        messagebox.showinfo("Error", "Can't found your location data!")

def open_link(url):
    webbrowser.open_new(url)

# Load and save configuration settings from config.ini
def load_config():
    config = configparser.ConfigParser()
    config_ini_path = get_config_ini_file()
    
    config.read(config_ini_path)
    config_data = config['CONFIG'] if 'CONFIG' in config else {}
    # If DWARF_IP is not in config.ini, use the value from config.py
    if 'dwarf_ip' not in config_data:
        config_data['dwarf_ip'] = DWARF_IP
    return config_data

def save_config(config_data):
    # Read the existing config file to preserve all sections
    config = configparser.ConfigParser()
    config_ini_path = get_config_ini_file()
    config.read(config_ini_path)
    # Update only the CONFIG section with new values
    if 'CONFIG' not in config:
        config.add_section('CONFIG')
    for key, value in config_data.items():
        config.set('CONFIG', key, value)
    # Write back to file, preserving all sections
    with open(config_ini_path, 'w') as configfile:
        config.write(configfile)
        
    # Update config.py with the new DWARF_IP value if it changed and not set in config.py
    if 'dwarf_ip' in config_data:   
        update_config_py_dwarf_ip(config_data['dwarf_ip'])
    # Update DWARF_ID in config.py based on camera_type (was device_type) selection
    if 'camera_type' in config_data:
        update_config_py_dwarf_id(config_data['device_type'])

def update_config_py_dwarf_id(device_type):
    """Update the DWARF_ID value in config.py based on device_type"""
    try:
        import os
        config_py_path = 'config.py'
        # Determine DWARF_ID value (config.py values are offset by -1)
        if device_type == 'Dwarf II':
            dwarf_id_val = 1  # Config value for Dwarf II (actual device ID is 2)
        elif device_type == 'Dwarf Mini Tele Lens' or device_type == 'Dwarf Mini Wide Lens':
            dwarf_id_val = 4  # Config value for Dwarf Mini (actual device ID is 4)
        else:
            dwarf_id_val = 2  # Config value for Dwarf 3 (actual device ID is 3)
        if os.path.exists(config_py_path):
            # Read the current config.py content
            with open(config_py_path, 'r') as f:
                lines = f.readlines()
            # Find and update the DWARF_ID line
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith('DWARF_ID'):
                    lines[i] = f'DWARF_ID = "{dwarf_id_val}"\n'
                    updated = True
                    break
            # If DWARF_ID line wasn't found, add it
            if not updated:
                lines.append(f'DWARF_ID = "{dwarf_id_val}"\n')
            # Write the updated content back to config.py
            with open(config_py_path, 'w') as f:
                f.writelines(lines)
        else:
            print("config.py not found, cannot update DWARF_ID")
    except Exception as e:
        print(f"Error updating DWARF_ID in config.py: {e}")

def update_config_py_dwarf_ip(new_ip):
    """Update the DWARF_IP value in config.py"""
    try:
        import os
        config_py_path = 'config.py'
        if os.path.exists(config_py_path):
            # Read the current config.py content
            with open(config_py_path, 'r') as f:
                lines = f.readlines()
            
            # Find and update the DWARF_IP line
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith('DWARF_IP'):
                    lines[i] = f'DWARF_IP = "{new_ip}"\n'
                    updated = True
                    break
            
            # If DWARF_IP line wasn't found, add it
            if not updated:
                lines.append(f'DWARF_IP = "{new_ip}"\n')
            
            # Write the updated content back to config.py
            with open(config_py_path, 'w') as f:
                f.writelines(lines)
                
        else:
            print("config.py not found, cannot update DWARF_IP")
            
    except Exception as e:
        print(f"Error updating config.py: {e}")

# Create the settings tab
def create_settings_tab(tab_settings, settings_vars, camera_type_change_callback=None, update_create_session_callback=None):

    config = load_config()
    # --- Modern scrollable frame setup ---
    container = ttk.Frame(tab_settings)
    container.grid(row=0, column=0, sticky='nsew')
    tab_settings.grid_rowconfigure(0, weight=1)
    tab_settings.grid_columnconfigure(0, weight=1)

    canvas = tk.Canvas(container, highlightthickness=0, bg=palette["bg"], bd=0)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    def _on_frame_configure(_event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    scrollable_frame.bind("<Configure>", _on_frame_configure)
    # Add a window with a tag so we can resize it
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", tags="frame")
    canvas.configure(yscrollcommand=scrollbar.set)

    def _on_canvas_configure(event):
        # Set the inner frame's width to the canvas width
        canvas.itemconfig("frame", width=event.width)

    canvas.bind('<Configure>', _on_canvas_configure)

    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    container.grid_rowconfigure(0, weight=1)
    container.grid_columnconfigure(0, weight=1)

    settings_fields = [
        ("Your Address", "address"),
        ("Help", "Tip: In Google Maps, Ctrl + right-click to copy coordinates."),
        ("Longitude", "longitude"),
        ("Latitude", "latitude"),
        ("Timezone", "timezone"),
        ("DWARF IP", "dwarf_ip"),
        ("BLE PSD", "ble_psd"),
        ("BLE STA SSID", "ble_sta_ssid"),
        ("BLE STA Password", "ble_sta_pwd"),
        ("Help", "Only needed for Stellarium integration. Leave blank for defaults."),
        ("Stellarium IP", "stellarium_ip"),
        ("Stellarium Port", "stellarium_port"),
        ("Help", "Defaults used on the Create Session page."),
        ("IR Cut", "ircut"),
        ("Binning", "binning"),
        ("Exposure", "exposure"),
        ("Gain", "gain"),
        ("Count", "count")
    ]

    camera_type_options = [
        ("Dwarf II", "Tele Camera"),
        ("Dwarf 3 Tele Lens", "Tele Camera"),
        ("Dwarf 3 Wide Lens", "Wide-Angle Camera"),
        ("Dwarf Mini Tele Lens", "Tele Camera"),
        ("Dwarf Mini Wide Lens", "Wide-Angle Camera")
    ]
    camera_type_display = [opt[0] for opt in camera_type_options]
    camera_type_value_map = {opt[0]: opt[1] for opt in camera_type_options}
    camera_type_reverse_map = {opt[1]: opt[0] for opt in camera_type_options}
    ircut_row_index = next((i for i, (field, key) in enumerate(settings_fields) if key == "ircut"), None)
    if ircut_row_index is not None:
        settings_fields.insert(ircut_row_index, ("Camera Type", "camera_type"))

    group_for_key = {
        "address": "location", "longitude": "location", "latitude": "location", "timezone": "location",
        "dwarf_ip": "device", "ble_psd": "device", "ble_sta_ssid": "device", "ble_sta_pwd": "device",
        "stellarium_ip": "stellarium", "stellarium_port": "stellarium",
        "camera_type": "imaging", "ircut": "imaging", "binning": "imaging",
        "exposure": "imaging", "gain": "imaging", "count": "imaging",
    }
    help_groups = ["location", "stellarium", "imaging"]

    cards = {}
    inners = {}
    rows = {}
    card_order = [
        ("appearance", "Appearance"),
        ("fonts", "Fonts"),
        ("location", "Location"),
        ("device", "Device / Bluetooth"),
        ("stellarium", "Stellarium"),
        ("imaging", "Imaging defaults"),
    ]
    panels = ttk.Frame(scrollable_frame)
    panels.pack(fill="x", padx=10, pady=10)
    panels.grid_columnconfigure(0, weight=1, uniform="panel")
    panels.grid_columnconfigure(1, weight=1, uniform="panel")
    panel_layout = {
        "location": (0, 0, 1),
        "device": (0, 1, 1),
        "imaging": (1, 0, 2),
        "appearance": (2, 0, 1),
        "stellarium": (2, 1, 1),
        "fonts": (3, 0, 2),
    }
    for key, title in card_order:
        outer, inner = card(panels, padding=10)
        row, column, span = panel_layout[key]
        outer.grid(
            row=row,
            column=column,
            columnspan=span,
            sticky="nsew",
            padx=(0, 4) if column == 0 and span == 1 else (4, 0) if span == 1 else 0,
            pady=(0, 8),
        )
        section_header(inner, title).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        inner.grid_columnconfigure(1, weight=1)
        cards[key] = outer
        inners[key] = inner
        rows[key] = 1

    appearance_var = tk.StringVar(value=load_appearance())

    def on_appearance_change():
        selected = appearance_var.get()
        save_appearance(selected)
        root = tab_settings.winfo_toplevel()
        apply_theme(root, selected)
        show_saved_message()

    theme_row = ttk.Frame(inners["appearance"], style="Card.TFrame")
    theme_row.grid(row=rows["appearance"], column=0, columnspan=2, sticky="w")
    rows["appearance"] += 1
    ttk.Label(theme_row, text="Theme", style="Card.TLabel", width=12, anchor="e").pack(side="left", padx=(0, 8))
    ttk.Radiobutton(
        theme_row, text="Dark", value="dark", variable=appearance_var, command=on_appearance_change
    ).pack(side="left", padx=(0, 12))
    ttk.Radiobutton(
        theme_row, text="Light", value="light", variable=appearance_var, command=on_appearance_change
    ).pack(side="left")
    hint_label(inners["appearance"], "Applies immediately and is remembered for next launch.").grid(
        row=rows["appearance"], column=0, columnspan=2, sticky="w", pady=(6, 0)
    )

    font_settings = load_font_settings()
    font_family_var = tk.StringVar(value=font_settings["family"])
    font_heading_var = tk.StringVar(value=str(font_settings["heading"]))
    font_body_var = tk.StringVar(value=str(font_settings["body"]))
    font_hint_var = tk.StringVar(value=str(font_settings["hint"]))
    font_job = {"id": None}

    def cancel_font_job():
        job = font_job["id"]
        if job is None:
            return
        try:
            tab_settings.after_cancel(job)
        except tk.TclError:
            pass
        font_job["id"] = None

    def apply_font_choices():
        cancel_font_job()
        current = load_font_settings()
        typed = (font_family_var.get() or "").strip() or DEFAULT_FONT_FAMILY
        known = {name.lower(): name for name in families}
        if typed.lower() in known:
            family = known[typed.lower()]
        elif typed.lower() == current["family"].lower():
            family = current["family"]
        else:
            return

        def size_value(var, role):
            lo, hi = FONT_SIZE_RANGES[role]
            try:
                return max(lo, min(hi, int(str(var.get()).strip())))
            except (TypeError, ValueError, tk.TclError):
                return current[role]

        heading = size_value(font_heading_var, "heading")
        body = size_value(font_body_var, "body")
        hint = size_value(font_hint_var, "hint")
        if (
            family == current["family"]
            and heading == current["heading"]
            and body == current["body"]
            and hint == current["hint"]
        ):
            return
        save_font_settings(family, heading=heading, body=body, hint=hint)
        font_family_var.set(family)
        font_heading_var.set(str(heading))
        font_body_var.set(str(body))
        font_hint_var.set(str(hint))
        root = tab_settings.winfo_toplevel()
        apply_theme(root, load_appearance())
        show_saved_message()

    def schedule_font_apply(*_args):
        cancel_font_job()
        font_job["id"] = tab_settings.after(250, apply_font_choices)

    def reset_fonts():
        font_family_var.set(DEFAULT_FONT_FAMILY)
        font_heading_var.set(str(DEFAULT_FONT_SIZES["heading"]))
        font_body_var.set(str(DEFAULT_FONT_SIZES["body"]))
        font_hint_var.set(str(DEFAULT_FONT_SIZES["hint"]))
        apply_font_choices()

    families = available_font_families(tab_settings)
    if font_settings["family"] and font_settings["family"] not in families:
        families = [font_settings["family"]] + families

    fonts_inner = inners["fonts"]
    fonts_inner.grid_columnconfigure(1, weight=1)
    fonts_inner.grid_columnconfigure(2, weight=0)

    ttk.Label(fonts_inner, text="Font family", width=12, anchor="e", style="Card.TLabel").grid(
        row=1, column=0, sticky="e", padx=(0, 8), pady=3
    )
    font_combo = SearchableCombobox(
        fonts_inner,
        values=families,
        textvariable=font_family_var,
        on_select=lambda _value: schedule_font_apply(),
        empty_message="No matching fonts",
        height=12,
    )
    font_combo.grid(row=1, column=1, sticky="ew", pady=3, padx=(0, 16))
    font_combo._entry.bind("<FocusOut>", lambda _event: schedule_font_apply(), add="+")
    font_combo._entry.bind("<Return>", lambda _event: schedule_font_apply(), add="+")

    def _size_spinbox(parent, label, variable, role):
        lo, hi = FONT_SIZE_RANGES[role]
        wrap = ttk.Frame(parent, style="Card.TFrame")
        ttk.Label(wrap, text=label, style="Card.TLabel").pack(side="left", padx=(0, 4))
        spin = ttk.Spinbox(
            wrap,
            from_=lo,
            to=hi,
            increment=1,
            width=4,
            textvariable=variable,
            command=schedule_font_apply,
        )
        spin.pack(side="left")
        spin.bind("<FocusOut>", schedule_font_apply)
        spin.bind("<Return>", schedule_font_apply)
        return wrap

    sizes_row = ttk.Frame(fonts_inner, style="Card.TFrame")
    sizes_row.grid(row=1, column=2, sticky="e", pady=3)
    _size_spinbox(sizes_row, "Body", font_body_var, "body").pack(side="left", padx=(0, 10))
    _size_spinbox(sizes_row, "Heading", font_heading_var, "heading").pack(side="left", padx=(0, 10))
    _size_spinbox(sizes_row, "Small", font_hint_var, "hint").pack(side="left", padx=(0, 12))
    ttk.Button(sizes_row, text="Reset fonts", command=reset_fonts, style="Compact.TButton").pack(side="left")

    hint_label(fonts_inner, "Type to search installed fonts. Changes apply immediately.").grid(
        row=2, column=1, columnspan=2, sticky="w"
    )

    def find_location_in_background():
        def task():
            original_text = location_button.cget("text")
            try:
                location_button.config(state=tk.DISABLED, text="Finding...")
                find_location(settings_vars)
            finally:
                location_button.config(state=tk.NORMAL, text=original_text)
        import threading
        threading.Thread(target=task, daemon=True).start()

    location_button = ttk.Button(
        inners["location"],
        text="Find location from address",
        command=find_location_in_background,
        style="Compact.TButton",
    )

    ircut_combo = None
    ircut_var = None

    def update_ircut_options(selected_camera_type):
        nonlocal ircut_combo, ircut_var
        update_ircut_dropdown(selected_camera_type, ircut_combo, ircut_var, settings_vars)
        if 'exposure_dropdown' in settings_vars and 'gain_dropdown' in settings_vars:
            update_exposure_gain_options(selected_camera_type, settings_vars['exposure_dropdown'], settings_vars['gain_dropdown'])

    help_index = 0
    for field, key in settings_fields:
        index = key.find("http")
        if "Help" in field:
            group = help_groups[min(help_index, len(help_groups) - 1)]
            help_index += 1
            parent = inners[group]
            grid_row = rows[group]
            if index != -1:
                url = key[index:].strip()
                link_label = ttk.Label(parent, text=key[:index], style="Link.TLabel", cursor="hand2", anchor="w")
                link_label.grid(row=grid_row, column=1, sticky="w", pady=3)
                link_label.bind("<Button-1>", lambda e, url=url: open_link(url))
            else:
                hint_label(parent, key).grid(row=grid_row, column=1, sticky="w", pady=3)
            rows[group] += 1
            continue

        group = group_for_key.get(key, "imaging")
        parent = inners[group]
        grid_row = rows[group]
        ttk.Label(parent, width=12, text=field, anchor="e", style="Card.TLabel").grid(
            row=grid_row, column=0, sticky="e", padx=(0, 8), pady=3
        )

        if key == "address":
            current_address = str(config.get(key, "") or "")
            var = tk.StringVar(value=current_address)
            place_lookup = {}

            def fetch_addresses(query):
                places = search_place_suggestions(query)
                place_lookup.clear()
                labels = []
                for address, lat, lon in places:
                    place_lookup[address] = (lat, lon)
                    labels.append(address)
                return labels

            def apply_address_choice(address):
                coords = place_lookup.get(address)
                if not coords:
                    return
                latitude, longitude = coords
                settings_vars["latitude"].set(latitude)
                settings_vars["longitude"].set(longitude)
                timezone_str = TimezoneFinder().timezone_at(lat=float(latitude), lng=float(longitude))
                if timezone_str:
                    settings_vars["timezone"].set(timezone_str)
                    tz_combo = settings_vars.get("timezone_dropdown")
                    if tz_combo is not None:
                        tz_values = list(tz_combo.cget("values") or ())
                        if timezone_str not in tz_values:
                            tz_combo.configure(values=[timezone_str] + tz_values)

            combo = SearchableCombobox(
                parent,
                textvariable=var,
                fetch_values=fetch_addresses,
                on_select=apply_address_choice,
                min_query_length=2,
                empty_message="No matching places",
            )
            settings_vars[key] = var
            settings_vars["address_dropdown"] = combo
            combo.grid(row=grid_row, column=1, sticky="ew", pady=3)
            hint_label(parent, "Type to search, then pick a place from the list.").grid(
                row=grid_row + 1, column=1, sticky="w"
            )
            location_button.grid(row=grid_row + 2, column=1, pady=3, sticky="ew")
            rows[group] += 2
        elif key == "timezone":
            current_tz = str(config.get(key, "") or "")
            tz_list = list(pytz.common_timezones)
            if current_tz and current_tz not in tz_list:
                tz_list = [current_tz] + tz_list
            var = tk.StringVar(value=current_tz)
            combo = ttk.Combobox(parent, textvariable=var, values=tz_list, state="readonly")
            settings_vars[key] = var
            settings_vars["timezone_dropdown"] = combo
            combo.grid(row=grid_row, column=1, sticky="ew", pady=3)
        elif key == "ircut":
            device_type_val = config.get('device_type', '')
            if device_type_val in camera_type_display:
                camera_type_display_val = device_type_val
            else:
                camera_type_val = config.get('camera_type', 'Tele Camera')
                camera_type_display_val = camera_type_reverse_map.get(camera_type_val, camera_type_display[0])

            if camera_type_display_val == "Dwarf II":
                display_options = ["D2: IRCut", "D2: IRPass"]
            elif camera_type_display_val == 'Dwarf Mini Tele Lens':
                display_options = ["Mini: Dark Filter", "Mini: Astro Filter", "Mini: DUAL Band"]
            else:
                display_options = ["D3: VIS Filter", "D3: Astro Filter", "D3: DUAL Band"]
            value_map = {"D2: IRCut": 0, "D2: IRPass": 1, "D3: VIS Filter": 0, "D3: Astro Filter": 1, "D3: DUAL Band": 2, "Mini: Dark Filter": 0, "Mini: Astro Filter": 1, "Mini: DUAL Band": 2}
            current_val = str(config.get(key, ''))
            initial_display = display_options[0]
            for disp in display_options:
                if str(value_map[disp]) == current_val:
                    initial_display = disp
                    break
            ircut_var = tk.StringVar(value=initial_display)
            ircut_combo = ttk.Combobox(parent, textvariable=ircut_var, values=display_options, state="readonly")
            settings_vars[key] = ircut_var
            settings_vars['ircut_dropdown'] = ircut_combo
            ircut_combo.grid(row=grid_row, column=1, sticky="ew", pady=3)
            settings_vars['_ircut_value_map'] = {disp: value_map[disp] for disp in display_options}
        elif key == "binning":
            binning_options = [("4k", 0), ("2k", 1)]
            binning_display_options = [opt for opt, val in binning_options]
            binning_value_map = {opt: val for opt, val in binning_options}
            current_val = str(config.get(key, ''))
            initial_display = binning_display_options[0]
            for disp, val in binning_value_map.items():
                if str(val) == current_val:
                    initial_display = disp
                    break
            var = tk.StringVar(value=initial_display)
            combo = ttk.Combobox(parent, textvariable=var, values=binning_display_options, state="readonly")
            settings_vars[key] = var
            settings_vars['binning_dropdown'] = combo
            combo.grid(row=grid_row, column=1, sticky="ew", pady=3)
            if '_binning_value_map' not in settings_vars:
                settings_vars['_binning_value_map'] = binning_value_map
        elif key == "camera_type":
            device_type_val = config.get('device_type', '')
            if device_type_val in camera_type_display:
                initial_display = device_type_val
            else:
                current_val = config.get(key, '')
                initial_display = camera_type_reverse_map.get(current_val, camera_type_display[0])
            var = tk.StringVar(value=initial_display)
            combo = ttk.Combobox(parent, textvariable=var, values=camera_type_display, state="readonly")
            settings_vars[key] = var
            combo.grid(row=grid_row, column=1, sticky="ew", pady=3)
            if '_camera_type_value_map' not in settings_vars:
                settings_vars['_camera_type_value_map'] = camera_type_value_map

            def make_camera_type_handler(bound_var):
                def handler(event):
                    selected_device_type = bound_var.get()
                    update_ircut_options(selected_device_type)
                    if selected_device_type == "Dwarf 3 Wide Lens" or selected_device_type == "Dwarf Mini Wide Lens":
                        if 'ircut_dropdown' in settings_vars:
                            settings_vars['ircut_dropdown'].config(state="disabled")
                            if 'ircut' in settings_vars and '_ircut_value_map' in settings_vars:
                                first_option = list(settings_vars['_ircut_value_map'].keys())[0]
                                settings_vars['ircut'].set(first_option)
                        if 'binning_dropdown' in settings_vars:
                            settings_vars['binning_dropdown'].config(state="disabled")
                    else:
                        if 'ircut_dropdown' in settings_vars:
                            settings_vars['ircut_dropdown'].config(state="readonly")
                        if 'binning_dropdown' in settings_vars:
                            settings_vars['binning_dropdown'].config(state="readonly")

                    if 'exposure' in settings_vars and 'gain' in settings_vars:
                        def get_available_names(instance):
                            return [entry["name"] for entry in instance.values]

                        if selected_device_type == "Dwarf II":
                            available_exposure_names = get_available_names(allowed_exposures)
                            available_gain_names = get_available_names(allowed_gains)
                            default_exposure = "15" if "15" in available_exposure_names else available_exposure_names[0] if available_exposure_names else "15"
                            default_gain = "100" if "100" in available_gain_names else available_gain_names[0] if available_gain_names else "100"
                        elif selected_device_type == "Dwarf 3 Tele Lens":
                            available_exposure_namesD3 = get_available_names(allowed_exposuresD3)
                            available_gain_namesD3 = get_available_names(allowed_gainsD3)
                            default_exposure = "30" if "30" in available_exposure_namesD3 else available_exposure_namesD3[0] if available_exposure_namesD3 else "30"
                            default_gain = "60" if "60" in available_gain_namesD3 else available_gain_namesD3[0] if available_gain_namesD3 else "60"
                        elif selected_device_type == "Dwarf 3 Wide Lens":
                            available_wide_exposure_namesD3 = get_available_names(allowed_wide_exposuresD3)
                            available_wide_gains_namesD3 = get_available_names(allowed_wide_gainsD3)
                            default_exposure = "0.4" if "0.4" in available_wide_exposure_namesD3 else available_wide_exposure_namesD3[0] if available_wide_exposure_namesD3 else "0.4"
                            default_gain = "100" if "100" in available_wide_gains_namesD3 else available_wide_gains_namesD3[0] if available_wide_gains_namesD3 else "100"
                        elif selected_device_type == "Dwarf Mini Tele Lens":
                            available_exposure_namesMini = get_available_names(allowed_exposuresMini)
                            available_gain_namesD3 = get_available_names(allowed_gainsD3)
                            default_exposure = "30" if "30" in available_exposure_namesMini else available_exposure_namesMini[0] if available_exposure_namesMini else "30"
                            default_gain = "60" if "60" in available_gain_namesD3 else available_gain_namesD3[0] if available_gain_namesD3 else "60"
                        elif selected_device_type == "Dwarf Mini Wide Lens":
                            available_wide_exposure_namesD3 = get_available_names(allowed_wide_exposuresD3)
                            available_wide_gains_namesMini = get_available_names(allowed_wide_gainsMini)
                            default_exposure = "0.4" if "0.4" in available_wide_exposure_namesD3 else available_wide_exposure_namesD3[0] if available_wide_exposure_namesD3 else "0.4"
                            default_gain = "100" if "100" in available_wide_gains_namesMini else available_wide_gains_namesMini[0] if available_wide_gains_namesMini else "100"
                        else:
                            available_exposure_names = get_available_names(allowed_exposures)
                            available_gain_names = get_available_names(allowed_gains)
                            default_exposure = "15" if "15" in available_exposure_names else available_exposure_names[0] if available_exposure_names else "15"
                            default_gain = "100" if "100" in available_gain_names else available_gain_names[0] if available_gain_names else "100"

                        settings_vars['exposure'].set(default_exposure)
                        settings_vars['gain'].set(default_gain)
                        if 'exposure_dropdown' in settings_vars and 'gain_dropdown' in settings_vars:
                            update_exposure_gain_options(selected_device_type, settings_vars['exposure_dropdown'], settings_vars['gain_dropdown'])

                    if camera_type_change_callback:
                        camera_type_change_callback(selected_device_type)
                return handler
            combo.bind('<<ComboboxSelected>>', make_camera_type_handler(var))
        elif key == "exposure":
            current_val = config.get(key, '30')
            var = tk.StringVar(value=current_val)
            combo = ttk.Combobox(parent, textvariable=var, state="readonly")
            settings_vars[key] = var
            settings_vars['exposure_dropdown'] = combo
            combo.grid(row=grid_row, column=1, sticky="ew", pady=3)
        elif key == "gain":
            current_val = config.get(key, '22')
            var = tk.StringVar(value=current_val)
            combo = ttk.Combobox(parent, textvariable=var, state="readonly")
            settings_vars[key] = var
            settings_vars['gain_dropdown'] = combo
            combo.grid(row=grid_row, column=1, sticky="ew", pady=3)
        else:
            var = tk.StringVar(value=config.get(key, ''))
            entry = ttk.Entry(parent, textvariable=var)
            settings_vars[key] = var
            entry.grid(row=grid_row, column=1, sticky="ew", pady=3)
        rows[group] += 1

    if 'exposure_dropdown' in settings_vars and 'gain_dropdown' in settings_vars:
        device_type_val = config.get('device_type', '')
        if device_type_val not in camera_type_display:
            camera_type_val = config.get('camera_type', 'Tele Camera')
            device_type_val = camera_type_reverse_map.get(camera_type_val, camera_type_display[0])
        update_exposure_gain_options(device_type_val, settings_vars['exposure_dropdown'], settings_vars['gain_dropdown'])

    initial_device_type = config.get('device_type', '')
    if initial_device_type not in camera_type_display:
        camera_type_val = config.get('camera_type', 'Tele Camera')
        initial_device_type = camera_type_reverse_map.get(camera_type_val, camera_type_display[0])

    if initial_device_type == "Dwarf 3 Wide Lens":
        if 'ircut_dropdown' in settings_vars:
            settings_vars['ircut_dropdown'].config(state="disabled")
            if 'ircut' in settings_vars and '_ircut_value_map' in settings_vars:
                first_option = list(settings_vars['_ircut_value_map'].keys())[0]
                settings_vars['ircut'].set(first_option)
        if 'binning_dropdown' in settings_vars:
            settings_vars['binning_dropdown'].config(state="disabled")

    saved_status = hint_label(inners["device"], "")
    saved_status.grid(row=rows["device"], column=0, columnspan=2, sticky="se", pady=(8, 0))
    inners["device"].grid_rowconfigure(rows["device"], weight=1)
    persist_job = {"id": None}
    status_job = {"id": None}
    listening = {"on": False}

    def cancel_job(holder):
        job = holder["id"]
        if job is None:
            return
        try:
            tab_settings.after_cancel(job)
        except tk.TclError:
            pass
        holder["id"] = None

    def show_saved_message():
        try:
            if not saved_status.winfo_exists():
                return
        except tk.TclError:
            return
        saved_status.configure(text="Settings Saved")
        cancel_job(status_job)

        def hide_saved_message():
            status_job["id"] = None
            try:
                if saved_status.winfo_exists():
                    saved_status.configure(text="")
            except tk.TclError:
                pass

        status_job["id"] = tab_settings.after(2500, hide_saved_message)

    def persist_settings(show_status=False):
        cancel_job(persist_job)
        changed = save_settings(
            settings_vars,
            show_message=False,
            update_create_session_callback=update_create_session_callback,
        )
        if show_status and changed:
            show_saved_message()
        return changed

    def schedule_persist(*_args):
        if not listening["on"]:
            return
        cancel_job(persist_job)
        persist_job["id"] = tab_settings.after(350, lambda: persist_settings(show_status=True))

    for key, var in list(settings_vars.items()):
        if key.startswith("_") or key.endswith("_dropdown"):
            continue
        if hasattr(var, "trace_add"):
            var.trace_add("write", schedule_persist)
    listening["on"] = True

    def on_tab_focus_out(_event):
        persist_settings(show_status=True)

    def on_app_close():
        persist_settings(show_status=False)
        if hasattr(tab_settings, "winfo_toplevel"):
            tab_settings.winfo_toplevel().destroy()

    tab_settings.bind("<FocusOut>", on_tab_focus_out)
    root = tab_settings.winfo_toplevel()
    if hasattr(root, "protocol"):
        try:
            root.protocol("WM_DELETE_WINDOW", on_app_close)
        except Exception:
            pass

def save_settings(settings_vars, show_message=True, update_create_session_callback=None):
    config_data = {}
    device_type_display_name = None
    settings_changed = False
    
    # Load current config to compare with new values
    try:
        current_config = load_config()
    except:
        current_config = {}
    
    # Track if any Create Session relevant settings changed
    create_session_relevant_keys = ['exposure', 'gain', 'count', 'device_type', 'camera_type']
    
    for key, var in settings_vars.items():
        if key == "ircut" and '_ircut_value_map' in settings_vars:
            display_val = var.get()
            value_map = settings_vars['_ircut_value_map']
            new_value = str(value_map.get(display_val, 0))
            config_data[key] = new_value
            # Check if this value actually changed
            if key in create_session_relevant_keys:
                old_value = current_config.get(key, "")
                if str(old_value) != new_value:
                    settings_changed = True
        elif key == "binning" and '_binning_value_map' in settings_vars:
            display_val = var.get()
            value_map = settings_vars['_binning_value_map']
            new_value = str(value_map.get(display_val, 0))
            config_data[key] = new_value
            # Check if this value actually changed
            if key in create_session_relevant_keys:
                old_value = current_config.get(key, "")
                if str(old_value) != new_value:
                    settings_changed = True
        elif key == "camera_type" and '_camera_type_value_map' in settings_vars:
            display_val = var.get()
            value_map = settings_vars['_camera_type_value_map']
            new_value = str(value_map.get(display_val, 'Tele Camera'))
            config_data[key] = new_value
            device_type_display_name = display_val  # Save the display name for config.ini
            # Check if camera_type actually changed
            old_value = current_config.get(key, "")
            if str(old_value) != new_value:
                settings_changed = True
        elif key.startswith('_') or key.endswith('_dropdown'):
            continue
        else:
            new_value = var.get()
            config_data[key] = new_value
            # Check if this value actually changed
            if key in create_session_relevant_keys:
                old_value = current_config.get(key, "")
                if str(old_value) != new_value:
                    settings_changed = True
            
    # Save the display name of camera_type as device_type in config.ini
    if device_type_display_name is not None:
        new_device_type = device_type_display_name
        config_data['device_type'] = new_device_type
        # Check if device_type actually changed
        old_device_type = current_config.get('device_type', "")
        if str(old_device_type) != new_device_type:
            settings_changed = True
        
    any_changed = False
    for key, value in config_data.items():
        if str(current_config.get(key, "")) != str(value):
            any_changed = True
            break
    if not any_changed:
        return False

    save_config(config_data)
    
    # Trigger Create Session update if relevant settings changed
    if settings_changed and update_create_session_callback:
        update_create_session_callback()
        
    if show_message:
        messagebox.showinfo("Settings", "Configuration saved successfully!")
    return True

# Utility function to update IR Cut dropdown and value map on the page
def update_ircut_dropdown(camera_type_display_val, ircut_combo, ircut_var, settings_vars):
    d2_options = [
        ("D2: IR Cut", 0),
        ("D2: IR Pass", 1)
    ]
    d3_options = [
        ("D3: VIS", 0),
        ("D3: ASTRO", 1),
        ("D3: DUAL BAND", 2)
    ]
    mini_options = [
        ("Mini: DARK", 0),
        ("Mini: ASTRO", 1),
        ("Mini: DUAL BAND", 2)
    ]
    if camera_type_display_val == "Dwarf II":
        options = d2_options
    elif camera_type_display_val == "Dwarf Mini Tele Lens":
        options = mini_options
    else:
        options = d3_options
    display_options = [opt for opt, val in options]
    value_map = {opt: val for opt, val in options}
    
    # Update the value map in settings_vars
    settings_vars['_ircut_value_map'] = value_map
    
    if ircut_combo is not None and ircut_var is not None:
        ircut_combo['values'] = display_options
        current_val = ircut_var.get()
        if current_val not in display_options:
            ircut_var.set(display_options[0])
    
    # Handle special case for Dwarf 3 Wide Lens
    if camera_type_display_val == "Dwarf 3 Wide Lens" or camera_type_display_val == "Dwarf Mini Wide Lens":
        # Set to first option and disable
        if 'ircut_dropdown' in settings_vars:
            settings_vars['ircut_dropdown'].config(state="disabled")
        if ircut_var is not None:
            ircut_var.set(display_options[0])
    else:
        # Enable for other device types
        if 'ircut_dropdown' in settings_vars:
            settings_vars['ircut_dropdown'].config(state="readonly")

def refresh_settings_tab(tab_settings, config_vars, camera_type_change_callback=None, update_create_session_callback=None):
    """Refresh the settings tab with new configuration data"""
    # Clear the existing tab
    for widget in tab_settings.winfo_children():
        widget.destroy()
    
    # Recreate the settings tab with fresh data and callback
    create_settings_tab(tab_settings, config_vars, camera_type_change_callback, update_create_session_callback)