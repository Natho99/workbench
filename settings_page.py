# settings_page.py
"""
Settings panel — rendered INSIDE the main window as a full-screen overlay
frame that slides over the notebook area.  No separate window is opened.

Settings are persisted to SQLite:
    %APPDATA%\\4GCapital\\journal.db  →  table: settings

Sections
--------
  1. Groq AI — API key, model selector
"""

import tkinter as tk
from tkinter import ttk, messagebox

from config import (
    THEME_BG, THEME_ACCENT, THEME_INPUT, THEME_BORDER,
    TEXT_COLOR, FONT_BODY, FONT_BOLD, FONT_HEADER, FONT_SMALL,
)
from settings_store import load_settings, save_settings, DB_PATH

# ── Colours ───────────────────────────────────────────────────────────────
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
    Full-size settings panel packed inside the main window.
    Call .show() to bring it forward.
    """

    def __init__(self, parent: tk.Misc, **kwargs):
        super().__init__(parent, bg=THEME_BG, **kwargs)
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
            relief="flat", bd=0, cursor="hand2",
            padx=14, pady=10,
            command=self.hide,
        ).pack(side="right", padx=10)

        # Main content
        content = tk.Frame(self, bg=THEME_BG)
        content.pack(fill="both", expand=True, padx=14, pady=10)
        self._build_ai_section(content)

        # Footer buttons
        footer = tk.Frame(self, bg=THEME_BG)
        footer.pack(fill="x", padx=14, pady=(0, 20))

        tk.Button(
            footer, text="💾  Save API Settings",
            font=FONT_BOLD,
            bg=THEME_ACCENT, fg=TEXT_COLOR,
            activebackground="#b58955",
            relief="flat", bd=0, cursor="hand2",
            padx=20, pady=8,
            command=self._save_all,
        ).pack(side="left", padx=(0, 12))

        tk.Button(
            footer, text="✖  Close",
            font=FONT_BOLD,
            bg="#e8d5a3", fg=TEXT_COLOR,
            activebackground=CARD_BORDER,
            relief="flat", bd=0, cursor="hand2",
            padx=14, pady=8,
            command=self.hide,
        ).pack(side="left")

    # ── Groq AI section ───────────────────────────────────────────────────

    def _build_ai_section(self, parent):
        # Card
        card = tk.Frame(
            parent, bg=CARD_BG,
            highlightbackground=CARD_BORDER, highlightthickness=1
        )
        card.pack(fill="x", padx=16, pady=16)

        ch = tk.Frame(card, bg=HDR_BG)
        ch.pack(fill="x")
        tk.Label(
            ch, text="Groq API Configuration",
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
            font=("Consolas", 10), width=52,
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
            body, text="👁  Show / Hide",
            font=FONT_SMALL, bg=CARD_BG, fg=TEXT_COLOR,
            relief="flat", bd=0, cursor="hand2",
            command=self._toggle_key,
        ).grid(row=0, column=2, padx=(10, 0), sticky="w")

        # Model row
        tk.Label(
            body, text="Model:", font=FONT_BOLD,
            bg=CARD_BG, fg=TEXT_COLOR, width=12, anchor="w"
        ).grid(row=1, column=0, sticky="w", pady=8)

        ttk.Combobox(
            body, textvariable=self._model_var,
            values=GROQ_MODELS, state="readonly", width=40, font=FONT_BODY,
        ).grid(row=1, column=1, sticky="w", pady=8)

        # Help link
        tk.Label(
            body,
            text="Get a free API key at  console.groq.com  — no credit card needed.",
            font=FONT_SMALL, bg=CARD_BG, fg="#7a5c2e",
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))

        # Info box — updated to mention SQLite, not JSON
        info = tk.Frame(
            parent, bg=INFO_BG,
            highlightbackground=INFO_BORDER, highlightthickness=1
        )
        info.pack(fill="x", padx=16)

        tk.Label(
            info,
            text=(
                f"ℹ  Your API key is stored securely in the local database:\n"
                f"   {DB_PATH}\n"
                f"   It is only sent to api.groq.com to power the Autofill with AI feature."
            ),
            font=FONT_SMALL, bg=INFO_BG, fg=TEXT_COLOR,
            justify="left", anchor="w", padx=12,
        ).pack(fill="x", pady=8)

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
                "Saved",
                "API settings saved successfully to the local database.",
                parent=self,
            )
        except IOError as exc:
            messagebox.showerror("Save Failed", str(exc), parent=self)