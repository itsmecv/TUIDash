#!/usr/bin/env python3
"""Entry point for TUIDash - handles PyInstaller bundling."""

import sys
import os

# Add the src directory to path for PyInstaller
if getattr(sys, 'frozen', False):
    # Running as compiled
    base_path = sys._MEIPASS
    sys.path.insert(0, base_path)
else:
    # Running as script
    base_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(base_path))

from src.app import main

if __name__ == "__main__":
    main()
