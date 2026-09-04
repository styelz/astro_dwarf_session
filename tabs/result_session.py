import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont
import json
import os
import csv
from datetime import datetime, timedelta
from ui.theme import apply_theme, fonts, load_appearance, palette, style_treeview_rows, sync_treeview_selection
from ui.widgets import card, section_header

# Directories
TIME_CHANGE_DAY = 18

# Define columns to display in Treeviews
columns_OK = ["Description", "Dwarf", "Starting", "Ending", 
           "Calibration", "Goto", "Target", 
           "RA", "Dec", "Lens", 
           "exposure", "gain", "IR", "count"]
columns_KO = ["Description", "Dwarf", "Starting", "Ending", 
           "Message", "Calibration", "Goto", "Target", 
           "RA", "Dec", "Lens", 
           "exposure", "gain", "IR", "count"]

def autosize_columns(treeview, padding, max_width_col = 0):
    for col in treeview["columns"]:
        max_width = tkFont.Font().measure(col)  # Start with the width of the header

        # Check each row to find the maximum width in the column
        for item in treeview.get_children():
            cell_value = treeview.set(item, col)
            cell_width = tkFont.Font().measure(cell_value)
            max_width = max(max_width, cell_width)

        if max_width_col !=0:
            max_width = min(max_width, max_width_col)
 
        # Set the column width based on the maximum width found
        treeview.column(col, width=max_width + padding)  # Add padding

def result_session_tab(parent_frame):
    parent_frame.grid_rowconfigure(1, weight=1)
    parent_frame.grid_rowconfigure(2, weight=1)
    parent_frame.grid_columnconfigure(0, weight=1)

    toolbar_card, top_frame = card(parent_frame)
    toolbar_card.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
    top_frame.grid_columnconfigure(1, weight=1)

    ttk.Label(top_frame, text="Observation file", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
    combobox = ttk.Combobox(top_frame, state="readonly")
    combobox.grid(row=0, column=1, sticky="ew")

    ok_card, ok_frame = card(parent_frame)
    ok_card.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
    ok_frame.grid_rowconfigure(1, weight=1)
    ok_frame.grid_columnconfigure(0, weight=1)
    section_header(ok_frame, "Sessions OK").grid(row=0, column=0, sticky="w", pady=(0, 8))

    ok_treeview = ttk.Treeview(ok_frame, columns=columns_OK, show='headings', height=10, cursor="hand2")
    default_width = 100
    for col in columns_OK:
        ok_treeview.heading(col, text=col)
        ok_treeview.column(col, anchor="center", width=default_width)
    ok_treeview.grid(row=1, column=0, sticky="nsew")
    ok_scroll = ttk.Scrollbar(ok_frame, orient="vertical", command=ok_treeview.yview)
    ok_scroll.grid(row=1, column=1, sticky="ns")
    ok_treeview.configure(yscrollcommand=ok_scroll.set)
    style_treeview_rows(ok_treeview)
    bind_result_treeview(ok_treeview)

    error_card, error_frame = card(parent_frame)
    error_card.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
    error_frame.grid_rowconfigure(1, weight=1)
    error_frame.grid_columnconfigure(0, weight=1)
    section_header(error_frame, "Error Sessions").grid(row=0, column=0, sticky="w", pady=(0, 8))

    error_treeview = ttk.Treeview(error_frame, columns=columns_KO, show='headings', height=10, cursor="hand2")
    for col in columns_KO:
        error_treeview.heading(col, text=col)
        error_treeview.column(col, anchor="center")
    error_treeview.grid(row=1, column=0, sticky="nsew")
    error_scroll = ttk.Scrollbar(error_frame, orient="vertical", command=error_treeview.yview)
    error_scroll.grid(row=1, column=1, sticky="ns")
    error_treeview.configure(yscrollcommand=error_scroll.set)
    style_treeview_rows(error_treeview)
    bind_result_treeview(error_treeview)

    # init results
    refresh_observation_list(combobox, ok_treeview, error_treeview)

    # Closure function for refreshing
    def refresh():
        refresh_observation_list(combobox, ok_treeview, error_treeview)


    def delete_selected_file():
        selected_file = combobox.get()
        if not selected_file:
            return
        from astro_dwarf_scheduler import LIST_ASTRO_DIR
        RESULTS_DIR = LIST_ASTRO_DIR["SESSIONS_DIR"] + '/Results'
        RESULTS_LIST = LIST_ASTRO_DIR["SESSIONS_DIR"]
        file_path = os.path.join(RESULTS_DIR, selected_file)
        list_path = os.path.join(RESULTS_LIST, "results_list.txt")
        if os.path.exists(file_path):
            import tkinter.messagebox as messagebox
            if messagebox.askyesno("Delete File", f"Are you sure you want to delete '{selected_file}'?"):
                try:
                    os.remove(file_path)
                    os.remove(list_path)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not delete file: {e}")
        refresh()

    update_button = ttk.Button(top_frame, text="Update Results", command=lambda: refresh())
    update_button.grid(row=0, column=2, padx=(10, 5))
    delete_button = ttk.Button(top_frame, text="Delete File", command=delete_selected_file, style="Danger.TButton")
    delete_button.grid(row=0, column=3)

    # Autosize the columns based on the content
    padding = 1
    max_width_col = 40
    autosize_columns(ok_treeview, padding, max_width_col)
    padding = 1
    max_width_col = 40
    autosize_columns(error_treeview, padding, max_width_col)

    combobox.bind("<<ComboboxSelected>>", lambda event: on_file_select(event, combobox, ok_treeview, error_treeview))

    return refresh

def get_observation_files():
    from astro_dwarf_scheduler import LIST_ASTRO_DIR

    # Directories
    RESULTS_DIR = LIST_ASTRO_DIR["SESSIONS_DIR"] + '/Results'

    files = [f for f in os.listdir(RESULTS_DIR) if f.endswith('.csv')]
    files.sort(reverse=True)
    return files

def load_csv_data(filename):
    from astro_dwarf_scheduler import LIST_ASTRO_DIR

    # Directories
    RESULTS_DIR = LIST_ASTRO_DIR["SESSIONS_DIR"] + '/Results'

    ok_data = []
    error_data = []
    with open(os.path.join(RESULTS_DIR, filename), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            
            row["Description"] = row.get("description")
            row["Dwarf"] = row.get("dwarf")
            starting_date = row.get("starting_date")
            row["Starting"] = starting_date[11:] if starting_date else ""
            processed_date = row.get("processed_date")
            row["Ending"] = processed_date[11:] if processed_date else ""
            row["Calibration"] = "Done" if row.get("calibration") == "True" else ""
            if row.get("goto_solar") == "True" :
                row["Goto"] = "Solar"
            elif row.get("goto_manual") == "True" :
                row["Goto"] = "Manual"
            else:
                row["Goto"] = ""
            row["Target"] = row.get("target")
            row["RA"] = row.get("ra_coord")
            row["Dec"] = row.get("dec_coord")
            if row.get("Tele Astro") == "True" :
                row["Lens"] = "Tele"
            elif row.get("Wide Angle") == "True" :
                row["Lens"] = "Wide"
            else:
                row["Lens"] = ""
            if row.get("dwarf") == "D2" :
                row["IR"] = "Cut" if row.get("IR") == "0" else "Pass"
            else:
                if row.get("IR") == "0":
                    row["IR"] = "VIS"
                elif row.get("IR") == "1":
                    row["IR"] = "ASTRO"
                else:
                    row["IR"] = "DUO B."
            if row.get("count") == "0":
                row["Lens"] = ""
                row["count"] = ""
                row["exposure"] = ""
                row["gain"] = ""
                row["IR"] = ""
            if row["result"] == "True":
                ok_data.append(row)
            else:
                row["Message"] = row["message"].replace("Error during execution: ", "").replace("Action failed at step: ", "Error: ")
                error_data.append(row)
    ok_data.sort(key=lambda x: x["starting_date"])
    error_data.sort(key=lambda x: x["starting_date"])
    return ok_data, error_data

def _display_value(row, *keys):
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return "—"


def bind_result_treeview(treeview):
    treeview.bind("<ButtonRelease-1>", lambda event: on_result_row_click(event, treeview), add="+")
    treeview.bind("<<TreeviewSelect>>", lambda _event: sync_treeview_selection(treeview), add="+")


def on_result_row_click(event, treeview):
    if treeview.identify_region(event.x, event.y) not in ("cell", "tree"):
        return
    item_id = treeview.identify_row(event.y)
    if not item_id:
        return
    row = getattr(treeview, "_row_data", {}).get(item_id)
    if not row:
        columns = treeview["columns"]
        values = treeview.item(item_id, "values")
        row = dict(zip(columns, values))
    show_session_detail(treeview, row)


def show_session_detail(anchor, row):
    parent = anchor.winfo_toplevel()
    dialog = tk.Toplevel(parent)
    dialog.title("Session details")
    dialog.transient(parent)
    dialog.resizable(False, False)
    apply_theme(dialog, load_appearance())

    body, inner = card(dialog)
    body.pack(fill="both", expand=True, padx=12, pady=12)
    inner.grid_columnconfigure(1, weight=1)

    title = _display_value(row, "Description", "description", "Target", "target")
    is_ok = str(row.get("result", "")).lower() == "true"
    status_text = "Succeeded" if is_ok else "Error"
    status_color = palette["log_success"] if is_ok else palette["log_error"]

    header = ttk.Frame(inner, style="Card.TFrame")
    header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
    header.grid_columnconfigure(0, weight=1)
    ttk.Label(header, text=title, style="Heading.TLabel").grid(row=0, column=0, sticky="w")
    status = tk.Label(
        header,
        text=f" {status_text} ",
        fg=status_color,
        bg=palette["card"],
        font=fonts["subheading"],
    )
    status._theme_keep_fg = True
    status.grid(row=0, column=1, sticky="e")

    sections = [
        ("Session", [
            ("Description", ("Description", "description")),
            ("Dwarf", ("Dwarf", "dwarf")),
            ("Started", ("starting_date", "Starting")),
            ("Ended", ("processed_date", "Ending")),
        ]),
        ("Target", [
            ("Calibration", ("Calibration",)),
            ("Goto", ("Goto",)),
            ("Target", ("Target", "target")),
            ("RA", ("RA", "ra_coord")),
            ("Dec", ("Dec", "dec_coord")),
        ]),
        ("Camera", [
            ("Lens", ("Lens",)),
            ("Exposure", ("exposure",)),
            ("Gain", ("gain",)),
            ("IR", ("IR",)),
            ("Count", ("count",)),
        ]),
    ]

    row_index = 1
    for heading, fields in sections:
        ttk.Label(inner, text=heading, style="Subheading.TLabel").grid(
            row=row_index, column=0, columnspan=2, sticky="w", pady=(8, 4)
        )
        row_index += 1
        for label, keys in fields:
            ttk.Label(inner, text=label, style="Muted.TLabel").grid(
                row=row_index, column=0, sticky="nw", padx=(0, 16), pady=3
            )
            ttk.Label(inner, text=_display_value(row, *keys), style="Card.TLabel", wraplength=360, justify="left").grid(
                row=row_index, column=1, sticky="w", pady=3
            )
            row_index += 1

    message = _display_value(row, "Message", "message")
    if message != "—":
        ttk.Label(inner, text="Message", style="Subheading.TLabel").grid(
            row=row_index, column=0, columnspan=2, sticky="w", pady=(12, 4)
        )
        row_index += 1
        inner.grid_rowconfigure(row_index, weight=1)
        message_box = tk.Text(
            inner,
            wrap="word",
            height=min(8, max(3, message.count("\n") + 2)),
            relief="flat",
            highlightthickness=0,
            borderwidth=0,
            bg=palette["input_bg"],
            fg=palette["log_error"] if not is_ok else palette["fg"],
            font=fonts["body"],
            padx=8,
            pady=8,
        )
        message_box.insert("1.0", message)
        message_box.configure(state="disabled")
        message_box.grid(row=row_index, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        row_index += 1

    ttk.Button(inner, text="Close", style="Accent.TButton", command=dialog.destroy).grid(
        row=row_index, column=0, columnspan=2, sticky="e", pady=(12, 0)
    )

    dialog.update_idletasks()
    width = max(dialog.winfo_reqwidth(), 460)
    height = dialog.winfo_reqheight()
    max_h = max(parent.winfo_height() - 80, 360)
    height = min(height, max_h)
    x = parent.winfo_rootx() + max((parent.winfo_width() - width) // 2, 0)
    y = parent.winfo_rooty() + max((parent.winfo_height() - height) // 2, 0)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    dialog.grab_set()
    dialog.focus_set()


def update_treeview(treeview, data, columns):
    treeview.delete(*treeview.get_children())
    treeview._row_data = {}
    style_treeview_rows(treeview)
    for index, row in enumerate(data):
        tag = "even" if index % 2 == 0 else "odd"
        item_id = treeview.insert("", tk.END, values=[row.get(col, "") for col in columns], tags=(tag,))
        treeview._row_data[item_id] = row
    sync_treeview_selection(treeview)

def on_file_select(event, combobox, ok_treeview, error_treeview):
    selected_file = combobox.get()
    if selected_file:
        ok_data, error_data = load_csv_data(selected_file)
        update_treeview(ok_treeview, ok_data, columns_OK)
        update_treeview(error_treeview, error_data, columns_KO)

def refresh_observation_list(combobox, ok_treeview, error_treeview):
    analyze_files()
    # Load initial data
    files = get_observation_files()
    combobox['values'] = files
    if files:
        combobox.set(files[0])
        ok_data, error_data = load_csv_data(files[0])
        update_treeview(ok_treeview, ok_data, columns_OK)
        update_treeview(error_treeview, error_data, columns_KO)
    else:
        combobox.set("")  # Clear the combobox
        # Clear the treeviews and display only column headers
        update_treeview(ok_treeview, [], columns_OK)
        update_treeview(error_treeview, [], columns_KO)

def get_observation_night(starting_date):
    """Determine the observation night for a given date and time."""
    observation_datetime = datetime.strptime(starting_date, '%Y-%m-%d %H:%M:%S')
    if observation_datetime.hour < TIME_CHANGE_DAY:
        observation_datetime -= timedelta(days=1)  # Shift to the previous night
    observation_night = observation_datetime.strftime('%Y-%m-%d')
    return observation_night

# Function to analyze JSON files and generate CSV
def analyze_files():
    from astro_dwarf_scheduler import LIST_ASTRO_DIR

    # Directories
    RESULTS_DIR = LIST_ASTRO_DIR["SESSIONS_DIR"] + '/Results'

    processed_files = load_processed_files()

    # Paths to Done and Error directories
    for status_dir in ['Done', 'Error']:
        dir_path = os.path.join(LIST_ASTRO_DIR["SESSIONS_DIR"], status_dir)
        if not os.path.exists(dir_path):
            continue

        for filename in os.listdir(dir_path):
            if filename in processed_files:
                continue  # Skip if already processed
            if not filename.endswith('.json'):
                continue  # Skip if not a JSON file
            if filename.startswith('.keep'):
                continue  # Skip if not a JSON file

            file_path = os.path.join(dir_path, filename)
            with open(file_path, 'r') as file:
                data = json.load(file)

            # Attempt to get starting_date from the JSON data
            starting_date = data["command"]["id_command"].get("starting_date")

            # If starting_date is not found, extract it from the filename
            if not starting_date:
                # Extract date and time from filename, e.g., "2024-10-20-17-29-45-Mosaic Pane 4.json"
                date_parts = filename.split('-')[:3]  # Get the first three parts for year, month, day
                time_parts = filename.split('-')[3:6]  # Get the next three parts for hours, minutes, seconds
                starting_date = '-'.join(date_parts) + ' ' + ':'.join(time_parts)  # Combine with time part
                # Strip any whitespace from starting_date
                starting_date = starting_date.strip()

                try:
                    # Convert to a datetime object to ensure the format is correct
                    datetime.strptime(starting_date, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    print(f"Invalid date format in filename: {filename}")
                    continue  # Skip this file if the date format is invalid

            typeDwarf = data["command"]["id_command"].get("dwarf")
            if not typeDwarf:
                typeDwarf = "-"

            observation_night = get_observation_night(starting_date)
    
            # Prepare the CSV data based on JSON content
            csv_data = {
                'id': data["command"]["id_command"]["uuid"],
                'description': data["command"]["id_command"]["description"],
                'dwarf': typeDwarf,
                'starting_date': starting_date,
                'processed_date': data["command"]["id_command"].get("processed_date", ""),
                'result': data["command"]["id_command"]["result"],
                'message': data["command"]["id_command"]["message"],
                'calibration': data["command"].get("calibration", {}).get("do_action", False),
                'goto_solar': data["command"].get("goto_solar", {}).get("do_action", False),
                'goto_manual': data["command"].get("goto_manual", {}).get("do_action", False),
                'target': data["command"].get("goto_manual", {}).get("target", ""),
                'ra_coord': data["command"].get("goto_manual", {}).get("ra_coord", ""),
                'dec_coord': data["command"].get("goto_manual", {}).get("dec_coord", ""),
                'Tele Astro': data["command"].get("setup_camera", {}).get("do_action", False),
                'Wide Angle': data["command"].get("setup_wide_camera", {}).get("do_action", False),
                'exposure': data["command"].get("setup_camera", {}).get("exposure", ""),
                'gain': data["command"].get("setup_camera", {}).get("gain", ""),
                'IR': data["command"].get("setup_camera", {}).get("ircut", ""),
                'count': data["command"].get("setup_camera", {}).get("count", ""),
            }

            # Write to CSV file
            csv_filename = f'results_session_night_{observation_night}.csv'
            csv_filepath = os.path.join(RESULTS_DIR, csv_filename)
            write_to_csv(csv_filepath, csv_data)

            save_processed_file(filename)

# Helper function to write data to CSV
def write_to_csv(csv_path, csv_data):
    headers = csv_data.keys()
    file_exists = os.path.exists(csv_path)

    with open(csv_path, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        writer.writerow(csv_data)

# Function to load already processed filenames
def load_processed_files():
    from astro_dwarf_scheduler import LIST_ASTRO_DIR

    RESULTS_LIST_PATH = os.path.join(LIST_ASTRO_DIR["SESSIONS_DIR"], 'results_list.txt')

    if os.path.exists(RESULTS_LIST_PATH):
        with open(RESULTS_LIST_PATH, 'r') as file:
            return set(line.strip() for line in file.readlines())

    return set()

# Function to save processed filename
def save_processed_file(filename):
    from astro_dwarf_scheduler import LIST_ASTRO_DIR

    RESULTS_LIST_PATH = os.path.join(LIST_ASTRO_DIR["SESSIONS_DIR"], 'results_list.txt')

    with open(RESULTS_LIST_PATH, 'a') as file:
        file.write(filename + '\n')
