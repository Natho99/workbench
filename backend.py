#!/usr/bin/env python
# coding: utf-8
# backend.py ── Core Logic & Mac File System Integration
# ════════════════════════════════════════════════════════════════════════

import os
import re
import csv
import sys
import pandas as pd
from datetime import datetime

from config import (
    MAX_ROWS, BEYONIC_DIR, FLEXIPAY_DIR, CLEANED_PATH,
    TARGET_DATE_FORMAT, UNAMBIGUOUS_INPUT_FORMATS,
    AMBIGUOUS_FORMAT_PAIRS, DROPDOWN_PLACEHOLDER,
)


# ── Utilities ──────────────────────────────────────────────────────────────────

def resource_path(relative_path: str) -> str:
    """ Get absolute path to resource, works for dev and for PyInstaller bundle """
    if hasattr(sys, "_MEIPASS"):
        # For macOS, PyInstaller unpacks to a temporary folder in /var/folders
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def find_header_row(input_path: str, mode: str) -> int:
    """ Scans first 50 rows to detect where the actual data columns begin """
    keywords = (
        ["TXN Date", "TXN_DATE", "Initiation Date"]
        if mode == "FlexiPay"
        else ["Txn Id", "Amount", "Status", "Payment Date", "Created", "Network"]
    )
    try:
        # Use errors="replace" to handle non-UTF8 characters often found in bank exports
        with open(input_path, "r", encoding="utf-8-sig", errors="replace") as f:
            for i in range(50):
                line = f.readline()
                if not line:
                    break
                norm = re.sub(r"[\t,]+", " ", line).lower()
                if sum(1 for k in keywords if k.lower() in norm) >= 2:
                    return i
    except Exception:
        pass
    return 0


def normalize_raw_file(input_path: str, cleaned_path: str, mode: str, log=None) -> None:
    """ Cleans raw exports by skipping metadata and fixing delimiters """
    start_row = find_header_row(input_path, mode)
    if start_row > 0 and log:
        log(f"**{mode}**: Header detected at row {start_row + 1}. Skipping metadata.")
    
    temp_lines = []
    try:
        with open(input_path, "r", encoding="utf-8-sig", errors="replace") as fin:
            for _ in range(start_row):
                fin.readline()
            for line in fin:
                # Remove summary footers
                if mode == "FlexiPay" and ("total" in line.lower() or "summary" in line.lower()):
                    continue
                line = line.strip()
                if not line:
                    continue
                # Normalise delimiters (tabs to commas)
                line = re.sub(r"[\t]+", ",", line)
                if mode == "FlexiPay":
                    # Fix multi-space gaps often found in PDF-to-CSV exports
                    line = re.sub(r"[ ]{2,}", ",", line)
                temp_lines.append(line)
    except Exception as e:
        if log:
            log(f"**ERROR** reading file: {e}")
        raise

    try:
        # Write using standard Unix line endings (\n) for pandas stability
        with open(cleaned_path, "w", encoding="utf-8-sig", newline="\n") as fout:
            fout.write("\n".join(temp_lines) + "\n")
    except Exception as e:
        if log:
            log(f"**ERROR** writing normalised file: {e}")
        raise


def format_scientific_notation(val):
    """ Converts 1.23E+11 back to 123000000000 string """
    try:
        if isinstance(val, str) and re.match(r"^\s*\d+(\.\d+)?[eE]\+?\d+\s*$", val.strip()):
            return str(int(float(val)))
    except Exception:
        pass
    return val


def read_dataframe(cleaned_path: str, log=None) -> pd.DataFrame:
    """ Reads normalized CSV into a clean Pandas DataFrame """
    try:
        df = pd.read_csv(
            cleaned_path, engine="python", dtype=str,
            on_bad_lines="skip", keep_default_na=False, index_col=False,
        )
    except Exception as e:
        raise ValueError(f"Failed to read CSV. Error: {e}") from e
    
    # Sanitize column names for internal logic
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(r"[^a-zA-Z0-9\s\.\-_]", "", regex=True)
    )
    
    if log:
        cols_found = ", ".join(list(df.columns)[:5]) + "..."
        log(f"**Columns found**: {cols_found}")
        
    for c in df.columns:
        df[c] = df[c].apply(lambda x: format_scientific_notation(x) if pd.notna(x) else x)
        
    return df.fillna("")


def clean_amount_field(val) -> str:
    """ Standardizes currency strings into clean numbers """
    if pd.isna(val) or str(val).strip() == "":
        return ""
    s = str(val).strip().replace(",", "")
    s = re.sub(r"[^\d\.\-]", "", s)
    if s.count(".") > 1:
        parts = s.split(".")
        s = "".join(parts[:-1]) + "." + parts[-1]
    try:
        if s in ["", ".", "-"]:
            return ""
        f = float(s)
        return str(int(f)) if f.is_integer() else str(f)
    except Exception:
        return re.sub(r"[^\d\-]", "", s)


def get_first_column(df: pd.DataFrame, candidates: list):
    """ Fuzzy matches column names from a list of possibilities """
    actual_map = {c.strip().lower(): c for c in df.columns}
    for cand in candidates:
        if cand is None: continue
        key = cand.strip().lower()
        if key in actual_map:
            return actual_map[key]
    # Secondary partial match loop
    for cand in candidates:
        if cand is None: continue
        key = cand.strip().lower()
        for actual_lower, actual_col in actual_map.items():
            if key in actual_lower:
                return actual_col
    return None


def robust_format_to_target(date_str: str, sequence_choice: str) -> str:
    """ Standardizes varying date formats to DD-MM-YYYY HH:MM:SS """
    if date_str is None or str(date_str).strip() == "":
        return ""
    s = str(date_str).strip()
    day_first = (
        sequence_choice.upper().startswith("DD")
        if sequence_choice != DROPDOWN_PLACEHOLDER
        else False
    )
    
    try_formats = list(UNAMBIGUOUS_INPUT_FORMATS)
    for day_fmt, month_fmt in AMBIGUOUS_FORMAT_PAIRS:
        if day_first:
            try_formats.extend([day_fmt, month_fmt])
        else:
            try_formats.extend([month_fmt, day_fmt])
            
    for fmt in try_formats:
        try:
            return datetime.strptime(s, fmt).strftime(TARGET_DATE_FORMAT)
        except ValueError:
            continue
    try:
        parsed = pd.to_datetime(s, errors="coerce", dayfirst=day_first)
        if pd.isna(parsed):
            return s
        return parsed.strftime(TARGET_DATE_FORMAT)
    except Exception:
        return s


# ── Transformers ───────────────────────────────────────────────────────────────

def transform_beyonic(df: pd.DataFrame, sequence_choice: str, log=None) -> pd.DataFrame:
    """ Maps Beyonic portal exports to 4G internal format """
    if log: log("**Applying Beyonic transformation...**")
    required_cols = {
        "Txn Id":         ["Txn Id", "Txn ID", "Transaction ID", "TxnId", "ID", "Id", "Reference", "Ref"],
        "From":           ["From", "From No", "From Number", "From Phone", "Sender", "Source", "Source No"],
        "Amount":         ["Amount", "AMOUNT", "Amt", "Value", "CR", "Debit", "Credit"],
        "Network":        ["Network", "Network Name", "Provider", "Operator"],
        "Network Txn Ref":["Network Txn Ref", "Network Txn Ref.", "Network Reference", "Network Ref"],
        "Status":         ["Status", "Payment Status", "Transaction Status"],
        "Payment Date":   ["Payment Date", "Paid At", "PaymentDate", "Date", "Payment Time", "Created At"],
    }
    out_cols = list(required_cols.keys())
    new_df = pd.DataFrame(index=df.index, columns=out_cols, dtype=str)
    date_col = None
    id_fallback_src = get_first_column(df, ["Id", "ID", "id", "Reference", "Ref"])

    for out_col in out_cols:
        found = get_first_column(df, required_cols[out_col])
        if found:
            new_df[out_col] = df[found].astype(str).fillna("").apply(str.strip)
            if out_col == "Payment Date": date_col = out_col
        else:
            new_df[out_col] = ""

    new_df["Amount"] = new_df["Amount"].apply(clean_amount_field)

    def resolve_txn_id(row_idx, current_val):
        val = str(current_val).strip()
        if val and val.upper().startswith("T"):
            return val
        if id_fallback_src:
            fb = str(df.loc[row_idx, id_fallback_src]).strip()
            if fb and fb.lower() != "nan": return fb
        return f"T_BLANK_{row_idx}"

    new_df["Txn Id"] = [resolve_txn_id(i, v) for i, v in new_df["Txn Id"].items()]
    if date_col:
        new_df[date_col] = new_df[date_col].apply(lambda x: robust_format_to_target(x, sequence_choice))
    return new_df.fillna("").astype(str)


def transform_flexipay(df: pd.DataFrame, sequence_choice: str, log=None) -> pd.DataFrame:
    """ Maps Flexipay exports and filters for valid transactions """
    if log: log("**Applying FlexiPay transformation & filtering...**")
    candidates = {
        "Initiation Date":       ["TXN Date", "TXN_DATE", "Txn Date", "Initiation Date", "Transaction Date"],
        "Transaction ID":        ["TXN Ref", "TXNRef", "Txn Ref", "Transaction ID", "EXT. ref", "EXT ref"],
        "Transaction Ref Number":["EXT. ref", "EXT ref", "EXT.ref", "EXT_REF", "Ext Ref", "Ref No"],
        "Initiator Number":      ["Source No.", "Source No", "Source Number", "Source", "Initiator"],
        "Account Number":        ["Dest No.", "Dest No", "Destination No", "Account Number", "Account No"],
        "Transaction Type":      ["TXN Type", "TXN Type.", "Transaction Type", "Txn Type", "TXN_TYPE"],
        "Credit Amount":         ["Credit", "Credit Amount", "CreditAmt", "Amount", "CR", "Cr"],
        "Status":                ["Status", "Transaction Status", "Txn Status"],
        "Notes":                 ["Narration", "Notes", "Narrative", "Description"],
        "Transaction Reason":    ["Reason for Transfer", "Reason", "Transaction Reason"],
    }
    out_cols = list(candidates.keys())
    new_df = pd.DataFrame(index=df.index, columns=out_cols, dtype=str)
    date_col = None

    for out_col in out_cols:
        found = get_first_column(df, candidates[out_col])
        if found:
            new_df[out_col] = df[found].astype(str).fillna("").apply(str.strip)
            if out_col == "Initiation Date": date_col = out_col
        else:
            new_df[out_col] = ""

    new_df["Credit Amount"] = new_df["Credit Amount"].apply(clean_amount_field)

    # Filtering Logic
    if "Transaction Type" in new_df.columns and "Status" in new_df.columns:
        initial_count = len(new_df)
        type_mask   = new_df["Transaction Type"].str.upper().str.strip().isin(["MERCHANT PURCHASE", "AIRTEL CASHIN"])
        status_mask = new_df["Status"].str.upper().str.strip() == "SUCCESSFUL"
        new_df = new_df[type_mask & status_mask].copy()
        if log:
            dropped = initial_count - len(new_df)
            log(f"**FlexiPay**: Filtered {dropped} rows. **{len(new_df)}** valid rows remain.")

    if date_col:
        new_df[date_col] = new_df[date_col].apply(lambda x: robust_format_to_target(x, sequence_choice))
    return new_df.fillna("").astype(str)


# ── Save ───────────────────────────────────────────────────────────────────────

def save_chunks(df_out: pd.DataFrame, base_output_dir: str, mode: str = "Beyonic", log=None) -> list:
    """ Splits large dataframes into smaller CSV chunks and saves them to Desktop """
    
    # Mac Logic: Resolve desktop path correctly even with iCloud enabled
    home = os.path.expanduser("~")
    desktop_standard = os.path.join(home, "Desktop")
    desktop_icloud = os.path.join(home, "Library", "Mobile Documents", "com~apple~CloudDocs", "Desktop")
    
    # Use iCloud path if it exists, otherwise standard
    final_desktop = desktop_icloud if os.path.exists(desktop_icloud) else desktop_standard
    
    # Update base_output_dir relative to the detected Desktop
    output_dir_name = os.path.basename(base_output_dir)
    real_output_path = os.path.join(final_desktop, output_dir_name)
    
    os.makedirs(real_output_path, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_files = []
    df_clean = df_out.fillna("").astype(str)
    num_rows = len(df_clean)

    if num_rows == 0:
        if log: log("**Warning**: No rows to save.")
        return []

    num_parts = (num_rows - 1) // MAX_ROWS + 1
    for part in range(num_parts):
        chunk  = df_clean.iloc[part * MAX_ROWS:(part + 1) * MAX_ROWS]
        suffix = f"_Part{part + 1}" if num_parts > 1 else ""
        fname  = f"{mode}{suffix}_{timestamp}.csv"
        path   = os.path.join(real_output_path, fname)
        try:
            # Use UTF-8-SIG for Mac Excel compatibility and CRLF for Windows compatibility
            chunk.to_csv(
                path, index=False, quoting=csv.QUOTE_MINIMAL,
                encoding="utf-8-sig", lineterminator="\r\n",
            )
            saved_files.append(path)
            if log: log(f"**Saved** {len(chunk)} rows → {fname}")
        except Exception as e:
            if log: log(f"**ERROR** saving chunk: {e}")
            
    return saved_files