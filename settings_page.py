#!/usr/bin/env python
# coding: utf-8
# settings_page.py ── macOS Optimized Settings Panel
# ════════════════════════════════════════════════════════════════════════
# Settings are persisted to SQLite via settings_store.py
# ════════════════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk, messagebox
import sys

# Ensure these imports exist in your project structure
from config import (
    THEME_BG, THEME_ACCENT, THEME_INPUT, THEME_BORDER,
    TEXT_COLOR, FONT_BODY, FONT_BOLD, FONT_HEADER, FONT_SMALL,
)
from settings_store import load_settings, save_settings, DB_PATH

# ── Colors ───────────────────────────────────────────────────────────────
CARD_BG     = "#fdf6e3"
CARD_BORDER = "#c9a66b"
HDR_BG      = "#c9a66b"
HDR_FG      = "#3a2f24"
INFO_BG     = "#fff8e7"
INFO_BORDER = "#d4b483"

GROQ_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "llama3-8b-8192",
    "llama3-70b-8192",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]

class SettingsPanel(tk.Frame):
    """
    Full-size settings panel packed inside the main window as an overlay.
    """

    def __init__(self, parent: tk.Misc, **kwargs):
        super().__init__(parent, bg=THEME_BG, **kwargs)
        
        # Mac Font Overrides
        self.mono_font = ("Menlo", 11) if sys.platform == "darwin" else ("Consolas", 10)
        self.ui_font = "Helvetica Neue" if sys.platform == "darwin" else "Segoe UI"
        
        self._cfg          = load_settings()
        self._api_key_var  = tk.StringVar(value=self._cfg.get("api_key", ""))
        self._model_var    = tk.StringVar(
            value=self._cfg.get("groq_model", "llama-3.1-8b-instant")
        )
        self._key_visible  = False
        self._build()

    # ── Public interface ──────────────────────────────────────────────────

    def show(self):
        """Refresh values from the DB whenever the panel is displayed."""
        self._cfg = load_settings()
        self._api_key_var.set(self._cfg.get("api_key", ""))
        self._model_var.set(
            self._cfg.get("groq_model", "llama-3.1-8b-instant")
        )

    def hide(self):
        """Ask the parent app to close the settings panel."""
        w = self.master
        while w is not None:
            if hasattr(w, "_toggle_settings"):
                w._toggle_settings()
                return
            w = getattr(w, "master", None)

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self):
        # Header bar
        hdr = tk.Frame(self, bg=HDR_BG)
        hdr.pack(fill="x")

        tk.Label(
            hdr, text="⚙  Settings",
            font=FONT_HEADER, bg=HDR_BG, fg=HDR_FG,
            padx=16, pady=10
        ).pack(side="left")

        tk.Button(
            hdr, text="✖  Close Settings",
            font=FONT_BOLD, bg=HDR_BG, fg=HDR_FG,
            activebackground="#b58955",
            highlightbackground=HDR_BG,
            relief="flat", bd=0, cursor="hand2",
            padx=14, pady=10,
            command=self.hide,
        ).pack(side="right", padx=10)

        # Main content area
        canvas = tk.Canvas(self, bg=THEME_BG, highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=THEME_BG)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._build_ai_section(scrollable_frame)
        self._build_storage_info(scrollable_frame)

        # Footer buttons
        footer = tk.Frame(self, bg=THEME_BG)
        footer.pack(fill="x", side="bottom", padx=14, pady=20)

        tk.Button(
            footer, text="💾  Save API Settings",
            font=FONT_BOLD,
            bg=THEME_ACCENT, fg=TEXT_COLOR,
            highlightbackground=THEME_BG,
            activebackground="#b58955",
            relief="flat", bd=0, cursor="hand2",
            padx=20, pady=8,
            command=self._save_all,
        ).pack(side="left", padx=(0, 12))

        tk.Button(
            footer, text="✖  Cancel",
            font=FONT_BOLD,
            bg="#e8d5a3", fg=TEXT_COLOR,
            highlightbackground=THEME_BG,
            activebackground=CARD_BORDER,
            relief="flat", bd=0, cursor="hand2",
            padx=14, pady=8,
            command=self.hide,
        ).pack(side="left")

    # ── Groq AI section ───────────────────────────────────────────────────

    def _build_ai_section(self, parent):
        card = tk.Frame(
            parent, bg=CARD_BG,
            highlightbackground=CARD_BORDER, highlightthickness=1
        )
        card.pack(fill="x", padx=30, pady=20)

        ch = tk.Frame(card, bg=HDR_BG)
        ch.pack(fill="x")
        tk.Label(
            ch, text="Groq AI Configuration",
            font=FONT_BOLD, bg=HDR_BG, fg=HDR_FG,
            padx=12, pady=7
        ).pack(side="left")

        body = tk.Frame(card, bg=CARD_BG)
        body.pack(fill="x", padx=16, pady=12)

        # API Key row
        tk.Label(
            body, text="API Key:", font=FONT_BOLD,
            bg=CARD_BG, fg=TEXT_COLOR, width=12, anchor="w"
        ).grid(row=0, column=0, sticky="w", pady=8)

        self._api_entry = tk.Entry(
            body, textvariable=self._api_key_var,
            font=self.mono_font, width=40,
            bg=THEME_INPUT, fg=TEXT_COLOR,
            relief="flat",
            highlightbackground=THEME_BORDER,
            highlightcolor=THEME_ACCENT,
            highlightthickness=1, bd=0,
            insertbackground=TEXT_COLOR,
            show="*",
        )
        self._api_entry.grid(row=0, column=1, sticky="w", pady=8)

        tk.Button(
            body, text="👁 Show/Hide",
            font=FONT_SMALL, bg=CARD_BG, fg=TEXT_COLOR,
            highlightbackground=CARD_BG,
            relief="flat", bd=0, cursor="hand2",
            command=self._toggle_key,
        ).grid(row=0, column=2, padx=(10, 0), sticky="w")

        # Model Selection row
        tk.Label(
            body, text="Model:", font=FONT_BOLD,
            bg=CARD_BG, fg=TEXT_COLOR, width=12, anchor="w"
        ).grid(row=1, column=0, sticky="w", pady=8)

        model_cb = ttk.Combobox(
            body, textvariable=self._model_var,
            values=GROQ_MODELS, state="readonly", width=38, font=FONT_BODY,
        )
        model_cb.grid(row=1, column=1, sticky="w", pady=8)

        # Help link/Info
        tk.Label(
            body,
            text="Get a free API key at console.groq.com (High-speed Llama 3).",
            font=FONT_SMALL, bg=CARD_BG, fg="#7a5c2e",
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))

    def _build_storage_info(self, parent):
        info = tk.Frame(
            parent, bg=INFO_BG,
            highlightbackground=INFO_BORDER, highlightthickness=1
        )
        info.pack(fill="x", padx=30, pady=(0, 20))

        # Mac paths are long, so we use wraplength
        tk.Label(
            info,
            text=(
                f"ℹ  Security & Storage:\n"
                f"   Your API key is stored locally in your SQLite database:\n"
                f"   {DB_PATH}\n\n"
                f"   Keys are only used to communicate with Groq Cloud services."
            ),
            font=FONT_SMALL, bg=INFO_BG, fg=TEXT_COLOR,
            justify="left", anchor="w", padx=12, pady=10,
            wraplength=800
        ).pack(fill="x")

    # ── Helpers ───────────────────────────────────────────────────────────

    def _toggle_key(self):
        self._key_visible = not self._key_visible
        self._api_entry.config(show="" if self._key_visible else "*")

    def _save_all(self):
        self._cfg["api_key"]    = self._api_key_var.get().strip()
        self._cfg["groq_model"] = self._model_var.get()
        self._cfg["parse_mode"] = "ai"
        try:
            save_settings(self._cfg)
            messagebox.showinfo(
                "Settings Saved",
                "API Configuration has been updated in the local database.",
                parent=self,
            )
        except Exception as exc:
            messagebox.showerror("Error", f"Could not save settings: {str(exc)}", parent=self)