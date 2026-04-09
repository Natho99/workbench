import os
import sqlite3

# ── DB path ──────────────────────────────────────────────────────────────
def _db_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, "4GCapital")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "journal.db")

DB_PATH = _db_path()

# ── Defaults ─────────────────────────────────────────────────────────────
DEFAULTS: dict = {
    "parse_mode": "ai",
    "api_key": "",
    "groq_model": "llama-3.1-8b-instant",
}

# ── Internal state (prevents re-creating table repeatedly) ───────────────
_db_initialized = False

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db():
    """Initialize DB only once per app lifecycle."""
    global _db_initialized
    if _db_initialized:
        return

    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.commit()

    _db_initialized = True

# ── Public API ───────────────────────────────────────────────────────────

def load_settings() -> dict:
    """Load settings without overwriting saved values."""
    _init_db()

    cfg = dict(DEFAULTS)

    try:
        with _get_conn() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()

        for row in rows:
            cfg[row["key"]] = row["value"]

    except Exception:
        pass

    return cfg


def save_settings(cfg: dict) -> None:
    """Save only provided values."""
    _init_db()

    try:
        with _get_conn() as conn:
            conn.executemany(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                [(str(k), str(v)) for k, v in cfg.items()]
            )
            conn.commit()

    except Exception as exc:
        raise IOError(f"Could not save settings: {exc}") from exc