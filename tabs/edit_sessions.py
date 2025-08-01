import os
import json
import tkinter as tk
from tkinter import messagebox
import re

def edit_sessions_tab(parent_tab, session_dir, refresh_callback=None):
    frame = tk.Frame(parent_tab)
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    label = tk.Label(frame, text="Available Sessions (JSON files):", font=("Arial", 12))
    label.pack(anchor="w")

    listbox = tk.Listbox(frame, width=40, height=20, selectmode=tk.EXTENDED)
    listbox.pack(side=tk.LEFT, fill=tk.Y, padx=(0,10))

    scrollbar = tk.Scrollbar(frame, orient="vertical", command=listbox.yview)
    scrollbar.pack(side=tk.LEFT, fill=tk.Y)
    listbox.config(yscrollcommand=scrollbar.set)

    # --- Add scrollable form frame (scrollbar on right) ---
    form_canvas = tk.Canvas(frame, borderwidth=0, highlightthickness=0)
    form_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    form_scrollbar = tk.Scrollbar(frame, orient="vertical", command=form_canvas.yview)
    form_scrollbar.pack(side=tk.LEFT, fill=tk.Y, padx=(0,0))
    form_canvas.configure(yscrollcommand=form_scrollbar.set)
    # Create a frame inside the canvas
    form_frame = tk.Frame(form_canvas)
    form_window = form_canvas.create_window((0, 0), window=form_frame, anchor="nw")

    frame.pack_propagate(False)
    form_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    form_scrollbar.pack_forget()
    form_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def on_frame_configure(event):
        form_canvas.configure(scrollregion=form_canvas.bbox("all"))
    form_frame.bind("<Configure>", on_frame_configure)
    def _on_mousewheel(event):
        form_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    form_canvas.bind_all("<MouseWheel>", _on_mousewheel)

    entries = {}
    form_widgets = {}  # Cache for form structure
    selected_file = {'name': None, 'data': None}
    save_pending = {'flag': False}
    form_built = {'flag': False}  # Track if form structure is built
    
    def natural_sort_key(text):
        """Convert a string into a list of mixed strings and integers for natural sorting."""
        return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', text)]

    def get_json_files_sorted_by_uuid(directory):
        files_with_uuid = []
        if os.path.exists(directory):
            for fname in os.listdir(directory):
                if fname.endswith('.json'):
                    fpath = os.path.join(directory, fname)
                    try:
                        with open(fpath, 'r') as f:
                            data = json.load(f)
                        uuid = data.get('command', {}).get('id_command', {}).get('uuid', '')
                    except Exception:
                        uuid = ''
                    files_with_uuid.append((uuid, fname))
            # Use natural sorting for UUIDs
            files_with_uuid.sort(key=lambda x: (x[0] == '', natural_sort_key(x[0])))
        return [fname for uuid, fname in files_with_uuid]

    def refresh_list():
        listbox.delete(0, tk.END)
        for fname in get_json_files_sorted_by_uuid(session_dir):
            listbox.insert(tk.END, fname)
        clear_form()
        selected_file['name'] = None
        selected_file['data'] = None
        if refresh_callback:
            refresh_callback()

    def clear_form():
        # Only clear values, not destroy widgets
        if form_built['flag']:
            for key, widget in entries.items():
                if hasattr(widget, 'delete'):
                    widget.delete(0, tk.END)
                elif hasattr(widget, 'set'):
                    widget.set('')
        else:
            # First time - destroy everything
            for widget in form_frame.winfo_children():
                widget.destroy()
            entries.clear()
            form_widgets.clear()
        save_pending['flag'] = False

    def schedule_save():
        """Schedule a save operation to reduce frequent saves"""
        if not save_pending['flag']:
            save_pending['flag'] = True
            form_frame.after(300, perform_save)  # Reduced delay

    def perform_save():
        """Perform the actual save operation"""
        if save_pending['flag']:
            save_pending['flag'] = False
            save_json()

    def build_form_structure(data):
        """Build the form structure once and reuse it"""
        if form_built['flag']:
            return  # Form already built
        
        clear_form()
        row = 0
        
        # Add Reset button at the top
        header_frame = tk.Frame(form_frame)
        header_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0,5))
        header_frame.grid_columnconfigure(0, weight=1)
        
        tk.Label(header_frame, text="Session Info", font=("Arial", 11, "bold")).grid(row=0, column=0, sticky="w")
        reset_btn = tk.Button(header_frame, text="Reset Session State", bg="#f0ad4e", fg="black")
        reset_btn.grid(row=0, column=1, sticky="e", padx=(0,10))
        form_widgets['reset_btn'] = reset_btn
        row += 1
        
        # Build id_command fields
        for key in ["uuid", "description", "date", "time", "process", "max_retries", "result", "message", "nb_try"]:
            label = tk.Label(form_frame, text=key+":")
            label.grid(row=row, column=0, sticky="e")
            ent = tk.Entry(form_frame, width=40)
            ent.grid(row=row, column=1, sticky="w")
            entries[('id_command', key)] = ent
            form_widgets[('id_command', key)] = (label, ent)
            ent.bind('<FocusOut>', lambda e: schedule_save())
            ent.bind('<Return>', lambda e: schedule_save())
            row += 1
        
        # Build subcmd sections - we'll populate dynamically
        form_widgets['subcmd_start_row'] = row
        form_built['flag'] = True

    def populate_subcmd_fields(data, start_row):
        """Populate subcmd fields dynamically"""
        # Clear existing subcmd widgets
        for key in list(entries.keys()):
            if key[0] != 'id_command':
                widget = entries[key]
                if hasattr(widget, 'destroy'):
                    widget.destroy()
                del entries[key]
        
        # Clear subcmd form widgets
        for key in list(form_widgets.keys()):
            if isinstance(key, tuple) and key[0] != 'id_command':
                widgets = form_widgets[key]
                if isinstance(widgets, tuple):
                    for w in widgets:
                        if hasattr(w, 'destroy'):
                            w.destroy()
                del form_widgets[key]
        
        row = start_row
        for subcmd in ["eq_solving", "auto_focus", "infinite_focus", "calibration", "goto_solar", "goto_manual", "setup_camera", "setup_wide_camera"]:
            sub = data['command'].get(subcmd, {})
            if not sub:  # Skip if subcmd doesn't exist
                continue
                
            label = tk.Label(form_frame, text=subcmd, font=("Arial", 10, "bold"))
            label.grid(row=row, column=0, sticky="w", pady=(10,0))
            form_widgets[f'{subcmd}_header'] = label
            row += 1
            
            for k, v in sub.items():
                sub_label = tk.Label(form_frame, text="    "+k+":")
                sub_label.grid(row=row, column=0, sticky="e")
                
                if k == 'do_action':
                    from tkinter import ttk
                    combo = ttk.Combobox(form_frame, values=["True", "False"], width=37, state="readonly")
                    combo.grid(row=row, column=1, sticky="w")
                    entries[(subcmd, k)] = combo
                    form_widgets[(subcmd, k)] = (sub_label, combo)
                    combo.bind('<<ComboboxSelected>>', lambda e: schedule_save())
                else:
                    ent = tk.Entry(form_frame, width=40)
                    ent.grid(row=row, column=1, sticky="w")
                    entries[(subcmd, k)] = ent
                    form_widgets[(subcmd, k)] = (sub_label, ent)
                    ent.bind('<FocusOut>', lambda e: schedule_save())
                    ent.bind('<Return>', lambda e: schedule_save())
                row += 1

    def populate_form(data):
        """Populate form with data - optimized version"""
        # Build form structure if not built
        build_form_structure(data)
        
        # Set reset button command
        def reset_fields():
            id_cmd = data['command']['id_command']
            id_cmd['process'] = 'wait'
            id_cmd['result'] = False
            id_cmd['message'] = ''
            id_cmd['nb_try'] = 1
            # Update the form fields visually
            entries[('id_command', 'process')].delete(0, tk.END)
            entries[('id_command', 'process')].insert(0, 'wait')
            entries[('id_command', 'result')].delete(0, tk.END)
            entries[('id_command', 'result')].insert(0, 'False')
            entries[('id_command', 'message')].delete(0, tk.END)
            entries[('id_command', 'message')].insert(0, '')
            entries[('id_command', 'nb_try')].delete(0, tk.END)
            entries[('id_command', 'nb_try')].insert(0, '1')
            save_json()
        
        form_widgets['reset_btn'].config(command=reset_fields)
        
        # Populate id_command fields
        id_cmd = data['command']['id_command']
        for key in ["uuid", "description", "date", "time", "process", "max_retries", "result", "message", "nb_try"]:
            if ('id_command', key) in entries:
                widget = entries[('id_command', key)]
                widget.delete(0, tk.END)
                val = id_cmd.get(key, "")
                widget.insert(0, str(val))
        
        # Populate subcmd fields
        populate_subcmd_fields(data, form_widgets['subcmd_start_row'])
        
        # Set subcmd values
        for subcmd in ["eq_solving", "auto_focus", "infinite_focus", "calibration", "goto_solar", "goto_manual", "setup_camera", "setup_wide_camera"]:
            sub = data['command'].get(subcmd, {})
            for k, v in sub.items():
                if (subcmd, k) in entries:
                    widget = entries[(subcmd, k)]
                    if k == 'do_action':
                        widget.set("True" if v else "False")
                    else:
                        if hasattr(widget, 'delete'):
                            widget.delete(0, tk.END)
                            widget.insert(0, str(v))

    def on_select(event):
        # Save any pending changes before switching files
        if save_pending['flag']:
            perform_save()
        
        selection = listbox.curselection()
        if not selection:
            return
            
        fname = listbox.get(selection[0])
        
        # Don't reload if same file is selected
        if selected_file['name'] == fname:
            return
        
        # Show loading indicator
        if not form_built['flag']:
            loading_label = tk.Label(form_frame, text="Loading...", font=("Arial", 12))
            loading_label.pack()
            form_frame.update_idletasks()
        
        fpath = os.path.join(session_dir, fname)
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
            selected_file['name'] = fname
            selected_file['data'] = data
            populate_form(data)
        except Exception as e:
            clear_form()
            tk.Label(form_frame, text=f"Error loading file: {e}", fg="red").pack()
            selected_file['name'] = None
            selected_file['data'] = None

    def save_json():
        fname = selected_file['name']
        if not fname:
            return
        data = selected_file['data']
        if not data:
            return
            
        try:
            id_cmd = data['command']['id_command']
            for key in ["uuid", "description", "date", "time", "process", "max_retries", "result", "message", "nb_try"]:
                if ('id_command', key) in entries:
                    val = entries[('id_command', key)].get()
                    if key in ["max_retries", "nb_try"]:
                        try: val = int(val)
                        except: val = 0
                    elif key == "result":
                        val = val.lower() == 'true'
                    id_cmd[key] = val
                    
            for subcmd in ["eq_solving", "auto_focus", "infinite_focus", "calibration", "goto_solar", "goto_manual", "setup_camera", "setup_wide_camera"]:
                sub = data['command'].get(subcmd, {})
                for k in sub.keys():
                    if (subcmd, k) in entries:
                        widget = entries[(subcmd, k)]
                        if k == 'do_action':
                            val = widget.get()
                            val = val == 'True'
                        else:
                            val = widget.get()
                            if isinstance(val, str) and val.lower() in ['true', 'false']:
                                val = val.lower() == 'true'
                            else:
                                try:
                                    if '.' in val:
                                        val = float(val)
                                    else:
                                        val = int(val)
                                except:
                                    pass
                        sub[k] = val
                        
            fpath = os.path.join(session_dir, fname)
            with open(fpath, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save file: {e}")

    listbox.bind('<<ListboxSelect>>', on_select)
    refresh_list()

    button_frame = tk.Frame(parent_tab)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

    def delete_selected_files():
        selections = listbox.curselection()
        if not selections:
            messagebox.showwarning("No file selected", "Please select one or more session files to delete.")
            return
        files_to_delete = [listbox.get(i) for i in selections]
        if not files_to_delete:
            return
        count = len(files_to_delete)
        if not messagebox.askyesno("Delete Files", f"Are you sure you want to delete the selected file(s)? ({count} file{'s' if count != 1 else ''} will be deleted)"):
            return
        errors = []
        for fname in files_to_delete:
            fpath = os.path.join(session_dir, fname)
            try:
                if os.path.exists(fpath):
                    os.remove(fpath)
            except Exception as e:
                errors.append(f"{fname}: {e}")
        refresh_list()
        if errors:
            messagebox.showerror("Delete Error", "Some files could not be deleted:\n" + '\n'.join(errors))

    delete_btn = tk.Button(button_frame, text="Delete File(s)", command=delete_selected_files)
    delete_btn.pack(side=tk.LEFT, padx=5)
    refresh_btn = tk.Button(button_frame, text="Refresh List", command=refresh_list)
    refresh_btn.pack(side=tk.LEFT, padx=5)

    return refresh_list
