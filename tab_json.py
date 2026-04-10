#!/usr/bin/env python
# coding: utf-8
# tab_json.py
"""
JSON Generator panel.

3-column layout (left → right):
  Col 1  Payment Form      — largest, flexible
  Col 2  Reference Holder — fixed 320 px
  Col 3  Generated JSON   — fixed 270 px

Buttons packed side="bottom" before text areas so they are always visible.
"""

import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from config import (
    THEME_BG, THEME_ACCENT, THEME_INPUT, THEME_BORDER,
    TEXT_COLOR, TEXT_MUTED,
    FONT_BODY, FONT_BOLD, FONT_TITLE, FONT_SMALL,
    JSON_TYPE_OPTIONS, DROPDOWN_PLACEHOLDER,
)
from json_data      import JSON_FIELDS, JSON_HINTS, build_json_payload
from groq_parser    import groq_extract
from settings_store import load_settings

# ── Palette ───────────────────────────────────────────────────────────────────
FORM_BG      = THEME_BG
FORM_HDR_BG  = "#c9a66b"
FORM_HDR_FG  = "#3a2f24"

REF_BG       = "#fdf3d8"
REF_HDR_BG   = THEME_ACCENT
REF_HDR_FG   = TEXT_COLOR
REF_BORDER   = "#d4b483"

JSON_BG      = "#eaf4f4"
JSON_HDR_BG  = "#3d7a7a"
JSON_HDR_FG  = "#ffffff"
JSON_BORDER  = "#3d7a7a"
JSON_TEXT_BG = "#f4fafa"
JSON_TEXT_FG = "#1a3a3a"
JSON_BTN_BG  = "#3d7a7a"
JSON_BTN_HOV = "#2a5858"

RULE_COLOR   = "#d4b896"

# ── Column widths ─────────────────────────────────────────────────────────────
REF_WIDTH    = 320
JSON_WIDTH   = 270

# ── Form constants ─────────────────────────────────────────────────────────────
FORM_COLS   = 2
ENTRY_WIDTH = 24

_PLACEHOLDER     = "Click  ⚙ Generate  on the payment form to see output."
_REF_PLACEHOLDER = "Paste your source payment text here for reference…"

_AIRTEL_DATE_FIELDS = (
    "creationDate",
    "agentAssignmentDateTime",
    "paymentTransactionDateTime",
)


def _btn(parent, text, cmd, bg, fg="#3a2f24", hover_bg=None,
         font=FONT_SMALL, padx=8, pady=3):
    return tk.Button(
        parent, text=text, command=cmd,
        font=font, bg=bg, fg=fg,
        relief="flat", bd=0, cursor="hand2",
        padx=padx, pady=pady,
        activebackground=hover_bg or bg,
        activeforeground=fg,
    )


class JsonGeneratorPanel(tk.Frame):
    """3-column JSON Generator: Payment Form | Reference Holder | Generated JSON."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=FORM_BG, **kwargs)
        self._json_type_var = tk.StringVar(value=DROPDOWN_PLACEHOLDER)
        self._entry_vars: dict[str, tk.StringVar] = {}
        self._build()
        self._on_type_change()
        self._clear_preview()

    # ══════════════════════════════════════════════════════════════════════════
    # TOP-LEVEL BUILD
    # ══════════════════════════════════════════════════════════════════════════

    def _build(self):
        outer = tk.Frame(self, bg=FORM_BG)
        outer.pack(fill="both", expand=True, padx=2, pady=2)

        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=0)
        outer.columnconfigure(2, weight=0)
        outer.rowconfigure(0, weight=1)

        def _vrule(col):
            tk.Frame(outer, bg=RULE_COLOR, width=2).grid(
                row=0, column=col, sticky="ns"
            )

        # Col 0: Payment Form
        col0 = tk.Frame(outer, bg=FORM_BG)
        col0.grid(row=0, column=0, sticky="nsew")
        self._build_form_column(col0)

        _vrule(1)

        # Col 2: Reference Holder
        col2 = tk.Frame(outer, bg=REF_BG, width=REF_WIDTH)
        col2.grid(row=0, column=2, sticky="nsew")
        col2.pack_propagate(False)
        self._build_reference_column(col2)

        _vrule(3)

        # Col 4: Generated JSON
        col4 = tk.Frame(outer, bg=JSON_BG, width=JSON_WIDTH)
        col4.grid(row=0, column=4, sticky="nsew")
        col4.pack_propagate(False)
        self._build_json_column(col4)

    # ══════════════════════════════════════════════════════════════════════════
    # COL 0 — PAYMENT FORM
    # ══════════════════════════════════════════════════════════════════════════

    def _build_form_column(self, parent: tk.Frame):
        hdr = tk.Frame(parent, bg=FORM_HDR_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📝  Payment Form",
                 font=FONT_BOLD, bg=FORM_HDR_BG, fg=FORM_HDR_FG,
                 padx=10, pady=6).pack(side="left")

        # Type selector row
        sel = tk.Frame(parent, bg=FORM_BG)
        sel.pack(fill="x", padx=8, pady=(6, 3))

        tk.Label(sel, text="Payment Type:", font=FONT_BOLD,
                 bg=FORM_BG, fg=TEXT_COLOR).pack(side="left", padx=(0, 6))

        self._type_box = ttk.Combobox(
            sel, textvariable=self._json_type_var,
            values=JSON_TYPE_OPTIONS, state="readonly",
            width=14, font=FONT_BODY,
        )
        self._type_box.pack(side="left")
        self._type_box.bind("<<ComboboxSelected>>", self._on_type_change)

        _btn(sel, "🗑  Clear All", self._clear_fields,
             bg="#e8d5a3", hover_bg="#d4b483",
             font=FONT_SMALL, padx=8, pady=3
             ).pack(side="left", padx=(8, 0))

        tk.Frame(parent, bg=RULE_COLOR, height=1).pack(fill="x", padx=4)

        # Action bar — bottom (packed before grid so always visible)
        act = tk.Frame(parent, bg=FORM_BG)
        act.pack(side="bottom", fill="x", padx=8, pady=4)
        tk.Frame(parent, bg=RULE_COLOR, height=1).pack(
            side="bottom", fill="x", padx=4
        )

        _btn(act, "⚙️  Generate JSON", self._generate,
             bg=THEME_ACCENT, hover_bg="#b58955",
             font=FONT_BOLD, padx=14, pady=5
             ).pack(side="left", padx=(0, 6))

        _btn(act, "🗑️  Clear Fields", self._clear_fields,
             bg="#e8d5a3", hover_bg="#d4b483",
             font=FONT_BOLD, padx=10, pady=5
             ).pack(side="left")

        # Scrollable field grid
        grid_wrap = tk.Frame(parent, bg=FORM_BG)
        grid_wrap.pack(fill="both", expand=True, padx=4, pady=2)

        self._canvas = tk.Canvas(grid_wrap, bg=FORM_BG, highlightthickness=0)
        sb = ttk.Scrollbar(grid_wrap, orient="vertical",
                           command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._grid_frame = tk.Frame(self._canvas, bg=FORM_BG)
        self._canvas_win = self._canvas.create_window(
            (0, 0), window=self._grid_frame, anchor="nw"
        )
        self._grid_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(
                scrollregion=self._canvas.bbox("all")
            ),
        )
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    # ══════════════════════════════════════════════════════════════════════════
    # COL 2 — REFERENCE HOLDER
    # ══════════════════════════════════════════════════════════════════════════

    def _build_reference_column(self, parent: tk.Frame):
        hdr = tk.Frame(parent, bg=REF_HDR_BG)
        hdr.pack(fill="x")

        # Header title
        tk.Label(
            hdr,
            text="📋  Reference Holder",
            font=FONT_BOLD,
            bg=REF_HDR_BG,
            fg=REF_HDR_FG,
            padx=10,
            pady=6
        ).pack(side="left")

        # Styled description (helper text)
        desc = tk.Label(
            parent,
            text="💡 Provide clear and relevant details to help the AI generate accurate results and minimize incorrect assumptions.",
            font=("Segoe UI", 9, "italic"),
            fg="#6b7280",   # muted gray tone
            bg=parent.cget("bg"),
            wraplength=260,
            justify="left",
            padx=10,
            pady=4
        )
        desc.pack(fill="x")
                    
        # Buttons — bottom
        act = tk.Frame(parent, bg=REF_BG)
        act.pack(side="bottom", fill="x", padx=6, pady=4)
        tk.Frame(parent, bg=REF_BORDER, height=1).pack(
            side="bottom", fill="x", padx=4
        )

        self._autofill_btn = _btn(
            act, "🤖  Autofill form with AI", self._run_ai_autofill,
            bg=THEME_ACCENT, hover_bg="#b58955",
            font=FONT_BOLD, padx=10, pady=4
        )
        self._autofill_btn.pack(side="left", padx=(0, 4))

        _btn(act, "🗑️  Clear", self._clear_reference,
             bg="#e8d5a3", hover_bg="#d4b483",
             font=FONT_BOLD, padx=8, pady=4
             ).pack(side="left")

        # Text area
        txt_wrap = tk.Frame(parent, bg=REF_BG)
        txt_wrap.pack(fill="both", expand=True, padx=4, pady=(4, 0))

        sb_y = ttk.Scrollbar(txt_wrap, orient="vertical")
        self._ref_text = tk.Text(
            txt_wrap,
            font=("Consolas", 9),
            bg=THEME_INPUT, fg=TEXT_COLOR,
            relief="flat", wrap="word",
            highlightbackground=REF_BORDER,
            highlightthickness=1,
            insertbackground=TEXT_COLOR,
            yscrollcommand=sb_y.set,
            undo=True,
        )
        sb_y.config(command=self._ref_text.yview)
        sb_y.pack(side="right", fill="y")
        self._ref_text.pack(fill="both", expand=True)

        self._ref_text.insert("1.0", _REF_PLACEHOLDER)
        self._ref_text.config(fg="#b0997a")
        self._ref_text.bind("<FocusIn>",  self._ref_focus_in)
        self._ref_text.bind("<FocusOut>", self._ref_focus_out)

    # ══════════════════════════════════════════════════════════════════════════
    # COL 4 — GENERATED JSON
    # ══════════════════════════════════════════════════════════════════════════

    def _build_json_column(self, parent: tk.Frame):
        hdr = tk.Frame(parent, bg=JSON_HDR_BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text="{ } JSON Generated",
                 font=FONT_BOLD, bg=JSON_HDR_BG, fg=JSON_HDR_FG,
                 padx=8, pady=6).pack(side="left")
        tk.Label(hdr, text="editable",
                 font=FONT_SMALL, bg=JSON_HDR_BG, fg="#a8d8d8",
                 padx=4).pack(side="right")

        # Buttons — bottom
        act = tk.Frame(parent, bg=JSON_BG)
        act.pack(side="bottom", fill="x", padx=4, pady=4)
        tk.Frame(parent, bg=JSON_BORDER, height=1).pack(
            side="bottom", fill="x", padx=4
        )

        _btn(act, "📋 Copy", self._copy_json,
             bg=JSON_BTN_BG, fg="#ffffff", hover_bg=JSON_BTN_HOV,
             font=FONT_SMALL, padx=7, pady=3
             ).pack(side="left", padx=(0, 3))

        _btn(act, "🗑 Clear", self._clear_preview,
             bg="#d0eaea", fg="#1a3a3a", hover_bg="#b8d8d8",
             font=FONT_SMALL, padx=7, pady=3
             ).pack(side="left")

        # Text area
        txt_wrap = tk.Frame(parent, bg=JSON_BG)
        txt_wrap.pack(fill="both", expand=True, padx=4, pady=(4, 0))

        sb_y = ttk.Scrollbar(txt_wrap, orient="vertical")
        self._preview_text = tk.Text(
            txt_wrap,
            font=("Consolas", 8),
            bg=JSON_TEXT_BG, fg=JSON_TEXT_FG,
            relief="flat", wrap="word",
            highlightbackground=JSON_BORDER,
            highlightthickness=1,
            insertbackground=JSON_HDR_BG,
            selectbackground=JSON_HDR_BG,
            selectforeground="#ffffff",
            yscrollcommand=sb_y.set,
        )
        sb_y.config(command=self._preview_text.yview)
        sb_y.pack(side="right", fill="y")
        self._preview_text.pack(fill="both", expand=True)

    # ══════════════════════════════════════════════════════════════════════════
    # REFERENCE TEXT HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _ref_focus_in(self, _=None):
        if self._ref_text.get("1.0", "end-1c") == _REF_PLACEHOLDER:
            self._ref_text.delete("1.0", "end")
            self._ref_text.config(fg=TEXT_COLOR)

    def _ref_focus_out(self, _=None):
        if not self._ref_text.get("1.0", "end-1c").strip():
            self._ref_text.insert("1.0", _REF_PLACEHOLDER)
            self._ref_text.config(fg="#b0997a")

    def _clear_reference(self):
        self._ref_text.delete("1.0", "end")
        self._ref_text.insert("1.0", _REF_PLACEHOLDER)
        self._ref_text.config(fg="#b0997a")

    # ══════════════════════════════════════════════════════════════════════════
    # FORM FIELD RENDERING
    # ══════════════════════════════════════════════════════════════════════════

    def _on_mousewheel(self, event):
        try:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def _on_type_change(self, event=None):
        json_type = self._json_type_var.get()
        for w in self._grid_frame.winfo_children():
            w.destroy()
        self._entry_vars.clear()
        self._clear_preview()

        if json_type not in JSON_FIELDS:
            tk.Label(
                self._grid_frame,
                text="Select a payment type above to load the form.",
                font=FONT_BODY, bg=FORM_BG, fg=TEXT_MUTED,
            ).grid(row=0, column=0, columnspan=FORM_COLS * 2,
                   pady=30, padx=10, sticky="w")
            return

        fields = JSON_FIELDS[json_type]
        hints  = JSON_HINTS.get(json_type, {})

        for pc in range(FORM_COLS):
            self._grid_frame.columnconfigure(pc * 2,     weight=0, minsize=8)
            self._grid_frame.columnconfigure(pc * 2 + 1, weight=0)
        self._grid_frame.columnconfigure(FORM_COLS * 2, weight=1, minsize=8)

        for idx, (key, label, default, is_numeric) in enumerate(fields):
            rp = idx // FORM_COLS
            cp = idx  % FORM_COLS
            lc = cp * 2 + (1 if cp == 1 else 0)
            ec = lc + 1

            tk.Label(
                self._grid_frame, text=label,
                font=FONT_BOLD, bg=FORM_BG, fg=TEXT_COLOR, anchor="w",
            ).grid(row=rp * 2, column=lc, sticky="w",
                   padx=(8 if cp == 0 else 14, 4), pady=(7, 0))

            var = tk.StringVar(value=default)
            tk.Entry(
                self._grid_frame, textvariable=var,
                font=FONT_BODY, width=ENTRY_WIDTH,
                bg=THEME_INPUT, fg=TEXT_COLOR,
                relief="flat", highlightbackground=THEME_BORDER,
                highlightcolor=THEME_ACCENT, highlightthickness=1, bd=0,
                insertbackground=TEXT_COLOR,
            ).grid(row=rp * 2, column=ec, sticky="w",
                   padx=(0, 8 if cp == 1 else 0), pady=(7, 0))
            self._entry_vars[key] = var

            hint = hints.get(key, "")
            if hint:
                tk.Label(
                    self._grid_frame, text=hint,
                    font=("Poppins", 8), bg=FORM_BG,
                    fg="#a08060", anchor="w",
                ).grid(row=rp * 2 + 1, column=ec,
                       sticky="w", pady=(0, 1))

    # ══════════════════════════════════════════════════════════════════════════
    # AI AUTOFILL
    # ══════════════════════════════════════════════════════════════════════════

    def _run_ai_autofill(self):
        json_type = self._json_type_var.get()
        if json_type not in JSON_FIELDS:
            messagebox.showwarning("Select Type",
                                   "Select a Payment Type first.", parent=self)
            return

        raw = self._ref_text.get("1.0", "end-1c").strip()
        if not raw or raw == _REF_PLACEHOLDER:
            messagebox.showwarning("No Text",
                                   "Paste your source text first.", parent=self)
            return

        cfg     = load_settings()
        api_key = cfg.get("api_key", "").strip()
        if not api_key:
            messagebox.showerror("No API Key",
                                 "API key missing. Visit Settings (⚙).",
                                 parent=self)
            return

        self._autofill_btn.config(state="disabled", text="⏳  AI…")
        self.update_idletasks()

        # Capture raw text in closure so _apply_rules can use it for fallback
        ref_text_snapshot = raw

        def _worker():
            try:
                model  = cfg.get("groq_model", "llama-3.1-8b-instant")
                # Pass raw text — groq_extract forwards it to _apply_rules
                # for fallback phone/transactionId extraction
                values = groq_extract(ref_text_snapshot, json_type, api_key, model)
                self.after(0, lambda: self._on_ai_success(json_type, values))
            except Exception as exc:
                self.after(0, lambda: self._on_ai_error(str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_ai_success(self, json_type: str, values: dict):
        self._autofill_btn.config(state="normal", text="🤖  Autofill form with AI")

        if not values:
            messagebox.showinfo("AI Result",
                                "No values could be extracted.", parent=self)
            return

        filled = []
        for key, var in self._entry_vars.items():
            if key in values and values[key]:
                var.set(values[key])
                filled.append(key)

        lines = [f"Filled {len(filled)} field(s)."]

        if json_type == "Beyonic":
            phone = values.get("PhoneNumber", "")
            if phone:
                lines += ["", f"📱 PhoneNumber → {phone}"]

        elif json_type == "Airtel":
            phone = values.get("customerReferenceNumber", "")
            if phone:
                lines += ["",
                          f"📱 customerReferenceNumber & senderPhoneNumber → {phone}"]
            date_val = values.get("creationDate", "")
            if date_val:
                lines += ["", "📅 All three date fields set to:", f"   {date_val}"]

        elif json_type in ("Bank", "Flexipay"):
            phone = values.get("billRefNumber", "")
            if phone:
                lines += ["", f"📱 billRefNumber & mobile → {phone}"]

        messagebox.showinfo("Autofill Complete", "\n".join(lines), parent=self)

    def _on_ai_error(self, error_msg: str):
        self._autofill_btn.config(state="normal", text="🤖  Autofill form with AI")
        messagebox.showerror("AI Error", error_msg, parent=self)

    # ══════════════════════════════════════════════════════════════════════════
    # GENERATE / COPY / CLEAR
    # ══════════════════════════════════════════════════════════════════════════

    def _generate(self):
        json_type = self._json_type_var.get()
        if json_type not in JSON_FIELDS:
            messagebox.showwarning("Error", "Select type first.", parent=self)
            return
        values = {k: v.get() for k, v in self._entry_vars.items()}
        blanks = [
            lbl for k, lbl, _d, _n in JSON_FIELDS[json_type]
            if not values.get(k, "").strip()
        ]
        if blanks:
            messagebox.showwarning(
                "Missing Fields",
                "Please fill in all required fields.",
                parent=self,
            )
            return
        payload  = build_json_payload(json_type, values)
        json_str = json.dumps(payload, ensure_ascii=False, indent=4)
        self._set_preview(json_str)

    def _copy_json(self):
        content = self._preview_text.get("1.0", "end-1c").strip()
        if not content or content == _PLACEHOLDER:
            messagebox.showinfo("Notice", "Click Generate first.", parent=self)
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        self.update()
        messagebox.showinfo("Copied!", "JSON copied to clipboard.", parent=self)

    def _clear_fields(self):
        json_type = self._json_type_var.get()
        if json_type in JSON_FIELDS:
            for k, _lbl, default, _n in JSON_FIELDS[json_type]:
                if k in self._entry_vars:
                    self._entry_vars[k].set(default)
        self._clear_preview()

    def _set_preview(self, text: str):
        self._preview_text.delete("1.0", "end")
        self._preview_text.insert("end", text)

    def _clear_preview(self):
        self._set_preview(_PLACEHOLDER)