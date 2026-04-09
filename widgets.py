# widgets.py
"""
Reusable UI widgets used across the application.
"""
import tkinter as tk
from tkinter import ttk

from config import THEME_BG, TEXT_COLOR, FONT_BODY, FONT_BOLD, THEME_INPUT, THEME_BORDER


# ── PreviewTree ────────────────────────────────────────────────────────────────

class PreviewTree:
    """Scrollable Treeview with right-click copy-cell support."""

    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        self.tree  = ttk.Treeview(self.frame, show="headings")

        v_scroll = ttk.Scrollbar(self.frame, orient="vertical",   command=self.tree.yview)
        h_scroll = ttk.Scrollbar(self.frame, orient="horizontal",  command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self._rc_row = None
        self._rc_col = None
        self._rc_menu = tk.Menu(self.frame, tearoff=0)
        self._rc_menu.add_command(label="Copy Cell", command=self._copy_cell)
        self.tree.bind("<Button-3>", self._on_right_click)

    def _on_right_click(self, event):
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            return
        self._rc_row = row_id
        try:
            self._rc_col = int(col_id.replace("#", ""))
        except Exception:
            self._rc_col = None
        self._rc_menu.post(event.x_root, event.y_root)

    def _copy_cell(self):
        if self._rc_row and self._rc_col:
            vals = self.tree.item(self._rc_row).get("values", [])
            val  = vals[self._rc_col - 1] if self._rc_col - 1 < len(vals) else ""
            try:
                self.frame.clipboard_clear()
                self.frame.clipboard_append(str(val))
            except Exception:
                pass

    def pack(self, **kw):
        self.frame.pack(**kw)

    def display(self, df, max_rows: int = 500):
        """Populate the tree from a DataFrame."""
        self.tree.delete(*self.tree.get_children())
        cols = list(df.columns)
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120, anchor="w")
        for _, row in df.head(max_rows).iterrows():
            self.tree.insert("", "end", values=[str(x) for x in row])

    def clear(self):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = []


# ── Styled Card Frame ──────────────────────────────────────────────────────────

class CardFrame(tk.Frame):
    """
    A rounded-looking frame with a subtle border and light card background.
    Used to group related form fields in the JSON Generator.
    """
    def __init__(self, parent, title: str = "", **kwargs):
        super().__init__(parent, bg=THEME_INPUT, relief="flat", bd=0, **kwargs)
        # Draw a 1-px border via a surrounding frame trick
        self.configure(highlightbackground=THEME_BORDER, highlightthickness=1)
        if title:
            tk.Label(
                self, text=title, font=FONT_BOLD,
                bg=THEME_INPUT, fg=TEXT_COLOR, anchor="w",
            ).pack(fill="x", padx=10, pady=(8, 2))
            ttk.Separator(self, orient="horizontal").pack(fill="x", padx=8, pady=(0, 6))


# ── Labelled Entry ─────────────────────────────────────────────────────────────

class LabelledEntry(tk.Frame):
    """
    A compact label + entry widget pair with optional hint text.
    Returns the StringVar for reading the value.
    """
    def __init__(self, parent, label: str, default: str = "", hint: str = "",
                 is_numeric: bool = False, **kwargs):
        super().__init__(parent, bg=THEME_INPUT, **kwargs)

        # Row label
        lbl_text = label + ("  ★" if is_numeric else "")
        tk.Label(
            self, text=lbl_text, font=FONT_BOLD,
            bg=THEME_INPUT, fg=TEXT_COLOR, anchor="w",
        ).pack(fill="x", padx=(0, 4))

        # Entry
        self.var   = tk.StringVar(value=default)
        self.entry = tk.Entry(
            self, textvariable=self.var, font=FONT_BODY,
            bg=THEME_INPUT, fg=TEXT_COLOR, relief="flat",
            highlightbackground=THEME_BORDER,
            highlightcolor="#c9a66b",
            highlightthickness=1, bd=0,
            insertbackground=TEXT_COLOR,
        )
        self.entry.pack(fill="x", ipady=4)

        # Hint
        if hint:
            tk.Label(
                self, text=hint, font=("Poppins", 8),
                bg=THEME_INPUT, fg="#a08060", anchor="w",
            ).pack(fill="x")

    def get(self) -> str:
        return self.var.get()

    def set(self, value: str):
        self.var.set(value)