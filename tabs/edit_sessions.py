import os
import json
import tkinter as tk
from tkinter import messagebox

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
    selected_file = {'name': None, 'data': None}

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
            files_with_uuid.sort(key=lambda x: (x[0] == '', x[0]))
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
        for widget in form_frame.winfo_children():
            widget.destroy()
        entries.clear()

    def populate_form(data):
        clear_form()
        row = 0
        id_cmd = data['command']['id_command']
        # Add Reset button at the top
        def reset_fields():
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

        # Place the label on the left and the reset button on the right, same row
        tk.Label(form_frame, text="Session Info", font=("Arial", 11, "bold")).grid(row=row, column=0, columnspan=1, sticky="w", pady=(0,5))
        reset_btn = tk.Button(form_frame, text="Reset Session State", command=reset_fields, bg="#f0ad4e", fg="black")
        reset_btn.grid(row=row, column=1, sticky="e", pady=(0,5), padx=(0,10))
        row += 1
        for key in ["uuid", "description", "date", "time", "process", "max_retries", "result", "message", "nb_try"]:
            tk.Label(form_frame, text=key+":").grid(row=row, column=0, sticky="e")
            val = id_cmd.get(key, "")
            ent = tk.Entry(form_frame, width=40)
            ent.insert(0, str(val))
            ent.grid(row=row, column=1, sticky="w")
            entries[('id_command', key)] = ent
            ent.bind('<FocusOut>', lambda e, k=key: save_json())
            ent.bind('<Return>', lambda e, k=key: save_json())
            row += 1
        for subcmd in ["eq_solving", "auto_focus", "infinite_focus", "calibration", "goto_solar", "goto_manual", "setup_camera", "setup_wide_camera"]:
            tk.Label(form_frame, text=subcmd, font=("Arial", 10, "bold")).grid(row=row, column=0, sticky="w", pady=(10,0))
            row += 1
            sub = data['command'].get(subcmd, {})
            for k, v in sub.items():
                tk.Label(form_frame, text="    "+k+":").grid(row=row, column=0, sticky="e")
                if k == 'do_action':
                    from tkinter import ttk
                    combo = ttk.Combobox(form_frame, values=["True", "False"], width=37, state="readonly")
                    combo.set("True" if v else "False")
                    combo.grid(row=row, column=1, sticky="w")
                    entries[(subcmd, k)] = combo
                    combo.bind('<<ComboboxSelected>>', lambda e, s=subcmd, kk=k: save_json())
                else:
                    ent = tk.Entry(form_frame, width=40)
                    ent.insert(0, str(v))
                    ent.grid(row=row, column=1, sticky="w")
                    entries[(subcmd, k)] = ent
                    ent.bind('<FocusOut>', lambda e, s=subcmd, kk=k: save_json())
                    ent.bind('<Return>', lambda e, s=subcmd, kk=k: save_json())
                row += 1

    def on_select(event):
        if selected_file['name'] and selected_file['data']:
            save_json()
        selection = listbox.curselection()
        if not selection:
            return
        fname = listbox.get(selection[0])
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
            messagebox.showwarning("No file selected", "Please select a session file to save.")
            return
        data = selected_file['data']
        if not data:
            messagebox.showerror("No data", "No session data loaded.")
            return
        id_cmd = data['command']['id_command']
        for key in ["uuid", "description", "date", "time", "process", "max_retries", "result", "message", "nb_try"]:
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
        try:
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
