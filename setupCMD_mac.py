"""
Setup script for building Astro Dwarf Scheduler Console application on macOS using py2app
"""

from setuptools import setup
import sys
import os
from app_version import get_app_version, packaged_version_files

VERSION = get_app_version()

# py2app setup options
OPTIONS = {
    'argv_emulation': True,
    'packages': [],
    'includes': [],
    'excludes': [],
    'resources': [],
    'plist': {
        'CFBundleName': 'AstroDwarfSchedulerConsole',
        'CFBundleDisplayName': 'Astro Dwarf Scheduler Console',
        'CFBundleVersion': VERSION,
        'CFBundleShortVersionString': VERSION,
        'CFBundleIdentifier': 'com.astrodwarf.scheduler.console',
        'LSMinimumSystemVersion': '10.9',
    }
}

# Include data files that exist  
DATA_FILES = []
if os.path.exists('dwarf_ble_connect'):
    DATA_FILES.append('dwarf_ble_connect')
if os.path.exists('config.ini'):
    DATA_FILES.append('config.ini')
if os.path.exists('config.py'):
    DATA_FILES.append('config.py')
if os.path.exists('Astro_Sessions'):
    DATA_FILES.append('Astro_Sessions')
for source, _dest in packaged_version_files():
    DATA_FILES.append(source)

setup(
    name="AstroDwarfSchedulerConsole",
    version=VERSION,
    description="Automatic Astro Session for the Dwarf - Console Version",
    author="Astro Dwarf Team",
    app=['astro_dwarf_scheduler.py'],
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
