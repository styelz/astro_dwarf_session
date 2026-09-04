import os
import json
import shutil
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from astro_dwarf_scheduler import LIST_ASTRO_DIR_DEFAULT
from ui.theme import status_color
from ui.widgets import card, section_header, hint_label

def overview_session_tab(parent_frame, refresh_setter=None):
    """Initializes the session overview tab. Optionally registers a refresh function for external use."""
    parent_frame.grid_rowconfigure(0, weight=1)
    parent_frame.grid_columnconfigure(0, weight=1, minsize=280)
    parent_frame.grid_columnconfigure(1, weight=2)

    list_card, list_inner = card(parent_frame)
    list_card.grid(row=0, column=0, sticky="nsew", padx=(12, 8), pady=12)
    list_inner.grid_rowconfigure(1, weight=1)
    list_inner.grid_columnconfigure(0, weight=1)

    section_header(list_inner, "Available Sessions").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

    json_listbox = tk.Listbox(list_inner, height=8, selectmode=tk.EXTENDED, relief="flat", highlightthickness=0)
    json_listbox.grid(row=1, column=0, columnspan=3, sticky="nsew")
    list_scroll = ttk.Scrollbar(list_inner, orient="vertical", command=json_listbox.yview)
    list_scroll.grid(row=1, column=3, sticky="ns")
    json_listbox.configure(yscrollcommand=list_scroll.set)

    toolbar = ttk.Frame(list_inner, style="Card.TFrame")
    toolbar.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(10, 0))
    toolbar.grid_columnconfigure(0, weight=1)
    toolbar.grid_columnconfigure(2, weight=1)
    hint_label(toolbar, "Double click session names to toggle.").grid(row=0, column=0, sticky="e", padx=(0, 8))
    select_button = ttk.Button(
        toolbar, text="Toggle Selected", command=lambda: select_session(json_listbox, json_text, select_button)
    )
    select_button.grid(row=0, column=1, padx=8)
    hint_label(toolbar, "Hold shift to select multiple sessions.").grid(row=0, column=2, sticky="w", padx=(8, 0))

    detail_card, detail_inner = card(parent_frame)
    detail_card.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=12)
    detail_inner.grid_rowconfigure(1, weight=1)
    detail_inner.grid_columnconfigure(0, weight=1)
    section_header(detail_inner, "Session details").grid(row=0, column=0, sticky="w", pady=(0, 8))

    json_text = tk.Text(detail_inner, state=tk.DISABLED, relief="flat", highlightthickness=0)
    json_text.grid(row=1, column=0, sticky="nsew")
    detail_scroll = ttk.Scrollbar(detail_inner, orient="vertical", command=json_text.yview)
    detail_scroll.grid(row=1, column=1, sticky="ns")
    json_text.configure(yscrollcommand=detail_scroll.set)

    json_listbox.bind('<<ListboxSelect>>', lambda event: on_json_select(event, json_listbox, json_text))
    json_listbox.bind('<Double-Button-1>', lambda event: select_session(json_listbox, json_text, refresh_json_list))

    def refresh_json_list():
        populate_json_list(json_listbox)
    refresh_json_list()
    if refresh_setter is not None:
        refresh_setter(refresh_json_list)
    return refresh_json_list

def populate_json_list(json_listbox):
    """Populates the listbox with JSON files from the Astro_Sessions folder, sorted by UUID."""
    json_listbox.delete(0, tk.END)
    
    # Get files from all session subdirectories
    from astro_dwarf_scheduler import LIST_ASTRO_DIR
    sessions_dir = LIST_ASTRO_DIR_DEFAULT["SESSIONS_DIR"]
    subdirs = {
        'main': {'path': sessions_dir, 'label': '', 'color': status_color('main'), 'font': None},
        'ToDo': {'path': LIST_ASTRO_DIR["TODO_DIR"], 'label': ' [ToDo]', 'color': status_color('ToDo'), 'font': None},
        'Current': {'path': os.path.join(sessions_dir, 'Current'), 'label': ' [Current]', 'color': status_color('Current'), 'font': None},
        'Done': {'path': os.path.join(sessions_dir, 'Done'), 'label': ' [Done]', 'color': status_color('Done'), 'font': None},
        'Error': {'path': os.path.join(sessions_dir, 'Error'), 'label': ' [Error]', 'color': status_color('Error'), 'font': None},
        'Results': {'path': os.path.join(sessions_dir, 'Results'), 'label': ' [Results]', 'color': status_color('Results'), 'font': None},
    }
    all_files = []

    # Collect all files with their metadata
    for key, info in subdirs.items():
        dirpath = info['path']
        label = info['label']
        if os.path.exists(dirpath):
            for fname in os.listdir(dirpath):
                if fname.endswith('.json'):
                    fpath = os.path.join(dirpath, fname)
                    try:
                        with open(fpath, 'r') as f:
                            data = json.load(f)
                        id_command = data.get('command', {}).get('id_command', {})
                        uuid = id_command.get('uuid', '')  # Extract UUID
                        date_str = id_command.get('date', '')
                        time_str = id_command.get('time', '')
                        # Combine date and time for sorting
                        datetime_str = f"{date_str} {time_str}"
                    except Exception:
                        uuid = ''
                        datetime_str = ''
                    # Add file metadata to the list
                    all_files.append((uuid, fname, datetime_str, dirpath, label, info['color'], info['font']))

    def parse_dt(s): 
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except:
            return None  # Invalid or missing date

    # Sort files by UUID first, then by datetime
#    all_files.sort(key=lambda x: (x[0] == '', x[0], x[2] == '', x[2]))
    # Sort files by datetime first , then by UUID
    all_files.sort(key=lambda x: (parse_dt(x[2]) is None, parse_dt(x[2]), x[0]))

    # Insert sorted files into the listbox
    json_listbox.file_origin_map = {}
    for uuid, fname, datetime_str, dirpath, label, color, font in all_files:
        display_name = fname + label
        json_listbox.insert(tk.END, display_name)
        if font:
            json_listbox.itemconfig(tk.END, foreground=color, font=font)
        else:
            json_listbox.itemconfig(tk.END, foreground=color)
        json_listbox.file_origin_map[display_name] = (dirpath, fname)

def on_json_select(event, json_listbox, json_text):
    """Triggered when a JSON file is selected, and displays its content."""
    selection = json_listbox.curselection()
    if selection:
        # Get the last selected item
        last_selected_index = selection[-1]
        selected_file = json_listbox.get(last_selected_index)
        # Determine origin
        file_origin_map = getattr(json_listbox, 'file_origin_map', {})
        if selected_file in file_origin_map:
            dirpath, fname = file_origin_map[selected_file]
            filepath = os.path.join(dirpath, fname)
            display_json_content(filepath, json_text)

def display_json_content(filepath, json_text):
    """Displays the content of the selected JSON file in the text area."""
    with open(filepath, 'r') as file:
        data = json.load(file)

    json_text.config(state=tk.NORMAL)
    json_text.delete(1.0, tk.END)
    # Extract 'id_command' details
    id_command = data['command']['id_command']
    description = id_command.get('description', 'N/A')
    date = id_command.get('date', 'N/A')
    time_ = id_command.get('time', 'N/A')
    status_ = id_command.get('process', 'N/A')
    # Insert description, date, and time
    json_text.insert(tk.END, f"Description: {description}\n")
    json_text.insert(tk.END, f"Date: {date}\n")
    json_text.insert(tk.END, f"Time: {time_}\n")
    json_text.insert(tk.END, f"Process: {status_}\n")
    # Now check each action and display details if 'do_action' is True
    command = data['command']
    # EQ Solving
    if command.get('eq_solving', {}).get('do_action', False):
        json_text.insert(tk.END, "\nEQ Solving:\n")
        json_text.insert(tk.END, f"  Wait Before: {command['eq_solving'].get('wait_before', 'N/A')}\n")
        json_text.insert(tk.END, f"  Wait After: {command['eq_solving'].get('wait_after', 'N/A')}\n")
    # Autofocus
    if command.get('auto_focus', {}).get('do_action', False):
        json_text.insert(tk.END, "\nAuto focus:\n")
        json_text.insert(tk.END, f"  Wait Before: {command['auto_focus'].get('wait_before', 'N/A')}\n")
        json_text.insert(tk.END, f"  Wait After: {command['auto_focus'].get('wait_after', 'N/A')}\n")
    # infinite_focus
    if command.get('infinite_focus', {}).get('do_action', False):
        json_text.insert(tk.END, "\nInfinite focus:\n")
        json_text.insert(tk.END, f"  Wait Before: {command['infinite_focus'].get('wait_before', 'N/A')}\n")
        json_text.insert(tk.END, f"  Wait After: {command['infinite_focus'].get('wait_after', 'N/A')}\n")
    # Calibration
    if command.get('calibration', {}).get('do_action', False):
        json_text.insert(tk.END, "\nCalibration:\n")
        json_text.insert(tk.END, f"  Wait Before: {command['calibration'].get('wait_before', 'N/A')}\n")
        json_text.insert(tk.END, f"  Wait After: {command['calibration'].get('wait_after', 'N/A')}\n")
    # Goto Solar
    if command.get('goto_solar', {}).get('do_action', False):
        json_text.insert(tk.END, "\nGoto Solar:\n")
        json_text.insert(tk.END, f"  Target: {command['goto_solar'].get('target', 'N/A')}\n")
        json_text.insert(tk.END, f"  Wait After: {command['goto_solar'].get('wait_after', 'N/A')}\n")
    # Goto Manual
    if command.get('goto_manual', {}).get('do_action', False):
        json_text.insert(tk.END, "\nGoto Manual:\n")
        json_text.insert(tk.END, f"  Target: {command['goto_manual'].get('target', 'N/A')}\n")
        json_text.insert(tk.END, f"  RA Coord: {command['goto_manual'].get('ra_coord', 'N/A')}\n")
        json_text.insert(tk.END, f"  Dec Coord: {command['goto_manual'].get('dec_coord', 'N/A')}\n")
        json_text.insert(tk.END, f"  Wait After: {command['goto_manual'].get('wait_after', 'N/A')}\n")
    # Setup Camera
    if command.get('setup_camera', {}).get('do_action', False):
        json_text.insert(tk.END, "\nSetup Camera:\n")
        setup_camera = command['setup_camera']
        json_text.insert(tk.END, f"  Exposure: {setup_camera.get('exposure', 'N/A')}\n")
        json_text.insert(tk.END, f"  Gain: {setup_camera.get('gain', 'N/A')}\n")
        json_text.insert(tk.END, f"  Binning: {setup_camera.get('binning', 'N/A')}\n")
        json_text.insert(tk.END, f"  IRCut: {setup_camera.get('ircut', 'N/A')}\n")
        json_text.insert(tk.END, f"  Count: {setup_camera.get('count', 'N/A')}\n")
        json_text.insert(tk.END, f"  Wait After: {setup_camera.get('wait_after', 'N/A')}\n")
    
    if command.get('setup_wide_camera', {}).get('do_action', False):
        json_text.insert(tk.END, "\nSetup Wide-Angle Camera:\n")
        setup_wide_camera = command['setup_wide_camera']
        json_text.insert(tk.END, f"  Exposure: {setup_wide_camera.get('exposure', 'N/A')}\n")
        json_text.insert(tk.END, f"  Gain: {setup_wide_camera.get('gain', 'N/A')}\n")
        json_text.insert(tk.END, f"  Count: {setup_wide_camera.get('count', 'N/A')}\n")
        json_text.insert(tk.END, f"  Wait After: {setup_wide_camera.get('wait_after', 'N/A')}\n")
    json_text.config(state=tk.DISABLED)

def select_session(json_listbox, json_text, select_button):
    # import directories
    from astro_dwarf_scheduler import LIST_ASTRO_DIR

    """Moves the selected JSON files to the ToDo folder."""

    selection = json_listbox.curselection()
    if selection:
        file_origin_map = getattr(json_listbox, 'file_origin_map', {})
        for index in selection:
            selected_file = json_listbox.get(index)
            if selected_file in file_origin_map:
                dirpath, fname = file_origin_map[selected_file]
                dir_base = os.path.basename(dirpath)
                # If file is in ToDo, Done, or Error, move it back to parent dir and reset values
                if dir_base in ("ToDo", "Done", "Error"):
                    parent_dir = os.path.dirname(dirpath)
                    dest_path = os.path.join(parent_dir, fname)
                    source_path = os.path.join(dirpath, fname)
                    try:
                        # Load the JSON data before moving
                        with open(source_path, 'r') as f:
                            data = json.load(f)
                        
                        # Reset the session values (same as "Reset Session State" button)
                        id_cmd = data['command']['id_command']
                        id_cmd['process'] = 'wait'
                        id_cmd['result'] = False
                        id_cmd['message'] = ''
                        id_cmd['nb_try'] = 1
                        
                        # Save the modified data to the destination
                        with open(dest_path, 'w') as f:
                            json.dump(data, f, indent=4)
                        
                        # Remove the original file
                        os.remove(source_path)
                        
                        #print(f"Moved {fname} back to {parent_dir} and reset session state.")
                    except Exception as e:
                        print(f"Error moving and resetting file {fname}: {e}")
                        # Try to move without reset if JSON modification fails
                        try:
                            shutil.move(source_path, dest_path)
                            #print(f"Moved {fname} back to {parent_dir} (without reset).")
                        except Exception as move_error:
                            print(f"Error moving file {fname}: {move_error}")
                else:
                    # Move file to ToDo as before
                    from astro_dwarf_scheduler import LIST_ASTRO_DIR
                    source_path = os.path.join(dirpath, fname)
                    destination_path = os.path.join(LIST_ASTRO_DIR["TODO_DIR"], fname)
                    try:
                        shutil.move(source_path, destination_path)
                        #print(f"Moved {fname} to ToDo folder.")
                    except Exception as e:
                        print(f"Error moving file {fname}: {e}")
        # Refresh the listbox after moving all files
        populate_json_list(json_listbox)
        # Clear the text area and disable the select button
        json_text.config(state=tk.NORMAL)
        json_text.delete(1.0, tk.END)
        json_text.config(state=tk.DISABLED)

