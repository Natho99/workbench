#!/usr/bin/env python
# coding: utf-8
# tab_csv.py ── macOS Optimized Instruction Renderer
# ════════════════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk
import sys

# Ensure F_BOLD is imported from config
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
    macOS Adjustment: Increased horizontal padding to account for wider font rendering.
    """
    # Fix: Ensure we use the imported FONT_BOLD variable
    # If on Mac, we use Helvetica Neue, otherwise we use the theme's FONT_BOLD
    ui_font_bold = ("Helvetica Neue", 10, "bold") if sys.platform == "darwin" else FONT_BOLD
    
    # Clear existing content
    for f in filter(None, [left_frame, right_frame, ref_frame]):
        for w in f.winfo_children():
            w.destroy()

    # ── No mode selected ─────────────────────────────────────────────────────
    if mode not in ("Beyonic", "FlexiPay", "JSON Generator"):
        tk.Label(
            left_frame,
            text="Select a Mode above to view instructions.",
            font=FONT_BODY, bg=THEME_BG, fg=TEXT_COLOR,
            padx=5
        ).pack(anchor="w")
        return

    # ══════════════════════════════════════════════════════════════════════════
    # JSON GENERATOR MODE — Condensed 3-column layout
    # ══════════════════════════════════════════════════════════════════════════
    if mode == "JSON Generator":

        # ── Column 1: JSON Tool Info ──────────────────────────────────────────
        tk.Label(left_frame, text="JSON GENERATOR", font=FONT_TITLE, 
                 bg=THEME_BG, fg=TEXT_COLOR, anchor="w").pack(fill="x", padx=5)
        tk.Label(left_frame, text=(
            "• Supports: Beyonic, Airtel, Bank, Flexipay.\n"
            "• Prevents manual JSON syntax errors.\n"
            " AI Hallucination Protection:\n" 
            "• Enforces constant fields (e.g., 'FOURTH').\n"
            "• Auto-Corrects Transaction ID prefixes."
        ), font=FONT_BODY, bg=THEME_BG, fg=TEXT_COLOR, justify="left", anchor="w").pack(fill="x", padx=10)

        # ── Column 2: Quick Steps ─────────────────────────────────────────────
        tk.Label(right_frame, text="QUICK STEPS", font=FONT_TITLE, 
                 bg=THEME_BG, fg=TEXT_COLOR, anchor="w").pack(fill="x", padx=5)
        tk.Label(right_frame, text=(
            "1. Select type & paste source text.\n"
            "2. Use 🤖 AI Autofill or type manually.\n"
            "3. Verify fields against original docs.\n"
            "4. ⚙️ Generate ➔ 📋 Copy ➔ Paste to Shujaa."
        ), font=FONT_BODY, bg=THEME_BG, fg=TEXT_COLOR, justify="left", anchor="w").pack(fill="x", padx=10)

        # ── Column 3: Reference Panel ─────────────────────────────────────────
        if ref_frame is not None:
            tk.Label(ref_frame, text="REFERENCE PANEL", font=FONT_TITLE, 
                     bg=THEME_BG, fg=TEXT_COLOR, anchor="w").pack(fill="x", padx=5)
            tk.Label(ref_frame, text=(
                "• Keeps source text visible while typing.\n"
                "• Supports Ticket, SMS or Statement data.\n"
                "• Setup Groq Key in ⚙ Settings.\n"
                "• Verify AI output before copying."
            ), font=FONT_BODY, bg=THEME_BG, fg=TEXT_COLOR, justify="left", anchor="w").pack(fill="x", padx=10)

        # Warning Bar (Condensed)
        ttk.Separator(left_frame, orient="horizontal").pack(fill="x", pady=(8, 4))
        tk.Label(left_frame, text="Note: Supports single reconciliation entries only.",
                 font=ui_font_bold, bg=THEME_BG, fg=TEXT_ERROR).pack(anchor="w", padx=5)
        return

    # ══════════════════════════════════════════════════════════════════════════
    # CSV MODES — Beyonic / FlexiPay
    # ══════════════════════════════════════════════════════════════════════════

    # Bottom Warning
    ttk.Separator(left_frame, orient="horizontal").pack(side="bottom", fill="x", pady=(5, 0))
    tk.Label(left_frame, text="IMPORTANT: Always verify transformed data against original statement.",
             font=ui_font_bold, bg=THEME_BG, fg=TEXT_ERROR).pack(side="bottom", fill="x")

    if mode == "FlexiPay":
        tk.Label(left_frame, text="FLEXIPAY USER ACTIONS", font=FONT_TITLE, 
                 bg=THEME_BG, fg=TEXT_COLOR, anchor="w").pack(fill="x", padx=5)
        tk.Label(left_frame, font=FONT_BODY, bg=THEME_BG, fg=TEXT_COLOR, justify="left", anchor="w",
            text=(
                "• Remove non-column header/footer rows.\n"
                "• Convert exponential numbers to standard format.\n"
                "• Ensure file is saved as .csv before upload."
            )).pack(fill="x", padx=10)

        tk.Label(right_frame, text="SYSTEM LOGIC", font=FONT_TITLE, 
                 bg=THEME_BG, fg=TEXT_COLOR, anchor="w").pack(fill="x", padx=5)
        tk.Label(right_frame, font=FONT_BODY, bg=THEME_BG, fg=TEXT_COLOR, justify="left", anchor="w",
            text=(
                "• Filters 'Successful' & 'Merchant Purchase' rows.\n"
                "• Standardizes dates to DD-MM-YYYY HH:MM:SS.\n"
                "• Saves to 'FLEXIPAY_TRANSFORMED' on Desktop."
            )).pack(fill="x", padx=10)

    elif mode == "Beyonic":
        tk.Label(left_frame, text="BEYONIC USER ACTIONS", font=FONT_TITLE, 
                 bg=THEME_BG, fg=TEXT_COLOR, anchor="w").pack(fill="x", padx=5)
        tk.Label(left_frame, font=FONT_BODY, bg=THEME_BG, fg=TEXT_COLOR, justify="left", anchor="w",
            text=(
                "• Upload original CSV directly from portal.\n"
                "• No manual column mapping required.\n"
                "• Check for exponential formatting errors."
            )).pack(fill="x", padx=10)

        tk.Label(right_frame, text="SYSTEM LOGIC", font=FONT_TITLE, 
                 bg=THEME_BG, fg=TEXT_COLOR, anchor="w").pack(fill="x", padx=5)
        tk.Label(right_frame, font=FONT_BODY, bg=THEME_BG, fg=TEXT_COLOR, justify="left", anchor="w",
            text=(
                "• Maps data to 7 standard recon columns.\n"
                "• Auto-fixes Txn IDs using 'Id' column data.\n"
                "• Saves to 'BEYONIC_TRANSFORMED' on Desktop."
            )).pack(fill="x", padx=10)