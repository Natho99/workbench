#!/usr/bin/env python
# coding: utf-8
# config.py ── macOS Optimized Application Constants
# ════════════════════════════════════════════════════════════════════════

import os
import sys

# ── Paths (macOS iCloud Aware) ────────────────────────────────────────────────
def get_desktop_path():
    """Resolves Desktop path even if redirected by iCloud Drive on macOS."""
    home = os.path.expanduser("~")
    standard_desktop = os.path.join(home, "Desktop")
    icloud_desktop = os.path.join(home, "Library", "Mobile Documents", "com~apple~CloudDocs", "Desktop")
    
    if sys.platform == "darwin" and os.path.exists(icloud_desktop):
        return icloud_desktop
    return standard_desktop

DESKTOP       = get_desktop_path()
BEYONIC_DIR   = os.path.join(DESKTOP, "BEYONIC_TRANSFORMED")
FLEXIPAY_DIR  = os.path.join(DESKTOP, "FLEXIPAY_TRANSFORMED")
CLEANED_PATH  = os.path.join(DESKTOP, "cleaned_input.csv")

# Ensure directories exist
os.makedirs(BEYONIC_DIR,  exist_ok=True)
os.makedirs(FLEXIPAY_DIR, exist_ok=True)

# ── Processing ────────────────────────────────────────────────────────────────
MAX_ROWS = 500

# ── Colours (4G Workbench Palette) ────────────────────────────────────────────
THEME_BG     = "#f4e3b2"   # Cream / Beige
THEME_ACCENT = "#c9a66b"   # Gold / Brown
THEME_CARD   = "#fdf6e3"   # Slightly lighter card background
THEME_INPUT  = "#fffdf5"   # Entry background
THEME_BORDER = "#d4b483"   # Input border
TEXT_COLOR   = "#3a2f24"   # Dark Brown
TEXT_MUTED   = "#8a7560"   # Muted label text
TEXT_ERROR   = "#b03030"   # Red for warnings
TEXT_SUCCESS = "#2a6e3a"   # Green for success hints

# ── Fonts (macOS System Stack Fallbacks) ──────────────────────────────────────
# On Mac, fonts appear ~25% smaller than Windows; sizes are adjusted for Retina.
_BASE_FONT = "Helvetica Neue" if sys.platform == "darwin" else "Poppins"
_MONO_FONT = "Menlo" if sys.platform == "darwin" else "Consolas"

FONT_BODY   = (_BASE_FONT, 11)
FONT_BOLD   = (_BASE_FONT, 11, "bold")
FONT_TITLE  = (_BASE_FONT, 13, "bold")
FONT_HEADER = (_BASE_FONT, 18, "bold")
FONT_SMALL  = (_BASE_FONT, 10)
FONT_MONO   = (_MONO_FONT, 10)

# ── Mode / Dropdown options ───────────────────────────────────────────────────
MODE_OPTIONS          = ["Beyonic", "FlexiPay", "JSON Generator"]
DATE_SEQUENCE_OPTIONS = ["MM/DD/YYYY", "DD/MM/YYYY"]
JSON_TYPE_OPTIONS     = ["Beyonic", "Airtel", "Bank", "Flexipay"]
DROPDOWN_PLACEHOLDER  = "-- Select --"

# ── Date formats ──────────────────────────────────────────────────────────────
TARGET_DATE_FORMAT  = "%d-%m-%Y %H:%M:%S"
TARGET_DATE_DISPLAY = "DD-MM-YYYY HH:MM:SS"

UNAMBIGUOUS_INPUT_FORMATS = [
    "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%d",          "%Y/%m/%d",
]

AMBIGUOUS_FORMAT_PAIRS = [
    ("%d-%m-%Y %H:%M:%S", "%m-%d-%Y %H:%M:%S"),
    ("%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S"),
    ("%d/%m/%Y %H:%M",    "%m/%d/%Y %H:%M"),
    ("%d-%m-%Y",          "%m-%d-%Y"),
    ("%d/%m/%Y",          "%m/%d/%Y"),
]