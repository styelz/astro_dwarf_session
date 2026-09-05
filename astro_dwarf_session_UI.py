from fractions import Fraction
import os
import shutil
import socket
import subprocess
import time
import threading
import io
import json
import ctypes
import signal
import logging
import traceback
import webbrowser
import requests
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk
from astro_dwarf_scheduler import check_and_execute_commands, start_connection, start_STA_connection, setup_new_config
from dwarf_python_api.lib.dwarf_utils import perform_stopAstroPhoto, perform_start_autofocus, read_longitude, read_latitude, perform_disconnect, perform_time, perform_GoLive, unset_HostMaster, set_HostMaster, perform_stop_goto, perform_calibration, start_polar_align, motor_action, perform_powerdown, perform_reboot
try:
    from dwarf_python_api.lib.dwarf_utils import (
        perform_open_camera,
        perform_open_widecamera,
        perform_enter_photo_mode,
    )
except ImportError:
    def perform_open_camera(*args, **kwargs):
        return False
    def perform_open_widecamera(*args, **kwargs):
        return False
    def perform_enter_photo_mode(*args, **kwargs):
        return False
from dwarf_python_api.lib.dwarf_utils import perform_powerOpenRGB, perform_powerCloseRGB, perform_powerIndOn, perform_powerIndOff
try:
    from dwarf_python_api.lib.dwarf_utils import perform_get_device_state_info
except ImportError:
    def perform_get_device_state_info(*args, **kwargs):
        return False
from dwarf_python_api.lib.websockets_utils import get_client_status
try:
    from dwarf_python_api.lib.websockets_utils import request_command_interrupt, clear_command_interrupt
except ImportError:
    def request_command_interrupt():
        return None
    def clear_command_interrupt():
        return None
from video_preview import (
    RTSP_FIRST_FRAME_TIMEOUT,
    rtsp_raw_ffmpeg_command,
    should_open_camera_on_preview_event,
    should_start_preview_on_lens_toggle,
    split_ppm_frame,
)

# import data for config.py
import dwarf_python_api.get_config_data as config_py
# The config value for dwarf_id is offset by -1 (stored as one less than the actual ID).
# the value return by get_config_data must be used with these functions
from dwarf_python_api.get_config_data import config_to_dwarf_id_int

import logging
from dwarf_python_api.lib.my_logger import NOTICE_LEVEL_NUM

from dwarf_session import verify_action, stop_telescope_activity
from device_stop import can_start_action, keep_action_until_stop_finishes, should_send_device_stop
from tabs import settings
from tabs import create_session
from tabs import overview_session
from tabs import result_session
from ui.theme import apply_theme, apply_ui_appearance, load_appearance, palette, fonts, spacing, style_log_text, close_date_entry_popups, theme_window_frame, win32_hwnd, set_pointer_blocked, refresh_disabled_pointer
from ui.widgets import (
    VIDEO_ASPECT,
    ScrollingLabel,
    VideoHoverOverlay,
    appearance_toggle,
    card,
    fit_image_in_box,
    hex_to_rgb,
    hide_native_titlebar,
    hint_label,
    install_mousewheel,
    section_header,
    status_label,
    tab_bar,
    title_bar,
)
from app_version import get_app_version

# import directories
from astro_dwarf_scheduler import CONFIG_DEFAULT, BASE_DIR, LIST_ASTRO_DIR_DEFAULT, get_json_files_sorted
import os

# Devices and sessions directories now use BASE_DIR from scheduler (AppData-aware)
DEVICES_DIR = os.path.join(BASE_DIR, "Devices_Sessions")
DEVICES_FILE = os.path.join(DEVICES_DIR, 'list_devices.txt')
WINDOW_NAME = "Astro Dwarf Scheduler"


def _window_title():
    try:
        return f"{WINDOW_NAME}  v{get_app_version()}"
    except Exception:
        return WINDOW_NAME

def load_configuration():
    # Ensure the devices directory exists
    os.makedirs(DEVICES_DIR, exist_ok=True)
    
    # Ensure the list_devices.txt file exists
    if not os.path.exists(DEVICES_FILE):
        with open(DEVICES_FILE, 'w') as file:
            pass  # Create an empty file

    # load configs in DEVICES_FILE
    devices = [CONFIG_DEFAULT]
    with open(DEVICES_FILE, 'r+') as file:
        devices = [line.strip() for line in file.readlines()]
    
    # Combine CONFIG_DEFAULT with the devices from the file, avoiding duplicates
    devices = list({CONFIG_DEFAULT, *devices})

    return devices

def check_new_configuration(config_name):
    """check a configuration exist and recreate the required directory structure if not present."""

    isPresent = False

    if config_name == CONFIG_DEFAULT: 
        return True

    # Check if the config already exists in the file
    with open(DEVICES_FILE, 'r+') as file:
        devices = [line.strip() for line in file.readlines()]
        if config_name in devices:
            isPresent = True

    if isPresent:
        # Create the main configuration directory if it doesn't exist
        config_dir = os.path.join(DEVICES_DIR, config_name)
        os.makedirs(config_dir, exist_ok=True)
    
        SESSIONS_DIR = os.path.join(config_dir, 'Astro_Sessions')
        # Ensure the devices directory exists
        os.makedirs(SESSIONS_DIR, exist_ok=True)
    
        # Create the subdirectories if they don't exist
        for dir_key, subdir in LIST_ASTRO_DIR_DEFAULT.items():
            if dir_key != "SESSIONS_DIR":
                full_path = os.path.join(SESSIONS_DIR, subdir)
                os.makedirs(full_path, exist_ok=True)

    return isPresent

def add_new_configuration(config_name):
    """Add a new configuration and create the required directory structure."""

    config_dir = os.path.join(DEVICES_DIR, config_name)
    
    # Ensure the devices directory exists
    os.makedirs(DEVICES_DIR, exist_ok=True)
    
    # Ensure the list_devices.txt file exists
    if not os.path.exists(DEVICES_FILE):
        with open(DEVICES_FILE, 'w') as file:
            pass  # Create an empty file

    # Check if the config already exists in the file
    with open(DEVICES_FILE, 'r+') as file:
        devices = [line.strip() for line in file.readlines()]
        if config_name not in devices:
            # Add the configuration name to the file if not present
            file.write(config_name + '\n')
    
    # Create the main configuration directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)

    SESSIONS_DIR = os.path.join(config_dir, 'Astro_Sessions')
    # Ensure the devices directory exists
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    
    # Create the subdirectories if they don't exist
    for dir_key, subdir in LIST_ASTRO_DIR_DEFAULT.items():
        if dir_key != "SESSIONS_DIR":
            full_path = os.path.join(SESSIONS_DIR, subdir)
            os.makedirs(full_path, exist_ok=True)

    print(f"Configuration '{config_name}' added successfully with required directory structure.")
    
# Tooltip class
class Tooltip:
    """Create a tooltip for a given widget."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self._after_id = None
        self.widget.bind("<Enter>", self._on_enter, add="+")
        self.widget.bind("<Leave>", self._on_leave, add="+")

    def _on_enter(self, event=None):
        self._cancel_pending()
        self._after_id = self.widget.after(400, self.show_tooltip)

    def _on_leave(self, event=None):
        self._cancel_pending()
        self.hide_tooltip()

    def _cancel_pending(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def show_tooltip(self, event=None):
        self._after_id = None
        if self.tooltip_window is not None or not self.text:
            return
        try:
            if not self.widget.winfo_exists():
                return
        except tk.TclError:
            return

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_attributes("-topmost", True)
        self.tooltip_window.configure(bg=palette["border"])
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            background=palette["tooltip_bg"],
            foreground=palette["tooltip_fg"],
            font=fonts["body"],
            borderwidth=0,
            padx=spacing["md"],
            pady=spacing["sm"],
        )
        label.pack(padx=1, pady=1)
        self.tooltip_window.update_idletasks()

        tip_w = self.tooltip_window.winfo_reqwidth()
        tip_h = self.tooltip_window.winfo_reqheight()
        widget_x = self.widget.winfo_rootx()
        widget_y = self.widget.winfo_rooty()
        widget_h = self.widget.winfo_height()
        x = widget_x
        y = widget_y + widget_h + 6
        screen_w = self.widget.winfo_screenwidth()
        screen_h = self.widget.winfo_screenheight()
        if y + tip_h > screen_h - 8:
            y = widget_y - tip_h - 6
        if x + tip_w > screen_w - 8:
            x = max(8, screen_w - tip_w - 8)
        if x < 8:
            x = 8
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        self._prevent_tooltip_activation()

    def _prevent_tooltip_activation(self):
        """Keep the parent button hovered; a normal Toplevel steals active state."""
        try:
            hwnd = win32_hwnd(self.tooltip_window)
            if not hwnd:
                return
            gwl_exstyle = -20
            ws_ex_noactivate = 0x08000000
            ws_ex_toolwindow = 0x00000080
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, gwl_exstyle)
            user32.SetWindowLongW(hwnd, gwl_exstyle, style | ws_ex_noactivate | ws_ex_toolwindow)
        except Exception:
            pass

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except tk.TclError:
                pass
            self.tooltip_window = None

class TextHandler(logging.Handler):
    """
    This class allows logging to be directed to a Tkinter Text widget.
    """
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.text_widget.config(state=tk.NORMAL)
    
    def emit(self, record):
        # Format the log message
        msg = self.format(record)
        # Determine color and emoji based on log level
        if record.levelno >= logging.ERROR:
            tag = "error"
            emoji = "✗ "
        elif record.levelno == logging.WARNING:
            tag = "warning"
            emoji = "⚠ "
        elif record.levelno == logging.INFO:
            tag = "info"
            emoji = "ℹ "
        elif record.levelno == 25:
            tag = "success"
            emoji = "✓ "
        else:
            tag = "default"
            emoji = "⇒ "

        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, emoji + msg + "\n", tag)
        self.text_widget.yview(tk.END)

# GUI Application class
class AstroDwarfSchedulerApp(tk.Tk):
    VIDEO_STARTING_STATUS = "Starting stream, please wait"

    def _is_dwarf_connected(self):
        """True when the scheduler still holds a live WebSocket to the telescope."""
        if not getattr(self, "scheduler_running", False):
            return False
        if getattr(self, "_scheduler_stopping", False):
            return False
        if getattr(self, "_scheduler_connecting", False):
            return False
        try:
            status = get_client_status()
            if isinstance(status, str):
                try:
                    status = json.loads(status)
                except Exception:
                    return False
            if not isinstance(status, dict):
                return False
            if status.get("error"):
                return False
            return "fullStatus" in status
        except Exception:
            return False

    def _client_full_status(self):
        try:
            status = get_client_status()
            if isinstance(status, str):
                try:
                    status = json.loads(status)
                except Exception:
                    return {}
            if not isinstance(status, dict) or status.get("error"):
                return {}
            return status.get("fullStatus", status) or {}
        except Exception:
            return {}

    def _read_light_states(self):
        full = self._client_full_status()
        return full.get("PowerIndicatorDwarf"), full.get("RgbIndicatorDwarf")

    def _lights_are_on(self, power=None, rgb=None):
        """True if either light is on, False if known off, None if not yet reported."""
        if power is None and rgb is None:
            power, rgb = self._read_light_states()
        known = [bool(value) for value in (power, rgb) if value is not None]
        if not known:
            return None
        return any(known)

    def _refresh_lights_button(self):
        if not hasattr(self, "toggle_lights_button"):
            return
        on = self._lights_are_on()
        if on is True:
            text, tip = "Turn Lights Off", "Lights are on. Click to turn them off."
        elif on is False:
            text, tip = "Turn Lights On", "Lights are off. Click to turn them on."
        else:
            text, tip = "Toggle Lights", "Light state is not known yet. Click to query the scope and toggle."
        if str(self.toggle_lights_button.cget("text")) != text:
            self.toggle_lights_button.config(text=text)
        if hasattr(self, "toggle_lights_tooltip"):
            self.toggle_lights_tooltip.text = tip

    def _discover_light_state(self, timeout=1.5):
        """Wait for connect cache, then ask the device if still unknown."""
        deadline = time.time() + timeout
        while True:
            on = self._lights_are_on()
            if on is not None:
                return on
            if time.time() >= deadline:
                break
            time.sleep(0.1)
        try:
            perform_get_device_state_info()
        except Exception:
            pass
        deadline = time.time() + timeout
        while True:
            on = self._lights_are_on()
            if on is not None or time.time() >= deadline:
                return on
            time.sleep(0.1)

    def _config_data(self):
        try:
            return config_py.get_config_data() or {}
        except Exception:
            return {}

    def _dwarf_ip(self):
        return self._config_data().get("ip") or "127.0.0.1"

    def _dwarf_id_int(self):
        dwarf_id = self._config_data().get("dwarf_id") or 2
        try:
            return config_to_dwarf_id_int(dwarf_id)
        except Exception:
            return 2

    def _preview_is_wide(self):
        """True when live preview should use the wide-angle lens (ch1)."""
        return getattr(self, "_preview_lens", "tele") == "wide"

    def _uses_rtsp_live(self):
        """Dwarf 3 / Mini use RTSP; Dwarf II uses HTTP JPEG on :8092."""
        return self._dwarf_id_int() >= 3

    def _ensure_live_preview_mode(self, switch_lens=False):
        """Open the camera for live view. Never call during imaging."""
        if getattr(self, "session_running", False):
            return
        if not self._is_dwarf_connected():
            self.log("Telescope not connected; waiting for live stream", level="warning")
            return
        if not switch_lens:
            try:
                if perform_GoLive():
                    self.log("Left astro mode for live view", level="success")
            except Exception as e:
                self.log(f"Go Live error: {e}", level="warning")
            try:
                if perform_enter_photo_mode():
                    self.log("Entered photo/live mode", level="success")
                else:
                    self.log("Photo/live mode was not entered", level="warning")
            except Exception as e:
                self.log(f"Photo mode error: {e}", level="warning")
        self._open_preview_camera()

    def _open_preview_camera(self):
        """Open the tele or wide camera that matches the live-preview lens."""
        wide = self._preview_is_wide()
        open_camera = perform_open_widecamera if wide else perform_open_camera
        lens = "wide" if wide else "tele"
        try:
            if open_camera():
                self.log(f"Opened {lens} camera for live preview", level="success")
            else:
                self.log(f"Open {lens} camera failed or was skipped", level="warning")
        except Exception as e:
            self.log(f"Open camera error: {e}", level="error")
        self._rtsp_transport = "tcp"

    def _set_video_status(self, text, clear_image=True):
        widgets = [getattr(self, "video_canvas", None)]
        expand = getattr(self, "_video_expand_canvas", None)
        if expand is not None:
            widgets.append(expand)
        try:
            for widget in widgets:
                if widget is None:
                    continue
                wrap = 0
                try:
                    wrap = max(widget.winfo_width() - 16, 200)
                except tk.TclError:
                    wrap = 280
                if clear_image:
                    widget.config(image="", text=text, wraplength=wrap)
                else:
                    widget.config(text=text, wraplength=wrap)
            if clear_image:
                self._video_photo = None
                self._video_expand_photo = None
                self._video_last_image = None
                self._video_pending_image = None
        except Exception:
            pass

    def _show_stream_starting(self):
        self.after(0, lambda: self._set_video_status(self.VIDEO_STARTING_STATUS))

    def _resolve_video_stream_url(self):
        dwarf_ip = self._dwarf_ip()
        wide = self._preview_is_wide()
        if self._uses_rtsp_live():
            path = "ch1/stream0" if wide else "ch0/stream0"
            self.video_stream_url = f"rtsp://{dwarf_ip}/{path}"
        else:
            path = "secondstream" if wide else "mainstream"
            self.video_stream_url = f"http://{dwarf_ip}:8092/{path}"
        return self.video_stream_url

    def _video_session_active(self):
        return bool(getattr(self, "session_running", False))

    def _video_should_retry(self):
        """Keep trying while a session is live, or while connected live preview is on."""
        if getattr(self, "_stop_video_stream", True):
            return False
        if self._video_session_active():
            return True
        if self._is_dwarf_connected():
            return True
        started = getattr(self, "_video_preview_started_at", 0) or 0
        return (time.time() - started) < 25

    def _tcp_port_open(self, host, port, timeout=1.2):
        sock = socket.socket()
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
            return True
        except Exception:
            return False
        finally:
            try:
                sock.close()
            except Exception:
                pass

    def _find_ffmpeg(self):
        return shutil.which("ffmpeg")

    def _stop_ffmpeg(self):
        proc = getattr(self, "_ffmpeg_proc", None)
        self._ffmpeg_proc = None
        if proc is None:
            return
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass
        try:
            proc.kill()
        except Exception:
            pass
        def reap():
            pid = getattr(proc, "pid", None)
            if os.name == "nt" and pid:
                try:
                    kwargs = {
                        "stdout": subprocess.DEVNULL,
                        "stderr": subprocess.DEVNULL,
                        "timeout": 2,
                    }
                    if hasattr(subprocess, "CREATE_NO_WINDOW"):
                        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], **kwargs)
                except Exception:
                    pass
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait(timeout=2)
            except Exception:
                pass
        threading.Thread(target=reap, daemon=True).start()

    def _video_stream_is_available(self, url, timeout=1.2):
        """True when the live endpoint is actually serving, or RTSP may still come up."""
        if url.startswith("rtsp://"):
            if self._tcp_port_open(self._dwarf_ip(), 554, timeout):
                return True
            # D3 RTSP can be UDP-only; try ffmpeg during the retry window.
            return self._video_should_retry()
        response = None
        try:
            response = requests.get(url, stream=True, timeout=(timeout, timeout))
            if response.status_code != 200:
                return False
            for chunk in response.iter_content(chunk_size=1024):
                return bool(chunk)
            return False
        except Exception:
            return False
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
        response = None
        try:
            response = requests.get(url, stream=True, timeout=(timeout, timeout))
            if response.status_code != 200:
                return False
            for chunk in response.iter_content(chunk_size=1024):
                return bool(chunk)
            return False
        except Exception:
            return False
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass

    def _iter_mjpeg_chunks(self, source, chunk_size=32768):
        if hasattr(source, "iter_content"):
            yield from source.iter_content(chunk_size=chunk_size)
            return
        while not getattr(self, "_stop_video_stream", False) and not getattr(self, "_reconnect_video_stream", False):
            chunk = source.read(chunk_size)
            if not chunk:
                break
            yield chunk

    def _decode_preview_frame(self, frame):
        from PIL import Image

        image = Image.open(io.BytesIO(frame))
        image.load()
        if image.mode != "RGB":
            image = image.convert("RGB")
        return image

    def _queue_video_frame(self, image):
        """Keep only the newest frame so Tk never paints a backlog."""
        if getattr(self, "_stop_video_stream", False) or getattr(self, "_quitting", False):
            return
        self._video_pending_image = image
        if getattr(self, "_video_flush_scheduled", False):
            return
        self._video_flush_scheduled = True
        self.after(0, self._flush_video_frame)

    def _flush_video_frame(self):
        image = getattr(self, "_video_pending_image", None)
        self._video_pending_image = None
        self._video_flush_scheduled = False
        if image is not None:
            self.update_video_canvas(image)
        if getattr(self, "_video_pending_image", None) is not None:
            if not getattr(self, "_video_flush_scheduled", False):
                self._video_flush_scheduled = True
                self.after(0, self._flush_video_frame)

    def _consume_mjpeg_source(self, source, current_url, idle_timeout=8):
        """Read JPEG frames from an MJPEG byte source. Returns True if a frame arrived."""
        bytes_data = bytearray()
        last_update = 0
        connect_time = time.time()
        got_frame = False
        for chunk in self._iter_mjpeg_chunks(source):
            if getattr(self, "_stop_video_stream", False):
                print("Stopping video stream worker")
                break
            if getattr(self, "_reconnect_video_stream", False):
                break
            if chunk:
                bytes_data.extend(chunk)
            while True:
                start = bytes_data.find(b"\xff\xd8")
                if start == -1:
                    if len(bytes_data) > 1:
                        bytes_data[:] = bytes_data[-1:]
                    else:
                        bytes_data.clear()
                    break
                end = bytes_data.find(b"\xff\xd9", start + 2)
                if end == -1:
                    if start > 0:
                        bytes_data[:] = bytes_data[start:]
                    if len(bytes_data) > 2_000_000:
                        bytes_data[:] = bytes_data[-64:]
                    break
                jpg = bytes(bytes_data[start : end + 2])
                del bytes_data[: end + 2]
                now = time.time()
                if now - last_update > 0.07:
                    last_update = now
                    try:
                        self._queue_video_frame(self._decode_preview_frame(jpg))
                    except Exception as e:
                        print(f"Error decoding video frame: {e}")
                        continue
                    if not got_frame:
                        got_frame = True
                        self.log(
                            f"First video frame from {current_url}",
                            level="success",
                        )
            if not got_frame and (time.time() - connect_time) > idle_timeout:
                break
        return got_frame

    def _consume_ppm_source(self, source, current_url, idle_timeout=8):
        """Read uncompressed PPM frames. Returns True if a frame arrived."""
        bytes_data = bytearray()
        last_update = 0
        connect_time = time.time()
        got_frame = False
        for chunk in self._iter_mjpeg_chunks(source, chunk_size=262144):
            if getattr(self, "_stop_video_stream", False):
                print("Stopping video stream worker")
                break
            if getattr(self, "_reconnect_video_stream", False):
                break
            if chunk:
                bytes_data.extend(chunk)
            if len(bytes_data) > 24_000_000:
                bytes_data[:] = bytes_data[-1024:]
            while True:
                frame, rest = split_ppm_frame(bytes_data)
                if frame is None:
                    if rest is not bytes_data:
                        bytes_data[:] = rest
                    break
                now = time.time()
                if now - last_update > 0.07:
                    last_update = now
                    try:
                        image = self._decode_preview_frame(frame)
                    except Exception as e:
                        print(f"Error decoding video frame: {e}")
                    else:
                        self._queue_video_frame(image)
                        if not got_frame:
                            got_frame = True
                            self.log(
                                f"First video frame from {current_url}",
                                level="success",
                            )
                bytes_data[:] = rest
            if not got_frame and (time.time() - connect_time) > idle_timeout:
                break
        return got_frame

    def _open_http_mjpeg(self, url):
        stream = requests.get(url, stream=True, timeout=(5, 3))
        if stream.status_code != 200:
            stream.close()
            raise requests.exceptions.HTTPError(f"HTTP {stream.status_code} for {url}")
        return stream

    def _open_rtsp_raw(self, url):
        ffmpeg = self._find_ffmpeg()
        if not ffmpeg:
            raise RuntimeError(
                "Dwarf 3 live view is RTSP. Install ffmpeg and keep it on PATH."
            )
        transport = getattr(self, "_rtsp_transport", "tcp") or "tcp"
        kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.DEVNULL,
            "bufsize": 10**7,
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.Popen(
            rtsp_raw_ffmpeg_command(ffmpeg, url, transport),
            **kwargs,
        )
        self._ffmpeg_proc = proc
        return proc.stdout

    def _stop_idle_video_preview(self, status="Click to start the stream"):
        """Leave preview off without retrying or logging that the stream is down."""
        self._stop_video_stream = True
        self._reconnect_video_stream = False
        self._stop_ffmpeg()
        self.after(0, lambda: self._set_video_status(status))

    def _video_wait(self, seconds):
        """Sleep in short slices so stop/reconnect flags are noticed quickly."""
        deadline = time.time() + seconds
        while time.time() < deadline:
            if getattr(self, "_stop_video_stream", False):
                return False
            if getattr(self, "_reconnect_video_stream", False):
                return False
            if not self._video_should_retry():
                return False
            time.sleep(0.1)
        return True

    def reconnect_video_preview(self):
        """Drop the current pull so the worker opens a fresh socket."""
        self._stop_video_stream = False
        self._video_preview_started_at = time.time()
        if getattr(self, "_video_worker_running", False):
            self._reconnect_video_stream = True
            self._stop_ffmpeg()
            self.log("Reconnecting video stream")
            self._show_stream_starting()
            return
        self.start_video_preview(ensure_live=False)

    def start_video_preview(self, ensure_live=True):
        try:
            from PIL import Image  # noqa: F401
        except ImportError:
            self.after(0, lambda: self._set_video_status("Install Pillow for video preview."))
            return

        self._stop_video_stream = False
        self._video_preview_started_at = time.time()
        self._resolve_video_stream_url()
        self._show_stream_starting()

        if ensure_live and not self._video_session_active():
            self._request_live_mode = True

        if getattr(self, "_video_worker_running", False):
            self._reconnect_video_stream = True
            return

        def video_stream_worker():
            self._video_worker_running = True
            print("Starting video stream worker")
            announced_url = False

            while not getattr(self, "_stop_video_stream", False):
                self._reconnect_video_stream = False
                current_url = self._resolve_video_stream_url()
                if getattr(self, "_request_live_mode", False) or getattr(self, "_request_lens_switch", False):
                    switch_lens = bool(getattr(self, "_request_lens_switch", False))
                    live_mode = bool(getattr(self, "_request_live_mode", False))
                    self._request_live_mode = False
                    self._request_lens_switch = False
                    stream_up = self._video_stream_is_available(current_url)
                    if should_open_camera_on_preview_event(
                        live_mode=live_mode,
                        lens_switch=switch_lens,
                        stream_up=stream_up,
                    ):
                        self._ensure_live_preview_mode(switch_lens=False)
                    self._rtsp_transport = "tcp"
                    current_url = self._resolve_video_stream_url()
                if current_url != getattr(self, "_logged_video_url", None):
                    announced_url = False

                in_session = self._video_session_active()
                if current_url.startswith("rtsp://") and not self._find_ffmpeg():
                    self._stop_idle_video_preview(
                        "Install ffmpeg for Dwarf 3 live preview"
                    )
                    self.log(
                        "Dwarf 3 live view is RTSP (rtsp://IP/ch0/stream0). ffmpeg was not found on PATH.",
                        level="error",
                    )
                    break

                if not self._video_stream_is_available(current_url):
                    if in_session or self._video_should_retry():
                        self.after(
                            0,
                            lambda: self._set_video_status(self.VIDEO_STARTING_STATUS),
                        )
                        self._video_wait(2 if in_session else 1.5)
                        if getattr(self, "_stop_video_stream", False):
                            self.after(0, lambda: self._set_video_status("Video stream is off"))
                            break
                        if getattr(self, "_reconnect_video_stream", False):
                            continue
                        if not self._video_should_retry():
                            self._stop_idle_video_preview()
                            break
                        continue
                    self._stop_idle_video_preview()
                    break

                if not announced_url:
                    announced_url = True
                    self._logged_video_url = current_url
                    self.log(f"Video stream: {current_url}")

                stream = None
                try:
                    self.after(0, lambda: self._set_video_status(self.VIDEO_STARTING_STATUS))
                    if current_url.startswith("rtsp://"):
                        stream = self._open_rtsp_raw(current_url)
                        got_frame = self._consume_ppm_source(
                            stream, current_url, idle_timeout=RTSP_FIRST_FRAME_TIMEOUT
                        )
                    else:
                        stream = self._open_http_mjpeg(current_url)
                        got_frame = self._consume_mjpeg_source(stream, current_url)
                    if current_url.startswith("rtsp://") and not got_frame:
                        current = getattr(self, "_rtsp_transport", "tcp")
                        self._rtsp_transport = "udp" if current == "tcp" else "tcp"
                except requests.exceptions.RequestException:
                    pass
                except Exception as e:
                    if not getattr(self, "_stop_video_stream", False):
                        print(f"Video stream error: {e}")
                        self.log(f"Video stream error: {e}", level="warning")
                finally:
                    self._stop_ffmpeg()
                    if stream is not None and hasattr(stream, "close"):
                        try:
                            stream.close()
                        except Exception:
                            pass

                if getattr(self, "_stop_video_stream", False):
                    self.after(0, lambda: self._set_video_status("Video stream is off"))
                    break

                if getattr(self, "_reconnect_video_stream", False):
                    continue

                if self._video_session_active() or self._video_should_retry():
                    self.after(0, lambda: self._set_video_status(self.VIDEO_STARTING_STATUS))
                    self._video_wait(2)
                    continue

                self._stop_idle_video_preview()
                break

            self._video_worker_running = False
            self._stop_ffmpeg()
            print("Video stream worker stopped")
            if (
                not getattr(self, "_stop_video_stream", True)
                and self._video_session_active()
            ):
                self.after(0, lambda: self.start_video_preview(ensure_live=False))

        threading.Thread(target=video_stream_worker, daemon=True).start()

    def update_video_canvas(self, frame):
        if getattr(self, "_stop_video_stream", True) or not self._is_dwarf_connected():
            return
        try:
            from PIL import Image

            if isinstance(frame, Image.Image):
                image = frame
            elif isinstance(frame, (bytes, bytearray)):
                image = self._decode_preview_frame(frame)
            else:
                image = frame
            if image.mode != "RGB":
                image = image.convert("RGB")
            self._video_last_image = image
            self._paint_video_surfaces()
        except Exception as e:
            print(f"Error updating video canvas: {e}")

    def _paint_video_surfaces(self):
        image = getattr(self, "_video_last_image", None)
        if image is None:
            return
        expand = getattr(self, "_video_expand_canvas", None)
        maximized = getattr(self, "_video_expand_mode", None) == "maximized"
        if not maximized:
            self._paint_video_widget(self.video_canvas, "_video_photo", image, 320, 180)
        if expand is None:
            return
        try:
            if expand.winfo_exists():
                self._paint_video_widget(expand, "_video_expand_photo", image, 640, 360)
        except tk.TclError:
            pass

    def _paint_video_widget(self, widget, photo_attr, image, min_w, min_h):
        from PIL import Image
        from PIL import ImageTk

        try:
            if not widget.winfo_exists():
                return
        except tk.TclError:
            return
        width = max(widget.winfo_width(), 1)
        height = max(widget.winfo_height(), 1)
        if width < 2 or height < 2:
            width = max(width, min_w)
            height = max(height, min_h)
        resample = getattr(Image, "Resampling", Image).BILINEAR
        fitted = fit_image_in_box(
            image,
            width,
            height,
            hex_to_rgb(palette["video_bg"]),
            resample=resample,
        )
        photo = ImageTk.PhotoImage(fitted)
        widget.config(image=photo, text="")
        setattr(self, photo_attr, photo)
        if photo_attr == "_video_expand_photo":
            self._expand_last_size = (width, height)

    def _schedule_expand_repaint(self, _event=None):
        canvas = getattr(self, "_video_expand_canvas", None)
        if canvas is None:
            return
        try:
            size = (canvas.winfo_width(), canvas.winfo_height())
        except tk.TclError:
            return
        if size == getattr(self, "_expand_last_size", None):
            return
        job = getattr(self, "_expand_repaint_job", None)
        if job is not None:
            try:
                self.after_cancel(job)
            except (tk.TclError, ValueError):
                pass
        self._expand_repaint_job = self.after(30, self._paint_video_surfaces)

    def _expand_video_fullscreen(self):
        self._expand_video("fullscreen")

    def _expand_video_maximize(self):
        self._expand_video("maximized")

    def _expand_video(self, mode):
        if mode not in ("fullscreen", "maximized"):
            return
        if not self._is_dwarf_connected():
            return
        if mode == "maximized":
            self._close_fullscreen_toplevel()
            self._show_video_fill_app_window()
            return
        self._hide_video_fill_app_window()
        self._open_video_fullscreen_window()

    def _video_status_text(self):
        status = "Video stream is off"
        try:
            status = self.video_canvas.cget("text") or status
        except tk.TclError:
            pass
        return status

    def _show_video_fill_app_window(self):
        cover = getattr(self, "_video_expand_cover", None)
        if cover is not None:
            try:
                if cover.winfo_exists():
                    self._place_video_fill_cover(cover)
                    self._video_expand_mode = "maximized"
                    overlay = getattr(self, "_video_expand_overlay", None)
                    if overlay is not None:
                        overlay.set_current("maximized")
                    self._bind_expand_escape()
                    self._expand_last_size = None
                    self._schedule_expand_repaint()
                    return
            except tk.TclError:
                pass
        self._teardown_expand_surface()
        cover = tk.Frame(self, bg=palette["video_bg"], highlightthickness=0, bd=0)
        cover._theme_role = "video"
        self._video_expand_cover = cover
        self._build_expand_stage(cover)
        self._place_video_fill_cover(cover)
        self._video_expand_mode = "maximized"
        overlay = getattr(self, "_video_expand_overlay", None)
        if overlay is not None:
            overlay.set_current("maximized")
        self._bind_expand_escape()
        self._paint_video_surfaces()

    def _place_video_fill_cover(self, cover):
        cover.place(relx=0, rely=0, relwidth=1, relheight=1)
        cover.lift()

    def _hide_video_fill_app_window(self):
        cover = getattr(self, "_video_expand_cover", None)
        if cover is None:
            return
        overlay = getattr(self, "_video_expand_overlay", None)
        if overlay is not None:
            overlay.destroy()
        try:
            cover.destroy()
        except tk.TclError:
            pass
        self._video_expand_cover = None
        self._video_expand_stage = None
        self._video_expand_canvas = None
        self._video_expand_overlay = None
        self._video_expand_photo = None
        self._expand_last_size = None
        if getattr(self, "_video_expand_mode", None) == "maximized":
            self._video_expand_mode = None

    def _open_video_fullscreen_window(self):
        existing = getattr(self, "_video_expand_win", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.attributes("-fullscreen", True)
                    self._video_expand_mode = "fullscreen"
                    overlay = getattr(self, "_video_expand_overlay", None)
                    if overlay is not None:
                        overlay.set_current("fullscreen")
                    existing.lift()
                    existing.focus_force()
                    self._bind_expand_escape()
                    self._expand_last_size = None
                    self._schedule_expand_repaint()
                    return
            except tk.TclError:
                pass
        self._teardown_expand_surface()
        win = tk.Toplevel(self)
        win.withdraw()
        win.title("Live Preview")
        win.configure(bg=palette["video_bg"])
        win._theme_role = "video"
        try:
            win.iconbitmap(self.iconbitmap())
        except Exception:
            pass
        win.protocol("WM_DELETE_WINDOW", self._restore_video_view)
        win.bind("<Escape>", lambda _event: self._restore_video_view())
        self._video_expand_win = win
        self._build_expand_stage(win)
        try:
            win.overrideredirect(False)
        except tk.TclError:
            pass
        win.attributes("-fullscreen", True)
        self._video_expand_mode = "fullscreen"
        overlay = getattr(self, "_video_expand_overlay", None)
        if overlay is not None:
            overlay.set_current("fullscreen")
        try:
            win.update_idletasks()
        except tk.TclError:
            pass
        win.deiconify()
        win.lift()
        win.focus_force()
        self._bind_expand_escape()
        self._paint_video_surfaces()

    def _build_expand_stage(self, parent):
        stage = tk.Frame(parent, bg=palette["video_bg"], highlightthickness=0, bd=0)
        stage._theme_role = "video"
        stage.pack(fill="both", expand=True)
        canvas = tk.Label(
            stage,
            text=self._video_status_text(),
            bg=palette["video_bg"],
            fg=palette["muted"],
            font=fonts["body"],
            justify="center",
            anchor="center",
        )
        canvas._theme_role = "video"
        canvas._theme_font = "body"
        canvas.pack(fill="both", expand=True)
        canvas.bind("<Configure>", self._schedule_expand_repaint)
        parent.bind("<Configure>", self._schedule_expand_repaint)
        for widget in (parent, stage, canvas):
            widget.bind("<Escape>", lambda _event: self._restore_video_view())
        self._video_expand_stage = stage
        self._video_expand_canvas = canvas
        self._video_expand_overlay = VideoHoverOverlay(
            stage,
            {
                "restore": self._restore_video_view,
                "maximize": self._expand_video_maximize,
                "fullscreen": self._expand_video_fullscreen,
            },
            visible_kinds=("restore", "maximize", "fullscreen"),
            can_show=self._is_dwarf_connected,
        )
        self._video_expand_overlay.attach_tooltips(Tooltip)

    def _bind_expand_escape(self):
        if getattr(self, "_expand_esc_id", None):
            return
        self._expand_esc_id = self.bind("<Escape>", self._restore_video_view, add="+")

    def _restore_video_view(self, _event=None):
        if not getattr(self, "_video_expand_mode", None):
            return
        self.after(1, self._close_video_expand_window)
        return "break"

    def _close_fullscreen_toplevel(self):
        overlay_on_toplevel = getattr(self, "_video_expand_win", None) is not None
        win = getattr(self, "_video_expand_win", None)
        if overlay_on_toplevel:
            overlay = getattr(self, "_video_expand_overlay", None)
            if overlay is not None:
                overlay.destroy()
            self._video_expand_overlay = None
            self._video_expand_stage = None
            self._video_expand_canvas = None
            self._video_expand_photo = None
        if win is not None:
            try:
                win.attributes("-fullscreen", False)
            except tk.TclError:
                pass
            try:
                win.destroy()
            except tk.TclError:
                pass
        self._video_expand_win = None
        if overlay_on_toplevel and getattr(self, "_video_expand_mode", None) == "fullscreen":
            self._video_expand_mode = None

    def _close_video_expand_window(self):
        self._teardown_expand_surface()

    def _teardown_expand_surface(self):
        job = getattr(self, "_expand_repaint_job", None)
        if job is not None:
            try:
                self.after_cancel(job)
            except (tk.TclError, ValueError):
                pass
            self._expand_repaint_job = None
        overlay = getattr(self, "_video_expand_overlay", None)
        if overlay is not None:
            overlay.destroy()
        cover = getattr(self, "_video_expand_cover", None)
        if cover is not None:
            try:
                cover.destroy()
            except tk.TclError:
                pass
        win = getattr(self, "_video_expand_win", None)
        if win is not None:
            try:
                win.attributes("-fullscreen", False)
            except tk.TclError:
                pass
            try:
                win.destroy()
            except tk.TclError:
                pass
        self._video_expand_win = None
        self._video_expand_cover = None
        self._video_expand_stage = None
        self._video_expand_canvas = None
        self._video_expand_overlay = None
        self._video_expand_mode = None
        self._video_expand_photo = None
        self._expand_last_size = None
        esc_id = getattr(self, "_expand_esc_id", None)
        if esc_id:
            try:
                self.unbind("<Escape>", esc_id)
            except tk.TclError:
                pass
            self._expand_esc_id = None

    def toggle_video_stream(self, event=None):
        """Toggle video stream on/off when canvas is single-clicked (with delay to avoid double-click conflict)."""
        if getattr(self, "_video_clicks_blocked", False):
            return
        if not self._is_dwarf_connected():
            return
        # Cancel any existing single-click timer
        if hasattr(self, '_single_click_timer') and self._single_click_timer:
            self.after_cancel(self._single_click_timer)
        
        # Set a timer for the single-click action (250ms delay)
        self._single_click_timer = self.after(250, self._perform_single_click)
    
    def _perform_single_click(self):
        """Perform the actual single-click action after delay."""
        if getattr(self, "_video_clicks_blocked", False):
            return
        if not self._is_dwarf_connected():
            return
        if hasattr(self, '_stop_video_stream'):
            if self._stop_video_stream:
                # Turn video stream on
                self._stop_video_stream = False
                self.start_video_preview()
                self.log("Video stream turned on")
            else:
                # Turn video stream off
                self._stop_video_stream = True
                self._stop_ffmpeg()
                self._set_video_status("Video stream is off")
                self.log("Video stream turned off")

    def _update_preview_lens_button(self):
        button = getattr(self, "preview_lens_button", None)
        if button is None:
            return
        if self._preview_is_wide():
            kind = "wide"
            tip = "Wide lens — click to switch to telephoto"
        else:
            kind = "tele"
            tip = "Telephoto — click to switch to wide lens"
        button.set_kind(kind)
        tooltip = getattr(self, "preview_lens_tooltip", None)
        if tooltip is not None:
            tooltip.text = tip
        self._sync_preview_lens_icon()

    def _sync_preview_lens_icon(self):
        button = getattr(self, "preview_lens_button", None)
        if button is None:
            return
        enabled = (
            self._is_dwarf_connected()
            and not self._page_is_busy()
            and not getattr(self, "_video_clicks_blocked", False)
        )
        button.set_enabled(enabled)

    def toggle_preview_lens(self):
        """Switch live preview between telephoto (ch0) and wide (ch1)."""
        if getattr(self, "_video_clicks_blocked", False):
            return
        if not self._is_dwarf_connected():
            return
        if self._page_is_busy():
            return
        wide = not self._preview_is_wide()
        self._preview_lens = "wide" if wide else "tele"
        self._update_preview_lens_button()
        name = "wide" if wide else "telephoto"
        self._resolve_video_stream_url()
        self.log(f"Live preview lens: {name} ({self.video_stream_url})")
        if not should_start_preview_on_lens_toggle(
            connected=self._is_dwarf_connected(),
            busy=self._page_is_busy(),
            clicks_blocked=bool(getattr(self, "_video_clicks_blocked", False)),
        ):
            return
        self._request_live_mode = False
        self._request_lens_switch = True
        self._rtsp_transport = "tcp"
        if getattr(self, "_stop_video_stream", True) or not getattr(
            self, "_video_worker_running", False
        ):
            self.start_video_preview(ensure_live=False)
            return
        self.reconnect_video_preview()
        
    def open_video_stream_in_browser(self, event=None):
        """Show the live-stream URL so it can be copied into VLC or another player."""
        if getattr(self, "_video_clicks_blocked", False):
            return
        if not self._is_dwarf_connected():
            return
        if hasattr(self, '_single_click_timer') and self._single_click_timer:
            self.after_cancel(self._single_click_timer)
            self._single_click_timer = None

        stream_url = getattr(self, "video_stream_url", None) or self._resolve_video_stream_url()
        if stream_url:
            self._show_stream_url_dialog(stream_url)
        else:
            self.log("Video stream URL not available", level="warning")

    def _show_stream_url_dialog(self, stream_url):
        existing = getattr(self, "_stream_url_dialog", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_set()
                    return
            except tk.TclError:
                pass

        is_rtsp = stream_url.startswith("rtsp://")
        dialog = tk.Toplevel(self)
        self._stream_url_dialog = dialog
        dialog.title("External stream")
        dialog.transient(self)
        dialog.resizable(False, False)
        apply_theme(dialog, load_appearance())

        body, inner = card(dialog)
        body.pack(fill="both", expand=True, padx=spacing["pad"], pady=spacing["pad"])
        inner.grid_columnconfigure(0, weight=1)

        ttk.Label(inner, text="Stream URL", style="Heading.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        hint = (
            "Windows has no default app for RTSP. Copy this URL and open it in VLC or another player."
            if is_rtsp
            else "Copy this URL, or open it in a browser."
        )
        hint_label(inner, hint).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(spacing["sm"], spacing["lg"])
        )

        url_entry = ttk.Entry(inner)
        url_entry.insert(0, stream_url)
        url_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, spacing["lg"]))
        url_entry.configure(state="readonly")

        def copy_url():
            dialog.clipboard_clear()
            dialog.clipboard_append(stream_url)
            dialog.update()
            copy_button.config(text="Copied")
            self.log(f"Copied stream URL: {stream_url}")
            def restore_copy_label():
                try:
                    if copy_button.winfo_exists():
                        copy_button.config(text="Copy")
                except tk.TclError:
                    pass
            dialog.after(1600, restore_copy_label)

        def open_in_browser():
            try:
                webbrowser.open(stream_url)
                self.log(f"Opening video stream in browser: {stream_url}")
            except Exception as e:
                self.log(f"Error opening video stream in browser: {e}", level="error")

        def close_dialog():
            if getattr(self, "_stream_url_dialog", None) is dialog:
                self._stream_url_dialog = None
            dialog.destroy()

        buttons = ttk.Frame(inner, style="Card.TFrame")
        buttons.grid(row=3, column=0, columnspan=2, sticky="e")
        copy_button = ttk.Button(buttons, text="Copy", style="Accent.TButton", command=copy_url)
        copy_button.pack(side="left", padx=(0, spacing["gap"]))
        if not is_rtsp:
            ttk.Button(buttons, text="Open in browser", command=open_in_browser).pack(
                side="left", padx=(0, spacing["gap"])
            )
        ttk.Button(buttons, text="Close", command=close_dialog).pack(side="left")

        dialog.protocol("WM_DELETE_WINDOW", close_dialog)
        dialog.update_idletasks()
        width = max(dialog.winfo_reqwidth(), 520)
        height = dialog.winfo_reqheight()
        x = self.winfo_rootx() + max((self.winfo_width() - width) // 2, 0)
        y = self.winfo_rooty() + max((self.winfo_height() - height) // 2, 0)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        theme_window_frame(dialog, load_appearance())
        dialog.bind("<Map>", lambda event, win=dialog: theme_window_frame(win, load_appearance()) if event.widget is win else None)
        dialog.bind("<Escape>", lambda _event: close_dialog())
        dialog.grab_set()
        copy_button.focus_set()
        
    def __init__(self):
        self.last_text = ""
        super().__init__()
                
        self.title(_window_title())
        self.geometry("960x840")
        self.minsize(900, 700)
        apply_theme(self, load_appearance())
        install_mousewheel(self)
        
        # Set window icon
        try:
            # Try multiple possible icon locations for different deployment scenarios
            icon_paths = [
                "Install/astro_dwarf_session_UI.ico",  # Development/source directory
                "astro_dwarf_session_UI.ico",  # Packaged application root
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "Install", "astro_dwarf_session_UI.ico"),  # Absolute path
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "astro_dwarf_session_UI.ico")  # Same directory as script
            ]
            
            icon_loaded = False
            for icon_path in icon_paths:
                try:
                    if os.path.exists(icon_path):
                        self.iconbitmap(icon_path)
                        icon_loaded = True
                        break
                except Exception:
                    continue
            
            if not icon_loaded:
                logging.warning("Could not load icon from any of the expected locations")
                
        except Exception as e:
            logging.warning(f"Could not load icon: {e}")

        # Set up window close protocol to properly clean up video stream
        self.protocol("WM_DELETE_WINDOW", self.quit_method)

        # --- Initialize all attributes used by methods before any method that uses them ---
        self.scheduler_running = False
        self.scheduler_stopped = True
        self.scheduler_stop_event = threading.Event()
        self._scheduler_stopping = False
        self._scheduler_connecting = False
        self._quitting = False
        self.session_running = False
        self.session_stop_event = threading.Event()
        self.action_stop_event = threading.Event()
        self._current_action = None
        self._stop_in_progress = False
        self._main_page_locked = False
        self._main_page_lock_states = []
        self._video_clicks_blocked = False
        self._bluetooth_choice_locked = False
        self.unset_lock_device_mode = True
        self.bluetooth_connected = False
        self.result = False
        self.stellarium_connection = None
        self.skip_time_checks = False
        self._video_worker_running = False
        self._reconnect_video_stream = False
        self._request_live_mode = False
        self._video_preview_started_at = 0
        self._ffmpeg_proc = None
        self._rtsp_transport = "tcp"
        self._single_click_timer = None
        self._video_last_image = None
        self._video_expand_photo = None
        self._video_expand_win = None
        self._video_expand_cover = None
        self._video_expand_stage = None
        self._video_expand_canvas = None
        self._video_expand_overlay = None
        self._video_expand_mode = None
        self._expand_repaint_job = None
        self._expand_last_size = None
        self._expand_esc_id = None
        self._preview_overlay = None

        self.title_bar, self._max_btn = title_bar(
            self,
            _window_title(),
            on_minimize=self.minimize_window,
            on_maximize=self.toggle_maximize,
            on_close=self.quit_method,
        )
        self.title_bar.pack(fill="x", side="top")

        self._tab_ids = [
            "main",
            "settings",
            "overview",
            "results",
            "create",
            "edit",
        ]
        self.tab_strip = tab_bar(
            self,
            [
                ("main", "Main"),
                ("settings", "Settings"),
                ("overview", "Session Overview"),
                ("results", "Results Session"),
                ("create", "Create Session"),
                ("edit", "Edit Sessions"),
            ],
            self._on_custom_tab,
            initial="main",
        )
        self.theme_toggle = appearance_toggle(self.tab_strip, self._on_appearance_toggle)
        self.theme_toggle.pack(side="right", padx=(spacing["gap"], spacing["lg"]), pady=spacing["md"])
        self.tab_strip.pack(fill="x", side="top")

        # Create tabs (native notebook tabs are hidden; the custom strip switches pages)
        self.tab_control = ttk.Notebook(self)
        self.tab_control.pack(expand=1, fill="both")

        self.tab_main = ttk.Frame(self.tab_control)
        self.tab_settings = ttk.Frame(self.tab_control)
        self.tab_overview_session = ttk.Frame(self.tab_control)
        self.tab_result_session = ttk.Frame(self.tab_control)
        self.tab_create_session = ttk.Frame(self.tab_control)
        self.tab_edit_sessions = ttk.Frame(self.tab_control)

        self.tab_control.add(self.tab_main, text="Main")
        self.tab_control.add(self.tab_settings, text="Settings")
        self.tab_control.add(self.tab_overview_session, text="Session Overview")
        self.tab_control.add(self.tab_result_session, text="Results Session")
        self.tab_control.add(self.tab_create_session, text="Create Session")
        self.tab_control.add(self.tab_edit_sessions, text="Edit Sessions")

        self.refresh_results = None
        self.create_main_tab()

        # Ensure file counts are updated on startup
        self.update_session_counts()
        self.settings_vars = {}
        self.config_vars = {}
        
        # Define callback to update create session tab when camera type changes
        def on_camera_type_change(camera_type_display):
            from tabs import create_session
            create_session.update_exposure_gain_dropdowns_from_camera_type(camera_type_display, self.settings_vars)
            # Only update defaults if camera type actually changed
            # This will be called by settings tab when camera type is changed by user
        
        # Store the callback for reuse during refresh
        self.camera_type_change_callback = on_camera_type_change
        
        settings.create_settings_tab(self.tab_settings, self.config_vars, on_camera_type_change, 
                                   update_create_session_callback=self.update_create_session_defaults)
        
        # Store refresh functions for tabs
        self.overview_refresh = None
        self.edit_sessions_refresh = None
        
        # Setup overview tab and capture refresh
        def set_overview_refresh(refresh_func):
            self.overview_refresh = refresh_func
        overview_session.overview_session_tab(self.tab_overview_session, set_overview_refresh)
        
        # Add the tab's content and capture the refresh function
        self.refresh_results = result_session.result_session_tab(self.tab_result_session)
        create_session.create_session_tab(self.tab_create_session, self.settings_vars, self.config_vars)
        
        # Setup edit sessions tab
        from tabs import edit_sessions
        def edit_sessions_tab_wrapper():
            from astro_dwarf_scheduler import LIST_ASTRO_DIR
            session_dir = LIST_ASTRO_DIR["SESSIONS_DIR"]
            result = edit_sessions.edit_sessions_tab(self.tab_edit_sessions, session_dir)
            # result is a tuple: (refresh_list, cleanup)
            if isinstance(result, tuple) and callable(result[0]):
                self.edit_sessions_refresh = result[0]

        edit_sessions_tab_wrapper()

        # Bind tab change event to refresh file lists
        def on_tab_changed(event):
            try:
                # Get current tab index more safely
                current_index = event.widget.index('current')
                
                # Handle various invalid index cases
                if current_index == '' or current_index is None:
                    return
                    
                # Convert to integer if it's a string number
                if isinstance(current_index, str):
                    if current_index.isdigit():
                        current_index = int(current_index)
                    else:
                        return  # Skip if not a valid numeric string
                
                # Get tab info safely
                tab_info = event.widget.tab(current_index)
                if tab_info and 'text' in tab_info:
                    tab = tab_info['text']
                    if tab == 'Session Overview':
                        if self.overview_refresh:
                            self.overview_refresh()
                    # Removed automatic Create Session update on tab change
                    # Only update when settings are actually changed
            except (tk.TclError, ValueError, TypeError, IndexError) as e:
                # Handle cases where tab index is invalid or widget is destroyed
                print(f"Error in on_tab_changed: {e}")
                pass

        self.tab_control.bind("<<NotebookTabChanged>>", on_tab_changed)
        apply_theme(self, load_appearance())
        self.after(50, self._apply_custom_chrome)
        self.bind("<Map>", self._on_window_map)

    def _on_custom_tab(self, tab_id):
        close_date_entry_popups(self)
        try:
            index = self._tab_ids.index(tab_id)
            self.tab_control.select(index)
        except (ValueError, tk.TclError):
            pass

    def _on_appearance_toggle(self, appearance):
        apply_ui_appearance(self, appearance)
        overlay = getattr(self, "_preview_overlay", None)
        if overlay is not None:
            overlay.refresh()
        expand_overlay = getattr(self, "_video_expand_overlay", None)
        if expand_overlay is not None:
            expand_overlay.refresh()
        cover = getattr(self, "_video_expand_cover", None)
        if cover is not None:
            try:
                if cover.winfo_exists():
                    cover.configure(bg=palette["video_bg"])
            except tk.TclError:
                pass
        win = getattr(self, "_video_expand_win", None)
        if win is not None:
            try:
                if win.winfo_exists():
                    win.configure(bg=palette["video_bg"])
            except tk.TclError:
                pass
        self._paint_video_surfaces()

    def minimize_window(self):
        self.iconify()

    def toggle_maximize(self):
        if self.state() == "zoomed":
            self.state("normal")
            if hasattr(self, "_max_btn"):
                self._max_btn.config(text="□")
        else:
            self.state("zoomed")
            if hasattr(self, "_max_btn"):
                self._max_btn.config(text="❐")
        self.after(20, self._apply_custom_chrome)

    def _apply_custom_chrome(self):
        hide_native_titlebar(self)

    def _on_window_map(self, event):
        if event.widget is self:
            self.after(20, self._apply_custom_chrome)

    def update_create_session_defaults(self):
        """Update Create Session tab defaults from current config - only call when settings change"""
        if hasattr(self, 'settings_vars'):
            from tabs import create_session
            create_session.update_exposure_gain_fields(self.settings_vars)

    def reset_total_runtime(self):
        self.total_session_runtime = 0
        self.session_runtime = 0
        self.session_start_time = 0

    def add_to_total_runtime(self, session_seconds):
        if not hasattr(self, 'total_session_runtime'):
            self.total_session_runtime = 0
        self.total_session_runtime += session_seconds

    # Function to get the exposure time from settings_vars
    def get_exposure_time(self, settings_vars):
        exposure_string = str(settings_vars["id_command"]["exposure"])  # Get the exposure string from settings_vars
        try:
            if not exposure_string:
                print("exposure not defined")
                return 0
            # Check for fractional input
            if '/' in exposure_string:
                exposure_seconds = float(Fraction(exposure_string))  # Convert fraction to float
            else:
                exposure_seconds = float(exposure_string)  # Convert to float to handle fractions

            return exposure_seconds  # Return the float value directly
        except (ValueError, ZeroDivisionError):
            print(f"Invalid exposure time: {exposure_string}. Defaulting to 0.")
            return 0.0  # Return a default value if conversion fails

    def calculate_end_time(self, settings_vars):
        try:
            # Get exposure and gain from settings_vars  
            settings_vars["id_command"]["exposure"] = 1
            settings_vars["id_command"]["gain"] = 1
            settings_vars["id_command"]["count"] = 1

            camera_sections = ['setup_camera', 'setup_wide_camera']
            for section in camera_sections:
                settings = settings_vars.get(section, {})
                if settings.get('do_action'):
                    settings_vars["id_command"]["exposure"] = settings['exposure']
                    settings_vars["id_command"]["gain"] = settings['gain']
                    settings_vars["id_command"]["count"] = settings['count']
                    break

            # Get the starting date, time, exposure, and count
            exposure_seconds = self.get_exposure_time(settings_vars)

            count = int(settings_vars["id_command"]["count"])

            # Initialise wait time - manual adjustment
            wait_time = 0

            if settings_vars.get("eq_solving", False):
                # wait time actions
                wait_time += 60
                wait_time += int(settings_vars.get("wait_before", 0))
                wait_time += int(settings_vars.get("wait_after", 0))
            if settings_vars.get("auto_focus", False):
                # wait time actions
                wait_time += 10
                wait_time += int(settings_vars.get("wait_before", 0))
                wait_time += int(settings_vars.get("wait_after", 0))
            if settings_vars.get("infinite_focus", False):
                # wait time actions
                wait_time += 5
                wait_time += int(settings_vars.get("wait_before", 0))
                wait_time += int(settings_vars.get("wait_after", 0))
            if settings_vars.get("calibration", False):
                dwarf_id = 2  # Ensure dwarf_id is always defined
                data_config = config_py.get_config_data()
                if data_config.get("dwarf_id"):
                    dwarf_id = data_config['dwarf_id']

                dwarf_id_int = config_to_dwarf_id_int(dwarf_id)

                # wait between actions and time actions
                wait_time += 10 + 60
                wait_time += 90 if dwarf_id_int >= 3 else 0
                wait_time += int(settings_vars.get("wait_before", 0))
                wait_time += int(settings_vars.get("wait_after", 0))
                wait_time += int(settings_vars.get("wait_after", 0))
            if settings_vars.get("goto_solar", False) or settings_vars.get("goto_manual", False):
                wait_time += 30
                wait_time += int(settings_vars.get("wait_after_target", 0))

            # wait time setup camera
            wait_time += int(settings_vars.get("wait_after_camera", 0))

            if not isinstance(self.session_start_time, datetime):
                self.session_start_time = datetime.now()

            # Combine date and time into a single datetime object
            start_datetime = self.session_start_time

            # Calculate the total exposure time
            total_exposure_time = wait_time + (exposure_seconds + 1) * count 

            # Calculate end time
            end_datetime = start_datetime + timedelta(seconds=total_exposure_time)

            # Calculate duration in H:M:S
            duration = end_datetime - start_datetime
            duration_str = str(duration).split(", ")[-1]  # Get the last part (H:M:S)

            return duration_str
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
            return 0


    def quit_method(self):
        '''
        User wants to quit
        '''
        if getattr(self, "_quitting", False):
            return
        self._quitting = True
        print("Waiting during closing...")
        self.log("Waiting during closing...")

        self._close_video_expand_window()

        self._stop_video_stream = True
        self._reconnect_video_stream = False
        self._stop_ffmpeg()

        self.scheduler_running = False
        self.scheduler_stop_event.set()
        try:
            request_command_interrupt()
        except Exception:
            pass

        threading.Thread(target=self._disconnect_in_background, daemon=True).start()
        self.after(250, self._destroy_window)

    def _disconnect_in_background(self):
        try:
            perform_disconnect()
        except Exception:
            pass

    def _destroy_window(self):
        try:
            self.destroy()
        except Exception:
            pass

    def finalize_close(self):
        '''
        Perform the final close with force termination if needed
        '''
        threading.Thread(target=self._disconnect_in_background, daemon=True).start()
        self.after(250, self._destroy_window)

    def countdown(self, wait):
        '''
        Countdown that checks scheduler status and waits for stop or timeout
        '''
        if self.scheduler_stopped or not self.scheduler_running:
            self.log("Scheduler stopped, closing now.")
            self.after(500, self.destroy)
        elif wait > 0:
            # Schedule the countdown to run again after 1 second
            self.after(1000, self.countdown, wait - 1)
        else:
            self.log("Timeout reached, forcing closure...")
            # Cannot forcibly terminate threads safely in Python; log and proceed to close
            if hasattr(self, 'scheduler_thread') and self.scheduler_thread.is_alive():
                self.log("Scheduler thread is still running and cannot be forcibly stopped safely.", level="warning")
            self.after(500, self.destroy)

    def toggle_multiple(self):
        """Show or hide the Listbox and related widgets based on checkbox state."""
        if self.multiple_var.get():
            devices = load_configuration()  # Call the function to load devices
            self.config_combobox["values"] = devices
            self.config_combobox.set(CONFIG_DEFAULT)  # Always set CONFIG_DEFAULT as selected initially
            # Use variables for row indices to make layout flexible
            row_config = 0
            row_entry = 1
    
            self.combobox_label.grid(row=row_config, column=1, sticky="e", padx=(0, spacing["label_gap"]), pady=spacing["row"])
            self.config_combobox.grid(row=row_config, column=2, sticky="ew", padx=(0, spacing["gap"]), pady=spacing["row"])
            self.entry_label.grid(row=row_entry, column=1, sticky="e", padx=(0, spacing["label_gap"]), pady=spacing["row"])
            self.entry_button_frame.grid(row=row_entry, column=2, sticky="w", pady=spacing["row"])
            self.show_current_config(CONFIG_DEFAULT)
        else:
            self.config_combobox.set("")
            self.combobox_label.grid_remove()
            self.config_combobox.grid_remove()
            self.entry_label.grid_remove()
            self.entry_button_frame.grid_remove()
            setup_new_config(CONFIG_DEFAULT)
            self.show_current_config(CONFIG_DEFAULT)
            
            # Refresh the settings tab to reload default settings from config.ini
            # Only if the settings tab has been initialized
            if hasattr(self, 'config_vars') and hasattr(self, 'camera_type_change_callback'):
                from tabs import settings
                settings.refresh_settings_tab(self.tab_settings, self.config_vars, self.camera_type_change_callback, 
                                             update_create_session_callback=self.update_create_session_defaults)

    def on_combobox_change(self, event):
        global LIST_ASTRO_DIR
        selected_value = self.config_combobox.get()
        print(f"Selected Configuration: {selected_value}")
        setup_new_config(selected_value)
        self.show_current_config(selected_value)
        
        # Refresh the settings tab with the new config's settings
        from tabs import settings
        settings.refresh_settings_tab(self.tab_settings, self.config_vars, self.camera_type_change_callback,
                                     update_create_session_callback=self.update_create_session_defaults)

    def add_config(self):
        """Add a new configuration to the Listbox."""
        config_name = self.config_entry.get().strip().capitalize()
        if config_name:
            if check_new_configuration(config_name):
                self.config_combobox.set(config_name)
                self.config_entry.delete(0, tk.END)
                self.show_current_config(config_name)
            else:
                # Add to Combobox values
                current_values = list(self.config_combobox["values"])
                current_values.append(config_name)
                self.config_combobox["values"] = current_values
                self.config_combobox.set(config_name)  # Set the newly added config as the current selection
                self.config_entry.delete(0, tk.END)
                setup_new_config(config_name)
                add_new_configuration(config_name)
                self.show_current_config(config_name, True)
        else:
            messagebox.showwarning("Input Error", "Configuration name cannot be empty.")


    def refresh_data(self):
        # Call the refresh function directly
        if self.refresh_results:
            self.refresh_results()
        # Always update file counts after refresh
        if hasattr(self, 'update_session_counts'):
            self.update_session_counts()

    def show_current_config(self, config_name, created = False):
        from astro_dwarf_scheduler import LIST_ASTRO_DIR

        if (self.log_text):
            if config_name == CONFIG_DEFAULT:
                self.log("Default configuration selected.")
            elif created:
                self.log(f"New configuration '{config_name}' created.")
            else:
                self.log(f"Configuration '{config_name}' selected.")
            self.log(f"Session directory: '{LIST_ASTRO_DIR['SESSIONS_DIR']}'.")

        self.refresh_data()
        # Always update file counts after config change
        if hasattr(self, 'update_session_counts'):
            self.update_session_counts()

    def disable_controls(self):
        """Disable the checkbox and Add button."""
        self.multiple_checkbox.config(state=tk.DISABLED)
        self.config_combobox.config(state=tk.DISABLED)
        self.add_button.config(state=tk.DISABLED)
        refresh_disabled_pointer(self)

    def enable_controls(self):
        """Enable the checkbox and Add button."""
        self.multiple_checkbox.config(state=tk.NORMAL)
        self.config_combobox.config(state=tk.NORMAL)
        self.add_button.config(state=tk.NORMAL)
        if not getattr(self, "scheduler_running", False) and not getattr(self, "_scheduler_stopping", False):
            self._set_bluetooth_choice_locked(False)
        refresh_disabled_pointer(self)

    def _set_scheduler_button(self, text, state, style="CompactAccent.TButton"):
        button = getattr(self, "scheduler_button", None)
        if button is None:
            return
        try:
            button.config(state=state, text=text, style=style)
        except tk.TclError:
            return
        refresh_disabled_pointer(self)

    def toggle_buttons(self, state):
        connecting = getattr(self, "_scheduler_connecting", False)
        stopping = getattr(self, "_scheduler_stopping", False)
        if stopping:
            scheduler_state = tk.DISABLED
            scheduler_text = "Stopping..."
            scheduler_style = "CompactWait.TButton"
            other_state = tk.DISABLED
        elif connecting:
            scheduler_state = tk.NORMAL
            scheduler_text = "Connecting"
            scheduler_style = "CompactWait.TButton"
            other_state = tk.DISABLED
        elif state == "waiting":
            scheduler_state = tk.NORMAL  # Allow stopping while waiting
            scheduler_text = "Stop Scheduler"
            scheduler_style = "CompactAccent.TButton"
            other_state = tk.DISABLED
        elif state == tk.NORMAL:
            if self.scheduler_running:
                scheduler_state = tk.NORMAL
                scheduler_text = "Stop Scheduler"
            else:
                scheduler_state = tk.NORMAL
                scheduler_text = "Start Scheduler"
            scheduler_style = "CompactAccent.TButton"
            other_state = state
        elif state == tk.DISABLED:
            if self.scheduler_running:
                scheduler_state = tk.NORMAL
                scheduler_text = "Stop Scheduler"
            else:
                scheduler_state = tk.DISABLED
                scheduler_text = "Start Scheduler"
            scheduler_style = "CompactAccent.TButton"
            other_state = state
        else:  # tk.NONE or other states
            scheduler_state = tk.DISABLED
            scheduler_text = "Start Scheduler"
            scheduler_style = "CompactAccent.TButton"
            other_state = tk.DISABLED

        """Enable or disable buttons based on the state."""
        self._set_scheduler_button(scheduler_text, scheduler_state, scheduler_style)
        self.unlock_button.config(state=other_state)
        self.eq_button.config(state=other_state)
        self.polar_button.config(state=other_state)
        self.calibrate_button.config(state=other_state)
        self.autofocus_button.config(state=other_state)	
        self.powerdown_button.config(state=other_state)
        self.reboot_button.config(state=other_state)
        self.toggle_lights_button.config(state=other_state)
        self._refresh_lights_button()
        self._sync_stop_session_button()
        self.after(0, self._sync_video_tools)
        refresh_disabled_pointer(self)

    def _sync_video_tools(self):
        """Show stream overlay tools only while the telescope is connected."""
        allowed = self._is_dwarf_connected()
        overlays = (
            getattr(self, "_preview_overlay", None),
            getattr(self, "_video_expand_overlay", None),
        )
        for overlay in overlays:
            if overlay is None:
                continue
            overlay.enabled = allowed
            if not allowed:
                overlay.hide()
                overlay._cancel_idle()
        canvas = getattr(self, "video_canvas", None)
        if canvas is not None:
            try:
                canvas.config(cursor="hand2" if allowed else "arrow")
            except tk.TclError:
                pass
        self._sync_bluetooth_browser_lock()
        self._sync_preview_lens_icon()

    def _bluetooth_browser_should_lock(self):
        return bool(self._is_dwarf_connected())

    def _sync_bluetooth_browser_lock(self):
        """Keep the web-Bluetooth option fixed while the telescope is connected."""
        checkbox = getattr(self, "checkbox_commandBluetooth", None)
        if checkbox is None:
            return
        locked = self._bluetooth_browser_should_lock()
        try:
            checkbox.config(state=tk.DISABLED if locked else tk.NORMAL)
        except tk.TclError:
            pass
        set_pointer_blocked(checkbox, locked)
        refresh_disabled_pointer(self)

    def _on_use_web_toggle(self):
        if self._bluetooth_browser_should_lock():
            try:
                self.use_web.set(getattr(self, "_use_web_locked_value", self.use_web.get()))
            except tk.TclError:
                pass
            return
        self._use_web_locked_value = bool(self.use_web.get())

    def _page_is_busy(self):
        """True while a session, main-page task, device-stop, or scheduler shutdown is running."""
        return bool(
            getattr(self, "session_running", False)
            or self._action_is_running()
            or getattr(self, "_scheduler_stopping", False)
        )

    def _main_page_lock_widgets(self):
        return [
            widget for widget in (
                getattr(self, "unlock_button", None),
                getattr(self, "calibrate_button", None),
                getattr(self, "autofocus_button", None),
                getattr(self, "polar_button", None),
                getattr(self, "eq_button", None),
                getattr(self, "powerdown_button", None),
                getattr(self, "reboot_button", None),
                getattr(self, "toggle_lights_button", None),
                getattr(self, "add_button", None),
                getattr(self, "multiple_checkbox", None),
                getattr(self, "config_combobox", None),
                getattr(self, "config_entry", None),
                getattr(self, "checkbox_commandBluetooth", None),
                getattr(self, "clear_log_button", None),
                getattr(self, "skip_time_checks_checkbox", None),
            ) if widget is not None
        ]

    def _apply_main_page_busy_lock(self):
        """While a task runs, only Stop Scheduler and Stop Session stay clickable."""
        busy = self._page_is_busy()
        scheduler = getattr(self, "scheduler_button", None)
        if busy:
            if not getattr(self, "_main_page_locked", False):
                self._main_page_lock_states = []
                for widget in self._main_page_lock_widgets():
                    try:
                        self._main_page_lock_states.append((widget, {"state": str(widget.cget("state"))}))
                    except tk.TclError:
                        pass
                self._main_page_locked = True
            for widget in self._main_page_lock_widgets():
                try:
                    widget.config(state=tk.DISABLED)
                except tk.TclError:
                    pass
            if scheduler is not None:
                try:
                    if getattr(self, "_scheduler_stopping", False):
                        self._set_scheduler_button("Stopping...", tk.DISABLED, "CompactWait.TButton")
                    elif getattr(self, "_scheduler_connecting", False):
                        self._set_scheduler_button("Connecting", tk.NORMAL, "CompactWait.TButton")
                    elif getattr(self, "scheduler_running", False):
                        self._set_scheduler_button("Stop Scheduler", tk.NORMAL)
                    else:
                        self._set_scheduler_button("Start Scheduler", tk.DISABLED)
                except tk.TclError:
                    pass
            self._video_clicks_blocked = True
            self._sync_preview_lens_icon()
            refresh_disabled_pointer(self)
            return
        if getattr(self, "_main_page_locked", False):
            for widget, config in self._main_page_lock_states:
                try:
                    widget.config(**config)
                except tk.TclError:
                    pass
            self._main_page_lock_states = []
            self._main_page_locked = False
            self._video_clicks_blocked = False
            if not getattr(self, "scheduler_running", False) and scheduler is not None:
                try:
                    self._set_scheduler_button("Start Scheduler", tk.NORMAL)
                except tk.TclError:
                    pass
                for widget in self._main_page_lock_widgets():
                    try:
                        if widget in (
                            getattr(self, "unlock_button", None),
                            getattr(self, "calibrate_button", None),
                            getattr(self, "autofocus_button", None),
                            getattr(self, "polar_button", None),
                            getattr(self, "eq_button", None),
                            getattr(self, "powerdown_button", None),
                            getattr(self, "reboot_button", None),
                            getattr(self, "toggle_lights_button", None),
                        ):
                            widget.config(state=tk.DISABLED)
                    except tk.TclError:
                        pass
        self._sync_bluetooth_browser_lock()
        self._sync_preview_lens_icon()
        refresh_disabled_pointer(self)

    def _action_thread_alive(self):
        for name in ("eq_thread", "polar_thread", "cal_thread", "autofocus_thread"):
            thread = getattr(self, name, None)
            if thread is not None and thread.is_alive():
                return True
        return False

    def _stop_thread_alive(self):
        thread = getattr(self, "stop_astro_photo", None)
        return thread is not None and thread.is_alive()

    def _action_is_running(self):
        return bool(getattr(self, "_current_action", None)) or self._action_thread_alive() or self._stop_thread_alive() or getattr(self, "_stop_in_progress", False)

    def _can_start_action(self, label):
        ok, reason = can_start_action(
            session_running=bool(getattr(self, "session_running", False)),
            current_action=getattr(self, "_current_action", None),
            stop_in_progress=bool(getattr(self, "_stop_in_progress", False) or self._stop_thread_alive()),
            action_thread_alive=self._action_thread_alive(),
        )
        if not ok:
            self.log(f"Cannot start {label}: {reason}.", level="warning")
            return False
        return True

    def _begin_action(self, name):
        self._current_action = name
        self.action_stop_event.clear()
        if not getattr(self, "session_running", False):
            self.session_stop_event.clear()
        if not getattr(self, "_stop_in_progress", False):
            try:
                clear_command_interrupt()
            except Exception:
                pass
        self.after(0, self._sync_stop_session_button)

    def _end_action(self, name=None):
        if keep_action_until_stop_finishes(
            getattr(self, "_stop_in_progress", False),
            name,
            getattr(self, "_current_action", None),
        ):
            return
        if name is None or getattr(self, "_current_action", None) == name:
            self._current_action = None
        self.after(0, self._sync_stop_session_button)

    def _action_should_stop(self):
        if getattr(self, "action_stop_event", None) is not None and self.action_stop_event.is_set():
            return True
        if (
            getattr(self, "session_running", False)
            and getattr(self, "session_stop_event", None) is not None
            and self.session_stop_event.is_set()
        ):
            return True
        return False

    def _wait_interruptible(self, seconds, message=None):
        if message:
            self.log(message)
        deadline = time.time() + float(seconds or 0)
        while time.time() < deadline:
            if self._action_should_stop():
                return False
            time.sleep(0.1)
        return True

    def _sync_stop_session_button(self):
        """Stop Session is usable during an imaging session or a main-page task."""
        stopping = bool(
            getattr(self, "_stop_in_progress", False) or self._stop_thread_alive()
        )
        running = (
            (
                getattr(self, "scheduler_running", False)
                and getattr(self, "session_running", False)
            )
            or self._action_is_running()
        )
        try:
            if hasattr(self, "stop_session_button"):
                if stopping:
                    self.stop_session_button.config(
                        text="Stopping, please wait",
                        state=tk.DISABLED,
                        style="Wait.TButton",
                    )
                else:
                    self.stop_session_button.config(
                        text="Stop Session",
                        state=tk.NORMAL if running else tk.DISABLED,
                        style="Danger.TButton",
                    )
            self._apply_main_page_busy_lock()
        except tk.TclError:
            pass

    def create_main_tab(self):
        self.log_text = None
        from astro_dwarf_scheduler import LIST_ASTRO_DIR
        from ui.theme import status_color

        gap = spacing["gutter"]
        pad = spacing["pad"]
        self.tab_main.grid_rowconfigure(1, weight=1)
        self.tab_main.grid_columnconfigure(0, weight=1)

        top = ttk.Frame(self.tab_main)
        top.grid(row=0, column=0, sticky="ew", padx=pad, pady=(pad, gap))
        top.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(1, weight=0)

        left = ttk.Frame(top)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, gap))
        left.grid_columnconfigure(0, weight=1)

        setup_card, setup_inner = card(left)
        setup_card.grid(row=0, column=0, sticky="ew")
        self.labelConfig = section_header(setup_inner, "Configuration")
        self.labelConfig.pack(anchor="w", pady=(0, spacing["section"]))
        Tooltip(self.labelConfig, "Tick the multiple checkbox if you have more than one Dwarf devices.")

        multiple_frame = ttk.Frame(setup_inner, style="Card.TFrame")
        multiple_frame.pack(anchor="w", fill="x")
        multiple_frame.grid_columnconfigure(2, weight=1)
        multiple_frame._theme_role = "card"

        self.multiple_var = tk.BooleanVar(value=False)
        self.multiple_checkbox = ttk.Checkbutton(
            multiple_frame, text="Multiple", variable=self.multiple_var, command=self.toggle_multiple
        )
        self.multiple_checkbox.grid(row=0, column=0, sticky="w", padx=(0, spacing["gap"]), pady=spacing["row"])

        self.combobox_label = ttk.Label(multiple_frame, text="Current Config:", style="Card.TLabel")
        self.combobox_label.grid(row=0, column=1, sticky="e", padx=(0, spacing["label_gap"]), pady=spacing["row"])
        self.config_combobox = ttk.Combobox(multiple_frame, state="readonly", width=27)
        self.config_combobox["values"] = (CONFIG_DEFAULT)
        self.config_combobox.set(CONFIG_DEFAULT)
        self.config_combobox.grid(row=0, column=2, sticky="ew", padx=(0, spacing["gap"]), pady=spacing["row"])

        self.entry_label = ttk.Label(multiple_frame, text="New Config:", style="Card.TLabel")
        self.entry_label.grid(row=1, column=1, sticky="e", padx=(0, spacing["label_gap"]), pady=spacing["row"])

        self.entry_button_frame = ttk.Frame(multiple_frame, style="Card.TFrame")
        self.entry_button_frame.grid(row=1, column=2, sticky="w", pady=spacing["row"])
        self.entry_button_frame._theme_role = "card"

        self.config_entry = ttk.Entry(self.entry_button_frame, width=20)
        self.config_entry.pack(side="left", padx=(0, spacing["gap"]))
        self.add_button = ttk.Button(self.entry_button_frame, text="Add", command=self.add_config)
        self.add_button.pack(side="left")

        self.toggle_multiple()
        self.config_combobox.bind("<<ComboboxSelected>>", self.on_combobox_change)

        self.label1 = section_header(setup_inner, "Dwarf connection")
        self.label1.pack(anchor="w", pady=(spacing["xl"], spacing["section"]))

        self.use_web = tk.BooleanVar(value=False)
        self._use_web_locked_value = False
        self.checkbox_commandBluetooth = ttk.Checkbutton(
            setup_inner,
            text="Use Web Browser for Bluetooth",
            variable=self.use_web,
            command=self._on_use_web_toggle,
        )
        self.checkbox_commandBluetooth.pack(anchor="w", pady=(0, spacing["section"]))
        Tooltip(
            self.checkbox_commandBluetooth,
            "Use the direct Bluetooth function if unchecked.\nUse the web browser for Bluetooth if checked.",
        )

        self.label2 = hint_label(setup_inner, "Do you want to start the Bluetooth connection?")
        self.label2.pack(anchor="w", pady=(0, spacing["section"]))
        Tooltip(self.label2, "Select Yes to launch the command for Bluetooth connection or No to skip the connection.")

        bluetooth_frame = ttk.Frame(setup_inner, style="Card.TFrame")
        bluetooth_frame.pack(anchor="w")
        self.button_yes = ttk.Button(bluetooth_frame, text="Yes", command=self.start_bluetooth, style="Accent.TButton", width=10)
        self.button_yes.grid(row=0, column=0, padx=(0, spacing["gap"]))
        self.button_no = ttk.Button(bluetooth_frame, text="No", command=self.skip_bluetooth, width=10)
        self.button_no.grid(row=0, column=1)
        for bluetooth_button in (self.button_yes, self.button_no):
            bluetooth_button.bind("<Button-1>", self._ignore_bluetooth_choice_when_locked, add="+")
            bluetooth_button.bind("<ButtonRelease-1>", self._ignore_bluetooth_choice_when_locked, add="+")
            bluetooth_button.bind("<space>", self._ignore_bluetooth_choice_when_locked, add="+")
            bluetooth_button.bind("<Return>", self._ignore_bluetooth_choice_when_locked, add="+")

        preview_w = 320
        preview_h = int(preview_w / VIDEO_ASPECT)

        video_card, video_inner = card(top)
        video_card.grid(row=0, column=1, sticky="nsew")

        self.stop_session_button = ttk.Button(
            video_inner, text="Stop Session", style="Danger.TButton",
            state=tk.DISABLED, command=self.run_stop_astro_photo
        )
        self.stop_session_button.pack(fill="x", side="bottom")
        self.toggle_lights_button = ttk.Button(
            video_inner, text="Toggle Lights", state=tk.DISABLED, command=self.toggle_lights
        )
        self.toggle_lights_button.pack(fill="x", side="bottom", pady=(0, spacing["gap"]))
        Tooltip(self.stop_session_button, "Stop the current session or main-page task")
        self.toggle_lights_tooltip = Tooltip(self.toggle_lights_button, "Toggle lights on/off")

        section_header(video_inner, "Live Preview").pack(anchor="w", pady=(0, spacing["section"]))

        self._preview_stage = tk.Frame(
            video_inner, bg=palette["video_bg"], highlightthickness=0, bd=0,
            width=preview_w, height=preview_h,
        )
        self._preview_stage.pack(anchor="w")
        self._preview_stage.pack_propagate(False)
        self._preview_stage._theme_role = "video"

        self.video_canvas = tk.Label(
            self._preview_stage,
            text="Video stream is off",
            bg=palette["video_bg"],
            fg=palette["muted"],
            font=fonts["body"],
            justify="center",
            anchor="center",
        )
        self.video_canvas._theme_role = "video"
        self.video_canvas._theme_font = "body"
        self.video_canvas.pack(fill="both", expand=True)
        self.video_canvas.bind("<Button-1>", self.toggle_video_stream)
        self.video_canvas.bind("<Double-Button-1>", self.open_video_stream_in_browser)
        self.video_canvas.config(cursor="arrow")
        Tooltip(
            self.video_canvas,
            "Connect the telescope to start the stream.\n"
            "Then: single click toggles the stream, double click shows the URL,\n"
            "hover for full screen or fill window.",
        )
        self._preview_lens = "tele"
        self._preview_overlay = VideoHoverOverlay(
            self._preview_stage,
            {
                "maximize": self._expand_video_maximize,
                "fullscreen": self._expand_video_fullscreen,
                "lens": self.toggle_preview_lens,
            },
            visible_kinds=("maximize", "fullscreen", "lens"),
            can_show=self._is_dwarf_connected,
        )
        self._preview_overlay.attach_tooltips(Tooltip)
        self.preview_lens_button = self._preview_overlay.buttons.get("lens")
        self.preview_lens_tooltip = None
        for handle in getattr(self._preview_overlay, "_tooltip_handles", []):
            if getattr(handle, "widget", None) is self.preview_lens_button:
                self.preview_lens_tooltip = handle
                break
        self._update_preview_lens_button()
        self._stop_video_stream = True

        hint_label(video_inner, "Connect the telescope to use the live preview").pack(
            anchor="w", pady=(spacing["gap"], 0)
        )
        ttk.Frame(video_inner, style="Card.TFrame").pack(fill="both", expand=True)

        sched_card, sched_inner = card(left)
        sched_card.grid(row=1, column=0, sticky="ew", pady=(gap, 0))
        scheduler_header_frame = ttk.Frame(sched_inner, style="Card.TFrame")
        scheduler_header_frame.pack(anchor="w", fill="x", pady=(0, spacing["section"]))
        scheduler_header_frame._theme_role = "card"

        self.label3 = section_header(scheduler_header_frame, "Scheduler")
        self.label3.pack(side="left", anchor="w")

        self.session_info_label = ScrollingLabel(
            scheduler_header_frame, text="", font=fonts["body"], fg=palette["accent"], bg=palette["card"]
        )
        self.session_info_label._theme_keep_fg = True
        self.session_info_label._theme_role = "card"
        self.session_info_label.pack(side="left", fill="x", expand=True, padx=(spacing["xl"], 0))

        scheduler_frame = ttk.Frame(sched_inner, style="Card.TFrame")
        scheduler_frame.pack(anchor="w", fill="x")
        for col in range(4):
            scheduler_frame.grid_columnconfigure(col, weight=1, uniform="sched")

        self.scheduler_button = ttk.Button(
            scheduler_frame, text="Start Scheduler", command=self.toggle_scheduler,
            state=tk.DISABLED, style="CompactAccent.TButton",
        )
        self.unlock_button = ttk.Button(
            scheduler_frame, text="Unset as Host", command=self.unset_lock_device,
            state=tk.DISABLED, style="Compact.TButton",
        )
        self.calibrate_button = ttk.Button(
            scheduler_frame, text="Calibrate", command=self.start_calibration,
            state=tk.DISABLED, style="Compact.TButton",
        )
        self.autofocus_button = ttk.Button(
            scheduler_frame, text="Auto Focus", command=self.start_auto_focus_button,
            state=tk.DISABLED, style="Compact.TButton",
        )
        self.polar_button = ttk.Button(
            scheduler_frame, text="Polar Position", command=self.start_polar_position,
            state=tk.DISABLED, style="Compact.TButton",
        )
        self.eq_button = ttk.Button(
            scheduler_frame, text="EQ Solving", command=self.start_eq_solving,
            state=tk.DISABLED, style="Compact.TButton",
        )
        self.powerdown_button = ttk.Button(
            scheduler_frame, text="Power Down", command=self.start_powerdown,
            state=tk.DISABLED, style="Compact.TButton",
        )
        self.reboot_button = ttk.Button(
            scheduler_frame, text="Reboot", command=self.start_reboot,
            state=tk.DISABLED, style="Compact.TButton",
        )
        for index, button in enumerate((
            self.scheduler_button, self.unlock_button, self.calibrate_button, self.autofocus_button,
            self.polar_button, self.eq_button, self.powerdown_button, self.reboot_button,
        )):
            button.grid(row=index // 4, column=index % 4, padx=spacing["xs"], pady=spacing["xs"], sticky="ew")

        self.status_powerlight = None
        self.status_rgblight = None

        log_card, log_inner = card(self.tab_main)
        log_card.grid(row=1, column=0, sticky="nsew", padx=pad, pady=(0, gap))
        log_inner.grid_rowconfigure(1, weight=1)
        log_inner.grid_columnconfigure(0, weight=1)
        section_header(log_inner, "Log").grid(row=0, column=0, sticky="w", pady=(0, spacing["section"]))

        log_frame = ttk.Frame(log_inner, style="Card.TFrame")
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=15, font=fonts["log"], relief="flat")
        self.log_text._theme_role = "log"
        self.log_text._theme_font = "log"
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        style_log_text(self.log_text)

        status_card, status_inner = card(self.tab_main, padding=spacing["md"])
        status_card.grid(row=2, column=0, sticky="ew", padx=pad, pady=(0, pad))

        folder_names = ["ToDo", "Current", "Done", "Error", "Results"]
        sessions_dir = LIST_ASTRO_DIR["SESSIONS_DIR"]

        summary_frame = ttk.Frame(status_inner, style="Card.TFrame")
        summary_frame.pack(side="left", anchor="w")
        ttk.Label(summary_frame, text="Astro Sessions", style="Subheading.TLabel").pack(side="left", padx=(0, spacing["gap"]))
        self.session_count_labels = {}
        for folder in folder_names:
            folder_path = os.path.join(sessions_dir, folder)
            try:
                count = len([
                    f for f in os.listdir(folder_path)
                    if os.path.isfile(os.path.join(folder_path, f)) and not f.startswith(".")
                ])
            except Exception:
                count = 0
            lbl = status_label(summary_frame, folder, count)
            lbl.pack(side="left")
            self.session_count_labels[folder] = lbl

        self.clear_log_button = ttk.Button(status_inner, text="Clear Log", command=self.clear_log_output)
        self.clear_log_button.pack(side="right")

        self.skip_time_checks_var = tk.BooleanVar(value=self.skip_time_checks)

        def on_skip_time_checks_changed():
            self.skip_time_checks = self.skip_time_checks_var.get()

        self.skip_time_checks_checkbox = ttk.Checkbutton(
            status_inner,
            text="Skip Time Checks",
            variable=self.skip_time_checks_var,
            command=on_skip_time_checks_changed,
        )
        self.skip_time_checks_checkbox.pack(side="right", padx=spacing["lg"])

        def update_session_counts():
            for folder in folder_names:
                folder_path = os.path.join(sessions_dir, folder)
                try:
                    count = len([
                        f for f in os.listdir(folder_path)
                        if os.path.isfile(os.path.join(folder_path, f)) and not f.startswith(".")
                    ])
                except Exception:
                    count = 0
                self.session_count_labels[folder].config(text=f" {folder}: {count}", fg=status_color(folder))

        self.update_session_counts = update_session_counts

        def periodic_update_counts():
            self.update_session_counts()
            self.after(10000, periodic_update_counts)

        periodic_update_counts()
        self.update_session_info()

    def clear_log_output(self):
        if self.log_text is not None:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.config(state=tk.NORMAL)
        # Update file counts in case log clearing is related to session changes
        if hasattr(self, 'update_session_counts'):
            self.update_session_counts()

    def _show_bluetooth_choice(self, chosen):
        """Give the picked Yes/No button the accent fill and quiet the other one."""
        for button, name in ((getattr(self, "button_yes", None), "yes"),
                             (getattr(self, "button_no", None), "no")):
            if button is None:
                continue
            try:
                button.configure(style="Accent.TButton" if name == chosen else "TButton")
            except tk.TclError:
                pass

    def _bluetooth_choice_buttons(self):
        return [
            widget for widget in (
                getattr(self, "button_yes", None),
                getattr(self, "button_no", None),
            ) if widget is not None
        ]

    def _ignore_bluetooth_choice_when_locked(self, _event=None):
        if getattr(self, "_bluetooth_choice_locked", False):
            return "break"
        return None

    def _set_bluetooth_choice_locked(self, locked):
        """Keep Yes/No looking selected, but stop them from being changed."""
        self._bluetooth_choice_locked = bool(locked)
        for widget in self._bluetooth_choice_buttons():
            set_pointer_blocked(widget, locked)
        refresh_disabled_pointer(self)

    def start_bluetooth(self):
        if getattr(self, "_bluetooth_choice_locked", False):
            return
        self._show_bluetooth_choice("yes")
        self.disable_controls()
        self.log("Starting Bluetooth connection in a separate thread...")
        # Only start if not already running
        if not hasattr(self, 'bluetooth_thread') or not self.bluetooth_thread.is_alive():
            self.bluetooth_thread = threading.Thread(target=self.bluetooth_connect_thread, daemon=True)
            self.bluetooth_thread.start()

    def bluetooth_connect_thread(self):
        try:
            self.bluetooth_connected = False
            self.result = start_connection(False, self.use_web.get())
            if self.result:
                self.bluetooth_connected = True
                # Enable the start scheduler button
                self.after(0, lambda: self._set_scheduler_button("Start Scheduler", tk.NORMAL))
                # Update the Settings Tab IP address with dwarf_ip and save config.ini
                data_config = config_py.get_config_data()
                dwarf_ip = data_config['ip']
                dwarf_id = data_config['dwarf_id']
                dwarfName = "Dwarf II"
                DWARF_NAME_MAP = {
                  2: "Dwarf II",
                  3: "Dwarf3",
                  5: "Dwarf Mini",
                }
                DWARF_TYPE_DEVICE = {
                  2: "Dwarf II",
                  3: "Dwarf 3 Tele Lens",
                  5: "Dwarf Mini Tele Lens",
                }
                dwarfName = DWARF_NAME_MAP.get(config_to_dwarf_id_int(dwarf_id), "Unknown Dwarf")
                typeDevice = DWARF_TYPE_DEVICE.get(config_to_dwarf_id_int(dwarf_id), "Unknown Dwarf")
                self.log(f"Bluetooth connected successfully. {dwarfName} @{dwarf_ip}")
                save_settings = False
                if dwarf_ip and 'dwarf_ip' in self.config_vars:
                    self.config_vars['dwarf_ip'].set(dwarf_ip)
                if typeDevice and 'device_ud' in self.config_vars:
                    self.config_vars['device_ud'].set(typeDevice)
                if save_settings:
                    settings.save_settings(self.config_vars, show_message=False)                
            else:
                self.log("Bluetooth connection failed.")
        except Exception as e:
            self.log(f"Bluetooth connection failed: {e}")

      #  self.after(0, self.start_scheduler)

    def skip_bluetooth(self):
        if getattr(self, "_bluetooth_choice_locked", False):
            return
        self._show_bluetooth_choice("no")
        self.log("Bluetooth connection skipped.")
        # Enable the start scheduler button
        self.bluetooth_connected = False
        self._set_scheduler_button("Start Scheduler", tk.NORMAL)

    def start_scheduler(self):
        if getattr(self, "_scheduler_stopping", False):
            self.log("Scheduler is still stopping.")
            return
        self.disable_controls()
        self._set_bluetooth_choice_locked(True)
        if not self.scheduler_running:
            self.log("Astro Dwarf Scheduler is starting...")
            self._scheduler_connecting = True
            self.scheduler_running = True
            self.toggle_buttons("waiting")
            self.scheduler_stop_event.clear()
            self.start_logHandler()
            self.scheduler_start_time = datetime.now()  # Track when the scheduler starts
            self.reset_total_runtime()
            # Only start if not already running
            if not hasattr(self, 'scheduler_thread') or not self.scheduler_thread.is_alive():
                self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
                self.scheduler_thread.start()
        # Update file counts when scheduler starts
        if hasattr(self, 'update_session_counts'):
            self.update_session_counts()

    def stop_scheduler(self):
        self.stop_logHandler()  # Stop the logging handler
        if self.scheduler_running:

            self.log("Stopping the scheduler...")
            self._scheduler_connecting = False
            self._scheduler_stopping = True
            self.scheduler_running = False
            self.scheduler_stop_event.set()
            self._stop_idle_video_preview("Video stream is off")
            try:
                request_command_interrupt()
            except Exception:
                pass
            self._sync_stop_session_button()

            # Wait for thread to finish with timeout
            self.verifyCountdown(20)

            # Stop an imaging session or main-page task if one is actually running.
            self.run_stop_astro_photo(False)
            
            deadline = time.time() + 20
            def wait_for_stop_scheduler_completion():
                # Check if stop_astro_photo thread is still running
                stop_photo_running = hasattr(self, 'stop_astro_photo') and self.stop_astro_photo.is_alive()
                # Check if scheduler thread is still running
                scheduler_running = hasattr(self, 'scheduler_thread') and self.scheduler_thread.is_alive()

                def finalize_stop():
                    self._scheduler_stopping = False
                    self.log("Scheduler and Astro Photo have fully stopped.")
                    self.toggle_buttons(tk.DISABLED)    
                    # Only enable the scheduler button so user can start again
                    self._set_scheduler_button("Start Scheduler", tk.NORMAL)
                    self.enable_controls()
                    self.scheduler_stopped = True
                    # Update file counts when scheduler stops
                    if hasattr(self, 'update_session_counts'):
                        self.update_session_counts()

                if (stop_photo_running or scheduler_running) and time.time() < deadline:
                    self.after(100, wait_for_stop_scheduler_completion)
                    return
                if stop_photo_running or scheduler_running:
                    self.log("Stop is taking too long; returning control of the app.")
                    try:
                        request_command_interrupt()
                    except Exception:
                        pass
                finalize_stop()

            # Start monitoring both threads
            wait_for_stop_scheduler_completion()
            self.toggle_buttons(tk.NONE)    
                    
        else:
            self.toggle_buttons(tk.DISABLED)
            self.log("Scheduler is stopped")

        # Update file counts when scheduler stops
        if hasattr(self, 'update_session_counts'):
            self.update_session_counts()

    def toggle_scheduler(self):
        """Toggle between start and stop scheduler functionality."""
        if getattr(self, "_scheduler_stopping", False):
            self.log("Scheduler is still stopping.")
            return
        if self.scheduler_running:
            self.stop_scheduler()
        else:
            self.start_scheduler()

    def unset_lock_device(self):
        # Only start if not already running
        if not hasattr(self, 'unset_thread') or not self.unset_thread.is_alive():
            self.unset_thread = threading.Thread(target=self.run_unset_lock_device, daemon=True)
            self.unset_thread.start()

    def start_eq_solving(self):
        if not self._can_start_action("EQ Solving"):
            return
        self._begin_action("EQ Solving")
        self.eq_thread = threading.Thread(target=self.run_start_eq_solving, daemon=True)
        self.eq_thread.start()

    def start_polar_position(self):
        if not self._can_start_action("Polar Position"):
            return
        self._begin_action("Polar Position")
        self.polar_thread = threading.Thread(target=self.run_start_polar_position, daemon=True)
        self.polar_thread.start()

    def start_calibration(self):
        if not self._can_start_action("Calibration"):
            return
        self._begin_action("Calibration")
        self.cal_thread = threading.Thread(target=self.run_start_calibration, daemon=True)
        self.cal_thread.start()

    def start_auto_focus_button(self):
        if not self._can_start_action("Auto Focus"):
            return
        self._begin_action("Auto Focus")
        self.autofocus_thread = threading.Thread(target=self.start_auto_focus, daemon=True)
        self.autofocus_thread.start()

    def start_powerdown(self):
        # Show confirmation dialog
        result = messagebox.askyesno(
            "Confirm Power Down", 
            "Are you sure you want to power down the Dwarf?\n\nThis will shut down the device completely.",
            icon="warning"
        )
        
        if result:  # User clicked "Yes"
            # Only start if not already running and user confirmed
            if not hasattr(self, 'powerdown_thread') or not self.powerdown_thread.is_alive():
                self.powerdown_thread = threading.Thread(target=self.run_start_powerdown, daemon=True)
                self.powerdown_thread.start()
        else:
            # User clicked "No" or closed dialog - do nothing
            self.log("Power down cancelled by user.")

    def start_reboot(self):
        # Show confirmation dialog
        result = messagebox.askyesno(
            "Confirm Power Down", 
            "Are you sure you want to reboot the Dwarf?",
            icon="warning"
        )
        
        if result:  # User clicked "Yes"
            # Only start if not already running and user confirmed
            if not hasattr(self, 'reboot_thread') or not self.reboot_thread.is_alive():
                self.reboot_thread = threading.Thread(target=self.run_start_reboot, daemon=True)
                self.reboot_thread.start()
        else:
            # User clicked "No" or closed dialog - do nothing
            self.log("Reboot cancelled by user.")

    def run_stop_astro_photo(self, confirm=True):
        session = bool(getattr(self, "session_running", False))
        action = getattr(self, "_current_action", None)
        if not should_send_device_stop(session, action):
            if confirm:
                self.log("Nothing is running.", level="warning")
                self._sync_stop_session_button()
            return

        if confirm and session:
            result = messagebox.askyesno(
                "Confirm Stopping Astro Photo Session",
                "Are you sure you want to stop the current session?",
                icon="warning",
            )
            if not result:
                self.log("Stopping session cancelled by user.")
                return

        self._stop_in_progress = True
        self.action_stop_event.set()
        if session:
            self.session_stop_event.set()
            self.session_running = False
        self._sync_stop_session_button()
        if not hasattr(self, "stop_astro_photo") or not self.stop_astro_photo.is_alive():
            self.stop_astro_photo = threading.Thread(
                target=self._stop_current_session,
                kwargs={"stop_imaging": session, "action_name": action},
                daemon=True,
            )
            self.stop_astro_photo.start()
        else:
            try:
                request_command_interrupt()
            except Exception:
                pass
            self.log("Stop already running; waiting for it to finish before another command.")

    def _stop_current_session(self, stop_imaging=False, action_name=None):
        if action_name and not stop_imaging:
            self.log(f"Stopping {action_name}...")
        else:
            self.log("Stopping current session...")
        self.action_stop_event.set()
        if stop_imaging:
            self.session_stop_event.set()
        try:
            stop_telescope_activity(action_name=action_name, stop_imaging=stop_imaging)
            if action_name and not stop_imaging:
                self.log(f"{action_name} stop command sent to the telescope.")
            else:
                self.log("Stop commands sent; waiting for the session to finish...")
        except Exception as e:
            self.log(f"Error requesting stop: {e}", level="error")
        finally:
            self._stop_in_progress = False
            self._end_action(action_name)
            self.after(0, self._sync_stop_session_button)

    def toggle_lights(self):
        # Only start if not already running
        if not hasattr(self, 'toogle_lights_thread') or not self.toogle_lights_thread.is_alive():
            self.toogle_lights_thread = threading.Thread(target=self.run_toogle_lights, daemon=True)
            self.toogle_lights_thread.start()

    def verifyCountdown(self, wait):
        '''
        verifyCountdown that checks scheduler status and waits for stop or timeout
        '''
        if getattr(self, "_scheduler_stopping", False):
            thread_alive = hasattr(self, "scheduler_thread") and self.scheduler_thread.is_alive()
            if thread_alive and wait > 0:
                self.after(1000, self.verifyCountdown, wait - 1)
                return
            if thread_alive:
                self.log("Timeout reached, forcing disconnect...")
                try:
                    perform_disconnect()
                except Exception:
                    pass
            return
        if self.scheduler_stopped or not self.scheduler_running:
            self.log("Scheduler is stopping...")
            # Only enable the scheduler button so user can start again
            self._set_scheduler_button("Start Scheduler", tk.NORMAL)
            self.enable_controls()
        elif wait > 0:
            # Schedule the verifyCountdown to run again after 1 second
            self.after(1000, self.verifyCountdown, wait - 1)
        else:
            self.log("Timeout reached, forcing disconnect...")
            try:
                perform_disconnect()
            except:
                pass
            self.scheduler_stopped = True
            # Only enable the scheduler button so user can start again
            self._set_scheduler_button("Start Scheduler", tk.NORMAL)
            self.enable_controls()

    def run_scheduler(self):
        try:
            self.scheduler_stopped = False
            self.session_running = False  # Track if a session is running
            attempt = 0
            result = False
            while not result and attempt < 3 and self.scheduler_running and not self.scheduler_stop_event.is_set():
                attempt += 1
                result = start_STA_connection(not self.bluetooth_connected)

            if result:
                def on_connected():
                    self._scheduler_connecting = False
                    self.toggle_buttons(tk.NORMAL)
                    self.log("Connected to the Dwarf")
                self.after(0, on_connected)
                def discover_lights():
                    on = self._discover_light_state()
                    if on is True:
                        self.log("Lights are on")
                    elif on is False:
                        self.log("Lights are off")
                    else:
                        self.log("Light state is not reported yet", level="warning")
                    self.after(0, self._refresh_lights_button)
                threading.Thread(target=discover_lights, daemon=True).start()

                while result and self.scheduler_running and not self.scheduler_stop_event.is_set():
                    try:
                        session_start = datetime.now()
                        sessions_processed = check_and_execute_commands(ui_instance=self, stop_event=self.scheduler_stop_event, skip_time_checks=self.skip_time_checks)
                        session_end = datetime.now()

                        if sessions_processed:
                            # Add this session's runtime to the total
                            session_runtime = (session_end - session_start).total_seconds()
                            self.add_to_total_runtime(session_runtime)
                            self.log("Session completed, checking for more sessions...")
                            # Brief pause between sessions
                            time.sleep(1)
                            continue

                        self.reset_total_runtime()

                        # If no sessions were processed and scheduler is still running, continue checking
                        if not sessions_processed and self.scheduler_running and not self.scheduler_stop_event.is_set():
                            self.session_running = False  # No session is running
                            self.after(0, self._sync_stop_session_button)

                            # Instead of sleeping for 10 seconds, check every 0.1s if stopped
                            total_sleep = 0
                            while total_sleep < 10 and self.scheduler_running and not self.scheduler_stop_event.is_set():
                                time.sleep(0.1)
                                total_sleep += 0.1

                    except Exception as e:
                        self.log(f"Error in scheduler loop: {e}", level="error")
                        self._stop_video_stream = True
                        self.session_running = False
                        break

        except KeyboardInterrupt:
            self.log("Operation interrupted by the user.")
        except Exception as e:
            self.log(f"Scheduler error: {e}", level="error")
        finally:
            self.session_running = False  # Ensure session state is reset
            self._stop_idle_video_preview("Video stream is off")
            self.after(0, self._sync_video_tools)
            # Ensure proper cleanup
            try:
                perform_disconnect()
                self.log("Disconnected from the Dwarf.")
            except Exception as e:
                self.log(f"Error during disconnect: {e}", level="error")

            # Update UI state on main thread
            def update_ui_after_scheduler():
                self._scheduler_connecting = False
                self.scheduler_running = False
                self.scheduler_stopped = True
                if getattr(self, "_scheduler_stopping", False):
                    # Stop Scheduler is waiting for the stop-task thread too.
                    self.after(0, self._sync_stop_session_button)
                    return
                self.toggle_buttons(tk.DISABLED)
                # Only enable the scheduler button so user can start again
                self._set_scheduler_button("Start Scheduler", tk.NORMAL)
                self.enable_controls()
                if hasattr(self, 'update_session_counts'):
                    self.update_session_counts()
                self.log("Scheduler stopped - no more sessions to process.", level="success")
                self.stop_logHandler()  # Stop the logging handler here as well

            self.after(0, update_ui_after_scheduler)

    def run_unset_lock_device(self):
        try:
            attempt = 0
            result = False
            while not result and attempt < 3:
                attempt += 1
                if self.unset_lock_device_mode:
                    result = unset_HostMaster()
                else:
                    result = set_HostMaster()
                if not result:
                    time.sleep(10)  # Sleep for 10 seconds between checks
            if result:
                def update_unlock_button():
                    if self.unset_lock_device_mode:
                        self.unlock_button.config(text="Set as Host")
                    else:
                        self.unlock_button.config(text="Unset as Host")
                    self.unset_lock_device_mode = not self.unset_lock_device_mode
                    self.unlock_button.update()
                self.after(0, update_unlock_button)
        except Exception as e:
            self.log(f"Error in unset_lock_device: {e}", level="error")

    def run_start_eq_solving(self):
        try:
            attempt = 0
            result = False
            self.log("Starting EQ Solving process...")
            while not result and attempt < 3:
                if self._action_should_stop():
                    self.log("EQ Solving stopped")
                    return
                attempt += 1
                result = start_polar_align()
                if self._action_should_stop():
                    self.log("EQ Solving stopped")
                    return
                if not result:
                    if not self._wait_interruptible(10):
                        self.log("EQ Solving stopped")
                        return
        except Exception as e:
            if self._action_should_stop():
                self.log("EQ Solving stopped")
                return
            try:
                read_longitude()
                read_latitude()
                self.log(f"Error during EQ Solving: {e}", level="error")
            except Exception as e:
                self.log(f"Error: Missing Longitude/Latitude in settings", level="error")
        finally:
            self._end_action("EQ Solving")

    def run_start_polar_position(self):
        try:
            dwarf_id = 2
            data_config = config_py.get_config_data()
            if data_config.get("dwarf_id"):
                dwarf_id = data_config['dwarf_id']

            dwarf_id_int = config_to_dwarf_id_int(dwarf_id)

            attempt = 0
            result = False
            self.log("Starting Polar Alignment positioning...")

            while not result and attempt < 1:
                if self._action_should_stop():
                    self.log("Polar Position stopped")
                    return
                attempt += 1
                # Rotation Motor Resetting
                result = motor_action(5)
                if self._action_should_stop():
                    self.log("Polar Position stopped")
                    return
                if result:
                    # Pitch Motor Resetting
                    result = motor_action(6)
                if self._action_should_stop():
                    self.log("Polar Position stopped")
                    return

                if result and dwarf_id_int >= 3:
                    # Rotation Motor positioning D3
                    result = motor_action(9)
                elif result:
                    # Rotation Motor positioning
                    result = motor_action(2)
                if self._action_should_stop():
                    self.log("Polar Position stopped")
                    return
                if result and dwarf_id_int >= 3:
                    # Pitch Motor positioning D3
                    result = motor_action(7)
                elif result:
                    # Pitch Motor positioning
                    result = motor_action(3)

                if self._action_should_stop():
                    self.log("Polar Position stopped")
                    return
                if result:
                    self.log("Successfully positioned for polar alignment")
                if not result:
                    if not self._wait_interruptible(10):
                        self.log("Polar Position stopped")
                        return

        except Exception as e:
            if self._action_should_stop():
                self.log("Polar Position stopped")
            else:
                self.log(f"Error in Polar Align positioning: {e}", level="error")
        finally:
            self._end_action("Polar Position")

    def start_auto_focus(self):
        try:
            self.log("Starting Auto Focus process...")
            if self._action_should_stop():
                self.log("Auto Focus stopped")
                return
            setattr(self, '_stop_video_stream', False)
            self.start_video_preview(ensure_live=False)

            continue_action = perform_time()
            if self._action_should_stop():
                self.log("Auto Focus stopped")
                return
            verify_action(continue_action, "step_0")

            # Go Live
            continue_action = perform_GoLive()
            if self._action_should_stop():
                self.log("Auto Focus stopped")
                return
            verify_action(continue_action, "step_1a")
            self.reconnect_video_preview()

            wait_after = 5
            wait_before = 5

            continue_action = perform_stop_goto()
            if self._action_should_stop():
                self.log("Auto Focus stopped")
                return
            verify_action(continue_action, "step_6")
            if not self._wait_interruptible(wait_before, f"Waiting for {wait_before} seconds"):
                self.log("Auto Focus stopped")
                return

            self.log("Starting Auto Focus")
            if not self._wait_interruptible(wait_before, f"Waiting for {wait_before} seconds"):
                self.log("Auto Focus stopped")
                return
            continue_action = perform_start_autofocus()
            if self._action_should_stop():
                self.log("Auto Focus stopped")
                return
            verify_action(continue_action, "step_7")
            if not self._wait_interruptible(wait_after, f"Waiting for {wait_after} seconds"):
                self.log("Auto Focus stopped")
                return
            continue_action = perform_stop_goto()
            if self._action_should_stop():
                self.log("Auto Focus stopped")
                return
            if not self._wait_interruptible(wait_after, f"Waiting for {wait_after} seconds"):
                self.log("Auto Focus stopped")
                return
            continue_action = perform_start_autofocus()

        except Exception as e:
            if self._action_should_stop():
                self.log("Auto Focus stopped")
            else:
                self.log(f"Error in Auto Focus: {e}", level="error")
        finally:
            self._end_action("Auto Focus")

    def run_start_calibration(self):
        try:

            # Session initialization
            self.log("Starting Calibration process...")
            if self._action_should_stop():
                self.log("Calibration stopped")
                return
            setattr(self, '_stop_video_stream', False)
            self.start_video_preview(ensure_live=False)

            continue_action = perform_time()
            if self._action_should_stop():
                self.log("Calibration stopped")
                return
            verify_action(continue_action, "step_0")

            # Go Live
            continue_action = perform_GoLive()
            if self._action_should_stop():
                self.log("Calibration stopped")
                return
            verify_action(continue_action, "step_1a")
            self.reconnect_video_preview()

            wait_after = 5
            wait_before = 5

            continue_action = perform_stop_goto()
            if self._action_should_stop():
                self.log("Calibration stopped")
                return
            verify_action(continue_action, "step_6")
            if not self._wait_interruptible(wait_before, f"Waiting for {wait_before} seconds"):
                self.log("Calibration stopped")
                return

            self.log("Starting Calibration")
            if not self._wait_interruptible(wait_before, f"Waiting for {wait_before} seconds"):
                self.log("Calibration stopped")
                return
            continue_action = perform_calibration()
            if self._action_should_stop():
                self.log("Calibration stopped")
                return
            verify_action(continue_action, "step_7")
            if not self._wait_interruptible(wait_after, f"Waiting for {wait_after} seconds"):
                self.log("Calibration stopped")
                return
            continue_action = perform_stop_goto()
            if self._action_should_stop():
                self.log("Calibration stopped")
                return
            if not self._wait_interruptible(wait_after, f"Waiting for {wait_after} seconds"):
                self.log("Calibration stopped")
                return

        except Exception as e:
            if self._action_should_stop():
                self.log("Calibration stopped")
            else:
                self.log(f"Error in Calibration: {e}", level="error")
        finally:
            self._end_action("Calibration")

    def run_stop_astrophotos(self):
        try:
            self.log("Stopping Astro Photo Session...")
            setattr(self, '_stop_video_stream', False)
            self.start_video_preview()

            wait_after = 5
            wait_before = 5

            self.log(f"Waiting for {wait_before} seconds")
            time.sleep(wait_before)

            continue_action = perform_stopAstroPhoto()
            verify_action(continue_action, "step_16")

            self.log(f"Waiting for {wait_after} seconds")
            time.sleep(wait_after)

            setattr(self, '_stop_video_stream', True)

        except Exception as e:
            self.log(f"Error in Stop AstroPhoto: {e}", level="error")
            setattr(self, '_stop_video_stream', True)

    def run_toogle_lights(self):
        try:
            self.log("Reading light state from the scope...")
            lights_on = self._discover_light_state()
            self.status_powerlight, self.status_rgblight = self._read_light_states()
            if lights_on is None:
                self.log("Light state unknown; turning lights off")
                lights_on = True
            if lights_on:
                self.log("Turning lights off")
                perform_powerCloseRGB()
                perform_powerIndOff()
            else:
                self.log("Turning lights on")
                perform_powerOpenRGB()
                perform_powerIndOn()
            time.sleep(0.3)
            self.status_powerlight, self.status_rgblight = self._read_light_states()
            self.after(0, self._refresh_lights_button)
        except Exception as e:
            self.log(f"Error toggling lights: {e}", level="error")

    def run_start_powerdown(self):
        try:
            self.log("Starting Power Down process...")
            self.toggle_buttons(tk.NONE)
            # Run toggle_scheduler in background with 5 second delay
            def delayed_toggle():
                time.sleep(5)
                self.toggle_scheduler()            
            threading.Thread(target=delayed_toggle, daemon=True).start()
            perform_powerdown()
            
        except Exception as e:
            self.log(f"Error in Power Down: {e}", level="error")
            setattr(self, '_stop_video_stream', True)

    def run_start_reboot(self):
        try:
            self.log("Starting Reboot process...")
            self.toggle_buttons(tk.NONE)
            # Run toggle_scheduler in background with 5 second delay
            def delayed_toggle():
                time.sleep(5)
                self.toggle_scheduler()            
            threading.Thread(target=delayed_toggle, daemon=True).start()
            perform_reboot()
            
        except Exception as e:
            self.log(f"Error in Power Down: {e}", level="error")
            setattr(self, '_stop_video_stream', True)

    def start_logHandler(self):

        # Create an instance of the TextHandler and attach it to the logger
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)  # Ensure all messages are captured

        self.text_handler = TextHandler(self.log_text)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',  datefmt='%y-%m-%d %H:%M:%S')
        self.text_handler.setFormatter(formatter)
        self.text_handler.setLevel(NOTICE_LEVEL_NUM)
        self.logger.addHandler(self.text_handler)

    def stop_logHandler(self):
        if hasattr(self, 'text_handler') and self.text_handler in self.logger.handlers:
            self.logger.removeHandler(self.text_handler)  # Remove the TextHandler
            self.text_handler = None  # Clear the reference to avoid reuse

    def log(self, message, level="info"):
        if level == "error":
            tag = "error"
            emoji = "✗ "
        elif level == "warning":
            tag = "warning"
            emoji = "⚠ "
        elif level == "info":
            tag = "info"
            emoji = "◉ "
        elif level == "success":
            tag = "success"
            emoji = "✓ "
        else:
            tag = "default"
            emoji = "⇒ "

        if self.log_text is not None:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, emoji + message + "\n", tag)
            self.log_text.see(tk.END)

    def update_session_info(self):
        """
        Update the session information label with the next session's start time,
        the runtime of the current session, or a countdown to the next session.
        """
        self._sync_stop_session_button()
        # Only update session_info_label if we're running in a GUI context
        has_gui = hasattr(self, 'session_info_label') and self.session_info_label is not None
        
        # Additional check to ensure the widget still exists
        if has_gui:
            try:
                # Test if the widget still exists by accessing its properties
                self.session_info_label.winfo_exists()
            except (tk.TclError, AttributeError):
                # Widget has been destroyed, disable GUI updates
                has_gui = False

        from astro_dwarf_scheduler import LIST_ASTRO_DIR

        if self.scheduler_running and self.session_running:
            # Check for the next session in the ToDo directory
            todo_dir_var = "CURRENT_DIR" if getattr(self, 'session_running', False) else "TODO_DIR"
            todo_dir = LIST_ASTRO_DIR[todo_dir_var]

            if os.path.exists(todo_dir):
                todo_files = get_json_files_sorted(todo_dir)
                if todo_files:
                    next_session_file = todo_files[0]
                    next_session_path = os.path.join(todo_dir, next_session_file)
                    try:
                        with open(next_session_path, 'r') as f:
                            session_data = json.loads(f.read())

                        # Always check for up next countdown if scheduler is running
                        # Track the last session file to reset timer if a new file loads
                        if not hasattr(self, 'last_session_path') or self.last_session_path != next_session_path:
                            self.session_start_time = datetime.now()
                            self.last_session_path = next_session_path

                        if not hasattr(self, 'session_start_time'):
                            self.session_start_time = datetime.now()

                        estimated_runtime = self.calculate_end_time(session_data.get('command', {}))
                        # Ensure self.session_start_time is a datetime object
                        if not isinstance(self.session_start_time, datetime):
                            self.session_start_time = datetime.now()
                        this_session_runtime = datetime.now() - self.session_start_time
                        this_session_runtime_str = str(this_session_runtime).split('.')[0]  # Format as HH:MM:SS
                        # Format total runtime (add current session's runtime live)
                        if not hasattr(self, 'total_session_runtime'):
                            self.total_session_runtime = 0
                        live_total_seconds = int(self.total_session_runtime + this_session_runtime.total_seconds())
                        total_runtime_td = timedelta(seconds=live_total_seconds)
                        total_runtime_str = str(total_runtime_td).split('.')[0]
                        self.last_text=f"Session runtime: {this_session_runtime_str} / {estimated_runtime} - Total runtime: {total_runtime_str}"
                        if has_gui:
                            try:
                                self.session_info_label.config(text=self.last_text, fg=palette["runtime"])
                            except tk.TclError as e:
                                print(f"Error updating session_info_label: {e}")
                                has_gui = False

                    except Exception as e:
                        if has_gui:
                            try:
                                self.session_info_label.config(text=f"Error reading next session. {e}\n{traceback.format_exc()}")
                            except tk.TclError as e:
                                print(f"Error updating session_info_label: {e}")
                                has_gui = False
            else:
                if has_gui:
                    try:
                        self.session_info_label.config(text="No session directory found - Check configuration", fg=palette["danger_text"])
                    except tk.TclError as e:
                        print(f"Error updating session_info_label: {e}")
                        has_gui = False
        else:
            # Check if there are any sessions in ToDo to provide useful information
            todo_dir = LIST_ASTRO_DIR["TODO_DIR"]
            if os.path.exists(todo_dir):
                todo_files = get_json_files_sorted(todo_dir)
                    
                if todo_files:
                    next_session_file = todo_files[0]
                    next_session_path = os.path.join(todo_dir, next_session_file)
                    with open(next_session_path, 'r') as f:
                        session_data = json.loads(f.read())
                    # Get scheduled date/time from session file
                    id_command = session_data.get('command', {}).get('id_command', {})
                    goto_manual = session_data.get('command', {}).get('goto_manual', {})
                    scheduled_date = id_command.get('date', None)
                    scheduled_time = id_command.get('time', None)
                    scheduled_target = goto_manual.get('target', 'Unknown')
                    show_countdown = False
                    countdown_str = ''

                    if scheduled_date and scheduled_time:
                        try:
                            scheduled_dt = datetime.strptime(f"{scheduled_date} {scheduled_time}", "%Y-%m-%d %H:%M:%S")
                            now = datetime.now()
                            if scheduled_dt > now:
                                show_countdown = True
                                countdown = scheduled_dt - now
                                countdown_str = str(countdown).split('.')[0]
                        except Exception:
                            pass

                    if show_countdown and self.scheduler_running:
                        if has_gui:
                            try:
                                self.session_info_label.config(
                                    text=f"Up next: {scheduled_target} - {countdown_str} at {scheduled_date} {scheduled_time}",
                                    fg=palette["countdown"]
                                )
                            except tk.TclError as e:
                                print(f"Error updating session_info_label: {e}")
                                has_gui = False
                    else:
                        if has_gui:
                            try:
                                self.session_info_label.config(
                                text=f"Ready to start - {len(todo_files)} session(s) waiting. Click 'Start Scheduler' to begin.",
                                fg=palette["success_text"]
                                )
                            except tk.TclError as e:
                                print(f"Error updating session_info_label: {e}")
                                has_gui = False
                else:
                    if has_gui:
                        try:
                            self.session_info_label.config(
                                text="No sessions scheduled - Create sessions in 'Create Session' tab to get started.",
                                fg=palette["info_text"]
                            )
                        except tk.TclError as e:
                            print(f"Error updating session_info_label: {e}")
                            has_gui = False
            else:
                if has_gui:
                    try:
                        self.session_info_label.config(
                            text="Session directory not found - Check your configuration settings.",
                            fg=palette["danger_text"]
                        )
                    except tk.TclError as e:
                        print(f"Error updating session_info_label: {e}")
                        has_gui = False

            if self.last_text != "":
                self.log(self.last_text)
                self.last_text = ""

        # Schedule the next update
        self.after(1000, self.update_session_info)

# Main application
if __name__ == "__main__":
    app = AstroDwarfSchedulerApp()

    def handler(sig, frame):
        print("\nExiting Astro Dwarf Scheduler.")
        app.quit()

    signal.signal(signal.SIGINT, handler)
    try:
        app.mainloop()
    except KeyboardInterrupt:
        # This is a fallback, but the handler should catch Ctrl+C
        print("\nExiting Astro Dwarf Scheduler.")
