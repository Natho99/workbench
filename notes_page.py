#!/usr/bin/env python
# coding: utf-8
# notes_page.py ── Diary Journal v4 (macOS Optimized)
# ════════════════════════════════════════════════════════════════════════
# Storage : SQLite database in ~/Library/Application Support/4GCapital/
# Layout  : 4-column card grid, newest first, row fills left→right
# Delete  : Inline confirm banner inside the card – NO messagebox
# Save    : Cmd+S (Mac) or Ctrl+S saves the note immediately
# ════════════════════════════════════════════════════════════════════════

import os
import sqlite3
import uuid
import sys
import tkinter as tk
from tkinter import font as tkfont
from datetime import datetime

# ── config fallback ──────────────────────────────────────────────────────
try:
    from config import (
        THEME_BG, THEME_ACCENT, THEME_BORDER,
        TEXT_COLOR, FONT_BOLD, FONT_HEADER, FONT_BODY, FONT_SMALL,
    )
except ImportError:
    THEME_BG     = "#f5ead6"
    THEME_ACCENT = "#b5763a"
    THEME_BORDER = "#ddc89a"
    TEXT_COLOR   = "#3a2518"
    # macOS friendly font fallbacks
    _f = "Helvetica Neue" if sys.platform == "darwin" else "Segoe UI"
    FONT_BOLD    = (_f, 10, "bold")
    FONT_HEADER  = ("Georgia", 15, "bold")
    FONT_BODY    = (_f, 11)
    FONT_SMALL   = (_f, 9)

# ════════════════════════════════════════════════════════════════════════
# DATABASE PATH (macOS Logic)
# ════════════════════════════════════════════════════════════════════════
def _db_path() -> str:
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    
    folder = os.path.join(base, "4GCapital")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "journal.db")

DB_PATH = _db_path()

# ════════════════════════════════════════════════════════════════════════
# PALETTE & FONTS
# ════════════════════════════════════════════════════════════════════════
C = {
    "bg":           "#f5ead6",
    "card_bg":      "#fffaf0",
    "card_border":  "#d4b080",
    "card_star_bg": "#fffbea",
    "card_star_bdr":"#d4a010",
    "editor_bg":    "#fffdf5",
    "status_bg":    "#ecdec8",
    "tag_bg":       "#f0ddb8",
    "search_bg":    "#fff8ee",
    "star_row_bg":  "#fdf3d0",
    "star_row_bdr": "#e8c040",
    "accent":       "#b5763a",
    "accent2":      "#7a4e2a",
    "accent_lt":    "#f0ddb8",
    "header_fg":    "#4a3520",
    "card_text":    "#3a2518",
    "muted":        "#9a8060",
    "rule":         "#d4b896",
    "card_star":    "#d4880a",
    "search_hl":    "#ffe898",
    "danger_btn":   "#b03020",
    "danger_text":  "#8a2010",
    "confirm_bg":   "#fff3e0",
    "confirm_bdr":  "#e8a020",
    "white":        "#fffdf5",
    "green":        "#4a7a2a",
    "green_hov":    "#355a1c",
    "sb_trough":    "#e0ccaa",
    "sb_thumb":     "#b5763a",
}

_m = "Helvetica Neue" if sys.platform == "darwin" else "Segoe UI"
_p = "Optima" if sys.platform == "darwin" else "Palatino Linotype"

F_HDR  = ("Georgia", 15, "bold")
F_H2   = ("Georgia", 12, "bold")
F_H3   = ("Georgia", 11, "bold")
F_DATE = ("Georgia", 10, "italic")
F_ED   = (_p, 11)
F_EDB  = (_p, 11, "bold")
F_SBB  = (_m, 10, "bold")
F_SM   = (_m, 9)
F_BTN  = (_m, 10)
F_CARD = (_p, 10)

COLS = 4 

# ════════════════════════════════════════════════════════════════════════
# DATABASE LAYER
# ════════════════════════════════════════════════════════════════════════

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def db_init():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id       TEXT PRIMARY KEY,
                created  TEXT NOT NULL,
                body     TEXT NOT NULL DEFAULT '',
                starred  INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()

def db_load_all() -> list:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM notes ORDER BY created DESC").fetchall()
    return [dict(r) for r in rows]

def db_upsert(note: dict):
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO notes (id, created, body, starred)
            VALUES (:id, :created, :body, :starred)
            ON CONFLICT(id) DO UPDATE SET
                body    = excluded.body,
                starred = excluded.starred
        """, {
            "id":      note["id"],
            "created": note["created"],
            "body":    note["body"],
            "starred": 1 if note["starred"] else 0,
        })
        conn.commit()

def db_delete(note_id: str):
    with _get_conn() as conn:
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()

def db_save_all(notes: list):
    with _get_conn() as conn:
        conn.execute("DELETE FROM notes")
        conn.executemany("""
            INSERT INTO notes (id, created, body, starred)
            VALUES (:id, :created, :body, :starred)
        """, [
            {
                "id":      n["id"],
                "created": n["created"],
                "body":    n["body"],
                "starred": 1 if n["starred"] else 0,
            }
            for n in notes
        ])
        conn.commit()

# ════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════

def _new_note(body: str = "") -> dict:
    return {
        "id":      str(uuid.uuid4()),
        "created": datetime.now().isoformat(timespec="seconds"),
        "body":    body,
        "starred": False,
    }

def _fmt_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y  ·  %I:%M %p")
    except Exception:
        return iso

def _flat_btn(parent, text, cmd, bg=None, fg=None, hover_bg=None, font=F_BTN, padx=12, pady=6):
    bg       = bg       or C["accent"]
    fg       = fg       or C["white"]
    hover_bg = hover_bg or C["accent2"]
    b = tk.Button(
        parent, text=text, command=cmd,
        font=font, bg=bg, fg=fg,
        relief="flat", cursor="hand2",
        padx=padx, pady=pady,
        activebackground=hover_bg,
        activeforeground=fg,
        bd=0
    )
    return b

def _scrollbar(parent, cmd):
    return tk.Scrollbar(
        parent, orient="vertical", command=cmd,
        bg=C["sb_trough"], troughcolor=C["sb_trough"],
        width=14
    )

# ════════════════════════════════════════════════════════════════════════
# NOTE CARD
# ════════════════════════════════════════════════════════════════════════

class NoteCard(tk.Frame):
    def __init__(self, parent, note: dict, serial: int,
                 on_open, on_star, on_delete, on_copy, **kw):
        is_starred = bool(note.get("starred"))
        card_bg  = C["card_star_bg"]  if is_starred else C["card_bg"]
        card_bdr = C["card_star_bdr"] if is_starred else C["card_border"]

        super().__init__(
            parent,
            bg=card_bg,
            highlightbackground=card_bdr,
            highlightthickness=1,
            cursor="hand2",
            **kw
        )
        self._note      = note
        self._serial    = serial
        self._on_open   = on_open
        self._on_star   = on_star
        self._on_delete = on_delete
        self._on_copy   = on_copy
        self._card_bg   = card_bg
        self._confirm_visible = False

        self._build()
        self._bind_all()

    def _build(self):
        bg = self._card_bg
        n  = self._note
        top = tk.Frame(self, bg=bg)
        top.pack(fill="x", padx=8, pady=(7, 3))

        tk.Label(top, text=f"#{self._serial}", font=F_SBB, bg=bg, fg=C["accent"]).pack(side="left")

        self._star_lbl = tk.Label(
            top,
            text="★" if n["starred"] else "☆",
            font=("Helvetica", 14),
            bg=bg,
            fg=C["card_star"] if n["starred"] else C["muted"],
            cursor="hand2"
        )
        self._star_lbl.pack(side="right")

        tk.Label(self, text=_fmt_date(n["created"]), font=F_DATE, bg=bg, fg=C["muted"]).pack(fill="x", padx=8)
        tk.Frame(self, bg=C["rule"], height=1).pack(fill="x", padx=6, pady=2)

        lines   = n["body"].strip().split("\n")
        preview = "\n".join(lines[:4]) + ("\n…" if len(lines) > 4 else "")
        self._body_lbl = tk.Label(
            self, text=preview,
            font=F_CARD, bg=bg, fg=C["card_text"],
            anchor="nw", justify="left", wraplength=170
        )
        self._body_lbl.pack(fill="both", expand=True, padx=8, pady=4)

        self._confirm_frame = tk.Frame(
            self, bg=C["confirm_bg"],
            highlightbackground=C["confirm_bdr"],
            highlightthickness=1
        )
        tk.Label(
            self._confirm_frame,
            text="Delete?", font=F_SM,
            bg=C["confirm_bg"], fg=C["danger_text"],
            padx=6, pady=3
        ).pack(side="left")
        _flat_btn(
            self._confirm_frame, "Yes",
            self._do_delete,
            bg=C["danger_btn"], hover_bg="#8a2010",
            padx=7, pady=2, font=F_SM
        ).pack(side="right", padx=3, pady=3)
        _flat_btn(
            self._confirm_frame, "No",
            self._hide_confirm,
            bg=C["status_bg"], fg=C["muted"], hover_bg=C["rule"],
            padx=7, pady=2, font=F_SM
        ).pack(side="right", pady=3)

        foot = tk.Frame(self, bg=C["tag_bg"])
        foot.pack(fill="x")
        wc = len(n["body"].split())
        tk.Label(foot, text=f"{wc}w", font=F_SM, bg=C["tag_bg"], fg=C["muted"], padx=5, pady=2).pack(side="left")
        tk.Label(foot, text="open →", font=F_SM, bg=C["tag_bg"], fg=C["accent"], padx=5).pack(side="right")

    def _bind_all(self):
        for w in [self, self._body_lbl]:
            w.bind("<Button-1>", lambda e: self._on_open(self._note))
            # Mac Right Click Handling (Button-2 and Control+Click)
            w.bind("<Button-2>", self._ctx)
            w.bind("<Button-3>", self._ctx)
            w.bind("<Control-Button-1>", self._ctx)
            w.bind("<Enter>", lambda e: self._hover(True))
            w.bind("<Leave>", lambda e: self._hover(False))

    def _hover(self, on):
        if self._confirm_visible: return
        col = C["search_hl"] if on else self._card_bg
        self.config(bg=col)
        try: self._body_lbl.config(bg=col)
        except Exception: pass

    def _star_clicked(self, event):
        self._on_star(self._note)
        return "break"

    def _ctx(self, event):
        m = tk.Menu(self, tearoff=0, bg=C["card_bg"], fg=C["accent2"],
                    activebackground=C["accent"], activeforeground=C["white"],
                    font=F_BTN, relief="flat", bd=0)
        m.add_command(label="✏ Edit", command=lambda: self._on_open(self._note))
        m.add_command(label="⎘ Copy", command=lambda: self._on_copy(self._note))
        m.add_separator()
        m.add_command(label="🗑 Delete", foreground=C["danger_btn"], command=self._show_confirm)
        m.tk_popup(event.x_root, event.y_root)

    def _show_confirm(self):
        self._confirm_visible = True
        self._confirm_frame.pack(fill="x", padx=5, pady=(0, 4))

    def _hide_confirm(self):
        self._confirm_visible = False
        self._confirm_frame.pack_forget()

    def _do_delete(self):
        self._confirm_visible = False
        self._on_delete(self._note)


# ════════════════════════════════════════════════════════════════════════
# EDITOR PANE
# ════════════════════════════════════════════════════════════════════════

class _EditorPane(tk.Frame):
    def __init__(self, parent, note: dict, on_save, on_close):
        super().__init__(parent, bg=C["bg"])
        self._note    = dict(note)
        self._on_save = on_save
        self._on_close = on_close
        self._plain   = tkfont.Font(family=_p, size=11)
        self._bold    = tkfont.Font(family=_p, size=11, weight="bold")
        self._build()

    def _build(self):
        tb = tk.Frame(self, bg=C["status_bg"])
        tb.pack(fill="x")
        tk.Label(tb, text=_fmt_date(self._note["created"]), font=F_DATE, bg=C["status_bg"], fg=C["muted"], padx=12, pady=7).pack(side="left")

        _flat_btn(tb, "B Bold", self._toggle_bold, bg=C["status_bg"], fg=C["accent2"], hover_bg=C["accent_lt"], padx=10, pady=7).pack(side="left")
        tk.Frame(tb, bg=C["rule"], width=1).pack(side="left", fill="y", pady=4)

        _flat_btn(tb, "⎘ Copy", self._copy_text, bg=C["status_bg"], fg=C["accent2"], hover_bg=C["accent_lt"], padx=10, pady=7).pack(side="left")
        tk.Frame(tb, bg=C["rule"], width=1).pack(side="left", fill="y", pady=4)

        self._star_var = tk.BooleanVar(value=bool(self._note.get("starred")))
        self._star_cb  = tk.Checkbutton(tb, text=("★ Starred" if self._star_var.get() else "☆ Star"), variable=self._star_var,
                                       font=F_BTN, bg=C["status_bg"], fg=C["card_star"], selectcolor=C["accent_lt"], relief="flat", cursor="hand2",
                                       activebackground=C["status_bg"], command=self._refresh_star)
        self._star_cb.pack(side="left", padx=6)

        _flat_btn(tb, "✕ Close", self._on_close, bg=C["status_bg"], fg=C["muted"], hover_bg=C["rule"], padx=10, pady=7).pack(side="right", padx=8)

        paper = tk.Frame(self, bg=C["editor_bg"], highlightbackground=C["rule"], highlightthickness=1)
        paper.pack(fill="both", expand=True, padx=14, pady=10)
        tk.Frame(paper, bg="#c87060", width=2).pack(side="left", fill="y")

        ef = tk.Frame(paper, bg=C["editor_bg"])
        ef.pack(side="left", fill="both", expand=True)
        vs = _scrollbar(ef, self.text_yview if hasattr(self, 'text_yview') else None)
        vs.pack(side="right", fill="y")

        self.text_area = tk.Text(ef, font=self._plain, bg=C["editor_bg"], fg=C["card_text"], relief="flat", padx=14, pady=14,
                                 undo=True, wrap="word", insertbackground=C["accent"], selectbackground=C["tag_bg"],
                                 selectforeground=C["card_text"], spacing1=3, spacing3=3, yscrollcommand=vs.set)
        self.text_area.pack(fill="both", expand=True)
        vs.config(command=self.text_area.yview)

        self.text_area.tag_config("bold", font=self._bold)
        self.text_area.insert("1.0", self._note.get("body", ""))
        self.text_area.focus_set()
        
        # Mac & Win Keyboard Bindings
        self.text_area.bind("<Command-b>", lambda e: self._toggle_bold())
        self.text_area.bind("<Control-b>", lambda e: self._toggle_bold())
        self.text_area.bind("<Command-s>", lambda e: self._do_save())
        self.text_area.bind("<Control-s>", lambda e: self._do_save())

        btm = tk.Frame(self, bg=C["bg"])
        btm.pack(fill="x", padx=14, pady=(0, 12))
        _flat_btn(btm, "💾 Save Entry", self._do_save, bg=C["accent"], hover_bg=C["accent2"]).pack(side="right", padx=(6, 0))
        _flat_btn(btm, "✕ Cancel", self._on_close, bg=C["status_bg"], fg=C["muted"]).pack(side="right")

    def _refresh_star(self):
        self._star_cb.config(text="★ Starred" if self._star_var.get() else "☆ Star")

    def _toggle_bold(self):
        try:
            s, e = self.text_area.index(tk.SEL_FIRST), self.text_area.index(tk.SEL_LAST)
        except tk.TclError:
            s, e = self.text_area.index("insert wordstart"), self.text_area.index("insert wordend")
        
        if "bold" in self.text_area.tag_names(s): self.text_area.tag_remove("bold", s, e)
        else: self.text_area.tag_add("bold", s, e)
        return "break"

    def _copy_text(self):
        try: txt = self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError: txt = self.text_area.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(txt)

    def _do_save(self):
        body = self.text_area.get("1.0", "end-1c").strip()
        if not body: return
        self._note["body"] = body
        self._note["starred"] = bool(self._star_var.get())
        self._on_save(self._note)
        return "break"


# ════════════════════════════════════════════════════════════════════════
# MAIN PANEL
# ════════════════════════════════════════════════════════════════════════

class NotesPanel(tk.Frame):
    def __init__(self, parent: tk.Misc, **kwargs):
        super().__init__(parent, bg=C["bg"], **kwargs)
        db_init()
        self._notes = []
        self._filter = "all"
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh_grid())
        self._active_editor = None
        self._build_skeleton()

    def show(self):
        self._load()

    def autosave(self):
        try: db_save_all(self._notes)
        except Exception: pass

    def _load(self):
        try:
            rows = db_load_all()
            for r in rows: r["starred"] = bool(r.get("starred", 0))
            self._notes = rows
            self._set_status(f"Loaded {len(self._notes)} note(s)  ✓")
        except Exception as exc:
            self._notes = []
            self._set_status(f"Load error: {exc}")

        if not self._notes:
            welcome = _new_note("Welcome to your Daily Work Journal!\n\nRight-click any card to edit.\nCmd+S to Save.")
            db_upsert(welcome); self._notes = [welcome]
        self._refresh_all()

    def _set_status(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        try: self._status_lbl.config(text=f"{msg}  ·  {ts}")
        except Exception: pass

    def _visible_notes(self) -> list:
        q = self._search_var.get().strip().lower()
        out = []
        for n in self._notes:
            if self._filter == "starred" and not n["starred"]: continue
            if self._filter == "unstarred" and n["starred"]: continue
            if q and q not in n["body"].lower(): continue
            out.append(n)
        return out

    def _refresh_all(self):
        self._refresh_grid()

    def _refresh_grid(self):
        if self._active_editor: return
        for w in self._content_pane.winfo_children(): w.destroy()

        visible = self._visible_notes()
        total = len(self._notes)

        if not visible:
            tk.Label(self._content_pane, text="No entries found.", font=F_H2, bg=C["bg"], fg=C["muted"]).pack(pady=80)
            return

        gc = tk.Canvas(self._content_pane, bg=C["bg"], highlightthickness=0)
        gvs = _scrollbar(self._content_pane, gc.yview)
        gc.configure(yscrollcommand=gvs.set)
        gvs.pack(side="right", fill="y")
        gc.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)

        inner = tk.Frame(gc, bg=C["bg"])
        win = gc.create_window((0, 0), window=inner, anchor="nw")

        starred = [n for n in visible if n["starred"]]
        unstarred = [n for n in visible if not n["starred"]]
        current_row = 0

        if starred:
            sh = tk.Frame(inner, bg=C["star_row_bg"], highlightbackground=C["star_row_bdr"], highlightthickness=1)
            sh.grid(row=current_row, column=0, columnspan=COLS, sticky="ew", padx=6, pady=(6, 2))
            tk.Label(sh, text="  ★  Starred Notes", font=F_H3, bg=C["star_row_bg"], fg=C["card_star"]).pack(side="left", pady=5)
            current_row += 1
            for i, n in enumerate(starred):
                NoteCard(inner, n, total - self._notes.index(n), self._open_note, self._toggle_star, self._delete_note, self._copy_note).grid(row=current_row + (i // COLS), column=i % COLS, padx=6, pady=6, sticky="nsew")
            current_row += (len(starred) + COLS - 1) // COLS
            tk.Frame(inner, bg=C["rule"], height=2).grid(row=current_row, column=0, columnspan=COLS, sticky="ew", padx=6, pady=4)
            current_row += 1

        if unstarred:
            for i, n in enumerate(unstarred):
                NoteCard(inner, n, total - self._notes.index(n), self._open_note, self._toggle_star, self._delete_note, self._copy_note).grid(row=current_row + (i // COLS), column=i % COLS, padx=6, pady=6, sticky="nsew")

        for c in range(COLS): inner.columnconfigure(c, weight=1, uniform="col")
        inner.bind("<Configure>", lambda e: gc.configure(scrollregion=gc.bbox("all")))
        gc.bind("<Configure>", lambda e: gc.itemconfig(win, width=e.width))

    def _open_note(self, note: dict):
        for w in self._content_pane.winfo_children(): w.destroy()
        self._active_editor = _EditorPane(self._content_pane, note, self._editor_saved, self._editor_closed)
        self._active_editor.pack(fill="both", expand=True)

    def _editor_saved(self, updated: dict):
        idx = next((i for i, n in enumerate(self._notes) if n["id"] == updated["id"]), None)
        if idx is not None: self._notes[idx] = updated
        else: self._notes.insert(0, updated)
        self._notes.sort(key=lambda n: n["created"], reverse=True)
        db_upsert(updated)
        self._active_editor = None
        self._refresh_all()

    def _editor_closed(self):
        self._active_editor = None
        self._refresh_all()

    def _toggle_star(self, note: dict):
        for n in self._notes:
            if n["id"] == note["id"]:
                n["starred"] = not n["starred"]
                db_upsert(n); break
        self._refresh_all()

    def _delete_note(self, note: dict):
        db_delete(note["id"])
        self._notes = [n for n in self._notes if n["id"] != note["id"]]
        self._refresh_all()

    def _copy_note(self, note: dict):
        self.clipboard_clear(); self.clipboard_append(note["body"])
        self._set_status("Copied to clipboard ✓")

    def _set_filter(self, key: str):
        self._filter = key
        for k, btn in self._tab_btns.items():
            btn.config(bg=C["accent"] if k == key else C["status_bg"], fg=C["white"] if k == key else C["accent2"])
        self._refresh_grid()

    def _build_skeleton(self):
        hdr = tk.Frame(self, bg=C["status_bg"]); hdr.pack(fill="x")
        tc = tk.Frame(hdr, bg=C["status_bg"]); tc.pack(side="left", padx=20, pady=12)
        tk.Label(tc, text="📓  Daily Work Journal", font=F_HDR, bg=C["status_bg"], fg=C["header_fg"]).pack(anchor="w")
        tk.Label(tc, text="Thinking space and progress tracking", font=(_m, 10, "italic"), bg=C["status_bg"], fg="#8A7F73").pack(anchor="w")
        
        _flat_btn(hdr, "✚ New Entry", lambda: self._open_note(_new_note()), bg=C["green"], hover_bg=C["green_hov"]).pack(side="right", padx=20)

        tb = tk.Frame(self, bg=C["status_bg"]); tb.pack(fill="x")
        self._tab_btns = {}
        for lbl, k in [("📋 All", "all"), ("★ Starred", "starred")]:
            btn = _flat_btn(tb, lbl, lambda key=k: self._set_filter(key), bg=C["accent"] if k == self._filter else C["status_bg"])
            btn.pack(side="left"); self._tab_btns[k] = btn

        sw = tk.Frame(tb, bg=C["status_bg"]); sw.pack(side="right", padx=14)
        tk.Entry(sw, textvariable=self._search_var, font=F_ED, bg=C["search_bg"], width=20, relief="flat").pack(side="left", ipady=4)

        self._content_pane = tk.Frame(self, bg=C["bg"]); self._content_pane.pack(fill="both", expand=True)

        foot = tk.Frame(self, bg=C["status_bg"]); foot.pack(fill="x", side="bottom")
        tk.Label(foot, text=f"DB: {DB_PATH} · Cmd+S = Save", font=F_SM, bg=C["status_bg"], fg=C["muted"]).pack(pady=5)