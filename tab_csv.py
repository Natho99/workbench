# tab_csv.py
"""
Instruction panel renderer.
Optimized to minimize vertical height for all modes, specifically JSON Generator.
"""
import tkinter as tk
from tkinter import ttk

from config import (
    THEME_BG, TEXT_COLOR, TEXT_ERROR,
    FONT_BODY, FONT_BOLD, FONT_TITLE,
)

def render_instructions(
    left_frame: tk.Frame,
    right_frame: tk.Frame,
    mode: str,
    ref_frame: tk.Frame | None = None,
):
    """
    Clear frames and render instructions.
    JSON Mode uses a condensed 3-column layout to minimize height.
    """
    for f in filter(None, [left_frame, right_frame, ref_frame]):
        for w in f.winfo_children():
            w.destroy()

    # ── No mode selected ─────────────────────────────────────────────────────
    if mode not in ("Beyonic", "FlexiPay", "JSON Generator"):
        tk.Label(
            left_frame,
            text="Select a Mode above to view instructions.",
            font=FONT_BODY, bg=THEME_BG, fg=TEXT_COLOR,
        ).pack(anchor="w")
        return

    # ══════════════════════════════════════════════════════════════════════════
    # JSON GENERATOR MODE — Condensed 3-column layout
    # ══════════════════════════════════════════════════════════════════════════
    if mode == "JSON Generator":

        # ── Column 1: JSON Tool Info ──────────────────────────────────────────
        tk.Label(left_frame, text="JSON GENERATOR", font=FONT_TITLE, 
                 bg=THEME_BG, fg=TEXT_COLOR, anchor="w").pack(fill="x")
        tk.Label(left_frame, text=(
            "• Supports: Beyonic, Airtel, Bank, Flexipay.\n"
            "• Prevents manual JSON syntax errors.\n"
            " AI Hallucination Protection measures:\n" 
            "• Auto-Enforces constant fields (e.g., 'FOURTH').\n"
            "• Auto-Corrects Transaction ID prefixes (e.g., 'S' for bank or '300' for flexi)."
        ), font=FONT_BODY, bg=THEME_BG, fg=TEXT_COLOR, justify="left", anchor="w").pack(fill="x")

        # ── Column 2: Quick Steps ─────────────────────────────────────────────
        tk.Label(right_frame, text="QUICK STEPS", font=FONT_TITLE, 
                 bg=THEME_BG, fg=TEXT_COLOR, anchor="w").pack(fill="x")
        tk.Label(right_frame, text=(
            "1. Select type & paste source text.\n"
            "2. Click 🤖 Autofill with AI or fill the form manually.\n"
            "3. Verify all fields vs original docs.\n"
            "4. ⚙️ Generate ➔ 📋 Copy ➔ Paste to Shujaa."
        ), font=FONT_BODY, bg=THEME_BG, fg=TEXT_COLOR, justify="left", anchor="w").pack(fill="x")

        # ── Column 3: Reference Panel ─────────────────────────────────────────
        if ref_frame is not None:
            tk.Label(ref_frame, text="REFERENCE HOLDER PANEL", font=FONT_TITLE, 
                     bg=THEME_BG, fg=TEXT_COLOR, anchor="w").pack(fill="x")
            tk.Label(ref_frame, text=(
                "• Keeps source text visible while typing.\n"
                "• Paste data from Ticket, SMS or Statement.\n"
                "• Configure API Key in ⚙ Settings.\n"
                "• Verify AI data as accuracy may not be 100%."
            ), font=FONT_BODY, bg=THEME_BG, fg=TEXT_COLOR, justify="left", anchor="w").pack(fill="x")

        # Warning Bar (Condensed)
        ttk.Separator(left_frame, orient="horizontal").pack(fill="x", pady=(4, 2))
        tk.Label(left_frame, text="Important: This mode does not support Bulk operations,just one recon at a time.",
                 font=FONT_BOLD, bg=THEME_BG, fg=TEXT_ERROR).pack(anchor="w")
        return

    # ══════════════════════════════════════════════════════════════════════════
    # CSV MODES — Beyonic / FlexiPay (Condensed)
    # ══════════════════════════════════════════════════════════════════════════

    # Standard Horizontal Warning at the bottom
    ttk.Separator(left_frame, orient="horizontal").pack(side="bottom", fill="x", pady=(5, 0))
    tk.Label(left_frame, text="IMPORTANT: Always verify transformed CSV data against original statement.",
             font=FONT_BOLD, bg=THEME_BG, fg=TEXT_ERROR).pack(side="bottom", fill="x")

    if mode == "FlexiPay":
        tk.Label(left_frame, text="FLEXIPAY USER ACTIONS", font=FONT_TITLE, 
                 bg=THEME_BG, fg=TEXT_COLOR, anchor="w").pack(fill="x")
        tk.Label(left_frame, font=FONT_BODY, bg=THEME_BG, fg=TEXT_COLOR, justify="left", anchor="w",
            text=(
                "• Remove 'Flexipay' top label and footers.\n"
                "• Remove non-column header rows.\n"
                "• Check for exponential formats in numbers to avoid exponential mess.\n"
                "• Save the prepared file as csv then upload."
            )).pack(fill="x")

        tk.Label(right_frame, text="SYSTEM LOGIC", font=FONT_TITLE, 
                 bg=THEME_BG, fg=TEXT_COLOR, anchor="w").pack(fill="x")
        tk.Label(right_frame, font=FONT_BODY, bg=THEME_BG, fg=TEXT_COLOR, justify="left", anchor="w",
            text=(
                "• Filters 'successful', 'Airtel Cashin' & 'MERCHANT PURCHASE' rows.\n"
                "• Maps data to 10 standard columns.\n"
                "• Initiation Date ➔ DD-MM-YYYY HH:MM:SS.\n"
                "•Saves the Transformed csv with timestamped name to FLEXIPAY_TRANSFORMED folder in desktop."
            )).pack(fill="x")

    elif mode == "Beyonic":
        tk.Label(left_frame, text="BEYONIC USER ACTIONS", font=FONT_TITLE, 
                 bg=THEME_BG, fg=TEXT_COLOR, anchor="w").pack(fill="x")
        tk.Label(left_frame, font=FONT_BODY, bg=THEME_BG, fg=TEXT_COLOR, justify="left", anchor="w",
            text=(
                "• Upload downloaded CSV directly.\n"
                "• No manual editing of columns needed.\n"
                "• Ensure no exponential values in the csv."
            )).pack(fill="x")

        tk.Label(right_frame, text="SYSTEM LOGIC", font=FONT_TITLE, 
                 bg=THEME_BG, fg=TEXT_COLOR, anchor="w").pack(fill="x")
        tk.Label(right_frame, font=FONT_BODY, bg=THEME_BG, fg=TEXT_COLOR, justify="left", anchor="w",
            text=(
                "• Maps data to 7 standard columns.\n"
                "• Fixes missing Txn IDs via 'Id' column.\n"
                "• Payment Date ➔ DD-MM-YYYY HH:MM:SS.\n"
                "•Saves the Transformed csv with timestamped name to BEYONIC_TRANSFORMED folder in desktop."
            )).pack(fill="x")