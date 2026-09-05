from cx_Freeze import setup, Executable
import sys
from app_version import get_app_version, packaged_version_files

VERSION = get_app_version()

# Include additional files and folders
buildOptions = dict(
    packages=["bleak"],
    include_files=[
        ('dwarf_ble_connect/', './dwarf_ble_connect'),
        ('Install/', '.'),
        ('Install/astro_dwarf_session_UI.ico', 'astro_dwarf_session_UI.ico')  # Copy icon to root for runtime access
    ] + packaged_version_files()
)

# Define the base for a GUI application
base = 'Win32GUI' if sys.platform == 'win32' else None

# Setup function
setup(
    name="Astro Dwarf Scheduler",
    version=VERSION,
    description="Dwarf Astro Scheduler",
    options=dict(build_exe=buildOptions),
    executables=[
        Executable(
            "astro_dwarf_session_UI.py",
            base=base,
            icon="Install/astro_dwarf_session_UI.ico"
        )
    ]
)