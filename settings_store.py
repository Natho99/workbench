import os
import sqlite3
import sys

# ── DB path (macOS Optimized) ──────────────────────────────────────────────
def _db_path() -> str:
    """
    Returns the standard path for local data storage.
    macOS: ~/Library/Application Support/4GCapital/journal.db
    Windows: %APPDATA%/4GCapital/journal.db
    """
    if sys.platform == "darwin":
        # Standard Mac location for application data
        base = os.path.expanduser("~/Library/Application Support")
    else:
        # Standard Windows location
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    
    folder = os.path.join(base, "4GCapital")
    
    # Ensure the directory exists
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception as e:
        # Fallback to current directory if permissions fail in the system path
        print(f"Warning: Could not create directory at {folder}. Error: {e}")
        folder = "."
        
    return os.path.join(folder, "journal.db")

DB_PATH = _db_path()

# ── Defaults ─────────────────────────────────────────────────────────────
DEFAULTS: dict = {
    "parse_mode": "ai",
    "api_key": "",
    "groq_model": "llama-3.1-8b-instant",
}

# ── Internal state ───────────────────────────────────────────────────────
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
    """Load settings from SQLite without overwriting defaults."""
    _init_db()

    cfg = dict(DEFAULTS)

    try:
        with _get_conn() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()

        for row in rows:
            cfg[row["key"]] = row["value"]

    except Exception:
        # If DB is empty or inaccessible, return DEFAULTS
        pass

    return cfg


def save_settings(cfg: dict) -> None:
    """Save settings using the SQLite UPSERT (Insert or Update) method."""
    _init_db()

    try:
        with _get_conn() as conn:
            # Use SQLite UPSERT logic (ON CONFLICT) to update existing keys
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
        raise IOError(f"Could not save settings to {DB_PATH}: {exc}") from exc

if __name__ == "__main__":
    # Quick debug to verify pathing
    print(f"Database Path: {DB_PATH}")
    test_cfg = load_settings()
    print(f"Loaded Settings: {test_cfg}")