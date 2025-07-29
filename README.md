
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
<!--
Field notes:
- date: "YYYY-MM-DD" (minimum date to launch processing)
- time: "HH:MM:SS"
- process: "wait" | "pending" | "ended"
- max_retries: integer (max retries on error)
- result: boolean (result after processing)
- message: object (result message)
- nb_try: integer (number of tries)
- processed_date: "YYYY-MM-DD HH:MM:SS" (date of processing)
- calibration.wait_before/wait_after: seconds
- goto_manual.ra_coord: decimal or "HH:MM:SS"
- goto_manual.dec_coord: decimal or "DD:MM:SS"
- setup_camera.binning: "0"=4k, "1"=2k
- setup_camera.IRCut: D2: "0"=IRCut, "1"=IRPass; D3: "0"=VIS, "1"=Astro, "2"=DUAL BAND
-->

{
  "command": {
    "id_command": {
      "uuid": "uuid",
      "description": "text",
      "date": "YYYY-MM-DD",
      "time": "HH:MM:SS",
      "process": "wait",
      "max_retries": 2,
      "result": false,
      "message": {},
      "nb_try": 1,
      "processed_date": "YYYY-MM-DD HH:MM:SS"
    },
    "calibration": {
      "do_action": false,
      "wait_before": 0,
      "wait_after": 0
    },
    "goto_solar": {
      "do_action": false,
      "target": "planet_name",
      "wait_after": 0
    },
    "goto_manual": {
      "do_action": false,
      "target": "target_name",
      "ra_coord": "HH:MM:SS",
      "dec_coord": "DD:MM:SS",
      "wait_after": 0
    },
    "setup_camera": {
      "do_action": false,
      "exposure": "exposure_strvalue",
      "gain": "gain_strvalue",
      "binning": "0",
      "IRCut": "0",
      "count": 1,
      "wait_after": 0
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
