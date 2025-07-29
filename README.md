
# astro_dwarf_session

## 🚀 Automatic Sessions for Dwarf II & Dwarf 3

**astro_dwarf_session** is a powerful tool for automating imaging sessions with Dwarf II and Dwarf 3 telescopes. It supports both console and GUI modes, enabling fully unattended astrophotography. The project is open source and welcomes contributions!

---

## ✨ Features
- Automated execution of imaging sessions from JSON files
- Bluetooth and WiFi connection support (with robust error handling)
- Console and modern GUI interfaces (Tkinter-based)
- Real-time log output with color and emoji indicators
- Flexible session configuration (goto, calibration, camera setup, etc.)
- Results analysis and session management tools
- Color-coded session status and file management
- Multi-device configuration support

---

## 📄 Session File Format

Session files are JSON documents placed in the `./Astro_Sessions/ToDo/` directory. Example and template files are provided in the `./Astro_Sessions/` directory.

**Example JSON structure:**

```json
{ 
  "command" : {
    "id_command" : {
        "uuid" : "uuid",
        "description": "text",
        "date" : date,                      // "YYYY-MM-DD" minimun date to launch the processing, can be later if a processing is in progress
        "time" : time,                      // "HH:MM:SS"
        "process" : {wait, pending, ended}, // "wait" to be proccessed
        "max_retries": 2,                   // maximun number of retries in case of errors
        "result" : boolean,                 // result after processing
        "message" : {...},                  // result message
        "nb_try": 1,                        // number of tries done
        "processed_date": date              // YYYY-MM-DD HH:MM:SS date of proccessing
    }
    "calibration" : {
        "do_action" : false,                // true to do the action
        "wait_before" : time_sec,
        "wait_after" : time_sec
    }
    "goto_solar" :  {
        "do_action" : false,
        "target" : planet_name,
        "wait_after" : time_sec
    }
    "goto_manual" :  {
        "do_action" : false,
        "target" : target_name,
        "ra_coord" : ra_coord,              // decimal value or HH:MM:SS
        "dec_coord" : dec_coord,            // decimal value or DD:MM:SS
        "wait_after" : time_sec
    }
    "setup_camera" :  {
        "do_action" : false,
        "exposure" : exposure_strvalue,
        "gain" : gain_strvalue,
        "binning" : binning_val,            // "0": 4k - "1": 2k
        "IRCut" : IRCut_val,                // For D2: "0"=IRCut, "1"=IRPass. For D3: "0"=VIS Filter, "1"=Astro Filter, "2"=DUAL BAND Filter
        "count" : nb_image,
        "wait_after" : time_sec
    }
  }
}
```

---

## ⚙️ Installation

1. **Clone this repository:**
   ```sh
   git clone https://github.com/styelz/astro_dwarf_session.git
   cd astro_dwarf_session
   ```

2. **Install dependencies:**
   ```sh
   python -m pip install -r requirements.txt
   python -m pip install -r requirements-local.txt --target .
   ```
   > **Note:** The [dwarf_python_api](https://github.com/styelz/dwarf_python_api) library must be installed locally in the root path of this project. The `--target .` argument is required. **Don't miss the dot at the end!**

3. **Configure WiFi:**
   - Edit `config.ini` with your WiFi SSID and password to enable your Dwarf device on your local network.

4. **Prepare your session files:**
   - Manually create session files (GUI session creation and editing is available).
   - Place your files in the `./Astro_Sessions/ToDo/` subdirectory. They will be processed automatically.

---

## 🖥️ Usage

- **Console version:**
  ```sh
  python ./astro_dwarf_scheduler.py [--ip <ip_value>] [--id 2|3]
  ```
- **GUI version:**
  ```sh
  python ./astro_dwarf_session_UI.py
  ```

### Parameters
- `--ip <ip_value>`: IP address of the Dwarf device (required if not previously connected via Bluetooth)
- `--id 2|3`: Dwarf model (2 or 3)

If parameters are not set, the program will attempt to connect via Bluetooth. A web page will open for Bluetooth pairing. If Bluetooth fails, you will be prompted to retry for 30 seconds, or after an error, for 60 seconds.

- If parameters are correct, the console will proceed without Bluetooth prompts.
- The console can run headless as long as it can connect to the Dwarf device.
- You can start the connection on Dwarfium (if available) to allow processing to continue without manual intervention.

---

## 🗂️ Directory Structure
- `Astro_Sessions/ToDo/` — Place your session files here for processing
- `Astro_Sessions/Done/` — Processed sessions
- `Astro_Sessions/Error/` — Sessions with errors
- `Astro_Sessions/Results/` — Results output
- `Astro_Sessions/Current/` — Currently running session

---

## 🛠️ Troubleshooting
- Ensure your Dwarf device is on the same WiFi network as your computer.
- Check `config.ini` for correct WiFi credentials.
- Review the console or GUI log output for error messages and retry if needed.
- For Bluetooth issues, ensure your system supports BLE and try pairing again.

---

## 🤝 Contributing
Pull requests and suggestions are welcome! Please open an issue or submit a PR for improvements, bug fixes, or new features.

---

## 📜 License
This project is licensed under the MIT License.

---

## 🌌 Clear skies and good night — let your Dwarf work for you! ✨
