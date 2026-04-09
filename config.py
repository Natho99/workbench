# config.py
"""
All application-wide constants, paths, styling, and format definitions.
"""
import os

# ── Paths ──────────────────────────────────────────────────────────────────────
DESKTOP       = os.path.join(os.path.expanduser("~"), "Desktop")
BEYONIC_DIR   = os.path.join(DESKTOP, "BEYONIC_TRANSFORMED")
FLEXIPAY_DIR  = os.path.join(DESKTOP, "FLEXIPAY_TRANSFORMED")
CLEANED_PATH  = os.path.join(DESKTOP, "cleaned_input.csv")

os.makedirs(BEYONIC_DIR,  exist_ok=True)
os.makedirs(FLEXIPAY_DIR, exist_ok=True)

# ── Processing ─────────────────────────────────────────────────────────────────
MAX_ROWS = 500

# ── Colours ────────────────────────────────────────────────────────────────────
THEME_BG     = "#f4e3b2"   # Cream / Beige
THEME_ACCENT = "#c9a66b"   # Gold / Brown
THEME_CARD   = "#fdf6e3"   # Slightly lighter card background
THEME_INPUT  = "#fffdf5"   # Entry background
THEME_BORDER = "#d4b483"   # Input border
TEXT_COLOR   = "#3a2f24"   # Dark Brown
TEXT_MUTED   = "#8a7560"   # Muted label text
TEXT_ERROR   = "#b03030"   # Red for warnings
TEXT_SUCCESS = "#2a6e3a"   # Green for success hints

# ── Fonts ──────────────────────────────────────────────────────────────────────
FONT_BODY   = ("Poppins", 10)
FONT_BOLD   = ("Poppins", 10, "bold")
FONT_TITLE  = ("Poppins", 12, "bold")
FONT_HEADER = ("Poppins", 16, "bold")
FONT_SMALL  = ("Poppins",  9)
FONT_MONO   = ("Consolas",  9)

# ── Mode / Dropdown options ────────────────────────────────────────────────────
MODE_OPTIONS          = ["Beyonic", "FlexiPay", "JSON Generator"]
# Order updated: MM/DD/YYYY now appears first in the dropdown
DATE_SEQUENCE_OPTIONS = ["MM/DD/YYYY", "DD/MM/YYYY"]
JSON_TYPE_OPTIONS    = ["Beyonic", "Airtel", "Bank", "Flexipay"]
DROPDOWN_PLACEHOLDER = "-- Select --"

# ── Date formats ───────────────────────────────────────────────────────────────
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