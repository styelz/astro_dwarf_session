import configparser
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser

from geopy.geocoders import Nominatim
from geopy.geocoders import Photon
from timezonefinder import TimezoneFinder
from geopy.exc import GeocoderInsufficientPrivileges

CONFIG_INI_FILE = 'config.ini'

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

        latitude = location.latitude
        longitude = location.longitude

        #Get the timezone using TimezoneFinder
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lat=latitude, lng=longitude)

        return latitude, longitude, timezone_str

    except GeocoderInsufficientPrivileges as e:
        print(f"Error: {e} - You do not have permission to access this resource.")

        # Attempt to switch agent and retry
        if agent == 1:
            print("Switching to Photon geocoder for the next attempt.")
            return get_location_data(address, agent=2)  # Retry with the second agent
        else:
            messagebox.showinfo("Error", "Can't found your location data!")
            return None, None, None

    except Exception as e:
        print(f"Error: {e}")

        # Attempt to switch agent and retry
        if agent == 1:
            print("Switching to Photon geocoder for the next attempt.")
            return get_location_data(address, agent=2)  # Retry with the second agent
        else:
            messagebox.showinfo("Error", "Can't found your location data!")
            return None, None, None

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
    config.read(CONFIG_INI_FILE)
    return config['CONFIG']

def save_config(config_data):
    config = configparser.ConfigParser()
    config['CONFIG'] = config_data
    with open(CONFIG_INI_FILE, 'w') as configfile:
        config.write(configfile)

# Create the settings tab
def create_settings_tab(tab_settings, settings_vars):

    config = load_config()
    # --- Modern scrollable frame setup ---
    container = ttk.Frame(tab_settings)
    container.grid(row=0, column=0, sticky='nsew')
    tab_settings.grid_rowconfigure(0, weight=1)
    tab_settings.grid_columnconfigure(0, weight=1)

    canvas = tk.Canvas(container, highlightthickness=0)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    def _on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
        # Make the scrollable_frame width always match the canvas width
        canvas_width = event.width
        canvas.itemconfig("frame", width=canvas_width)

    scrollable_frame.bind(
        "<Configure>", _on_frame_configure
    )
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
        ("Help", "Find longitude and lattitude in Google Map by CTRL + Right Click"),
        ("Longitude", "longitude"),
        ("Latitude", "latitude"),
        ("Help", "The timezone value can be found here https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"),
        ("Timezone", "timezone"),
        ("BLE PSD", "ble_psd"),
        ("BLE STA SSID", "ble_sta_ssid"),
        ("BLE STA Password", "ble_sta_pwd"),
        ("Help", "Use to Connect to Stellarium, let them blank if you are using default config"),
        ("Stellarium IP", "stellarium_ip"),
        ("Stellarium Port", "stellarium_port"),
        ("Help", "The following values are the default values use in the Create Session Tabs"),
        ("Exposure", "exposure"),
        ("Gain", "gain"),
        ("Help IR Cut", "For D2: 0=IR Cut 1=IR Pass, For D3: 0=VIS 1=ASTRO 2=DUAL BAND"),
        ("IR Cut", "ircut"),
        ("Help Binning", "0: 4k 1: 2k"),
        ("Binning", "binning"),
        ("Count", "count")
    ]

    # Add location button at the top
    location_button = tk.Button(scrollable_frame, text="Find your location data from your address or Enter them manually", command=lambda: find_location(settings_vars))
    location_button.grid(row=0, column=0, columnspan=2, pady=(15, 15), padx=10, sticky='ew')

    grid_row = 1
    for field, key in settings_fields:
        index = key.find("http")
        if not "Help" in field:
            label = tk.Label(scrollable_frame, width=22, text=field, anchor='e')
            var = tk.StringVar(value=config.get(key, ''))
            entry = tk.Entry(scrollable_frame, textvariable=var)
            settings_vars[key] = var
            label.grid(row=grid_row, column=0, sticky='e', padx=(10,6), pady=4)
            entry.grid(row=grid_row, column=1, sticky='ew', padx=(0,14), pady=4)
            scrollable_frame.grid_columnconfigure(1, weight=1)
        elif index != -1:
            url = key[index:].strip()
            link_label = tk.Label(scrollable_frame, text=key[:index], fg="blue", cursor="hand2", anchor='w')
            # Align the link label to the data entry column
            link_label.grid(row=grid_row, column=1, sticky='w', padx=(0,14), pady=4)
            link_label.config(font=("Arial", 12, "underline"))
            link_label.bind("<Button-1>", lambda e, url=url: open_link(url))
        else:
            help_Label = tk.Label(scrollable_frame, width=60, text=key, anchor='w', fg="#555")
            # Align the help label to the data entry column
            help_Label.grid(row=grid_row, column=1, sticky='w', padx=(0,14), pady=4)
        grid_row += 1

    # Save button at the bottom
    save_button = tk.Button(scrollable_frame, text="Save", command=lambda: save_settings(settings_vars))
    save_button.grid(row=grid_row, column=0, columnspan=2, pady=20, padx=10, sticky='ew')

def save_settings(settings_vars):
    config_data = {key: var.get() for key, var in settings_vars.items()}
    save_config(config_data)
    messagebox.showinfo("Settings", "Configuration saved successfully!")
