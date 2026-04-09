# groq_parser.py
"""
Groq-API-powered payment field extractor.

Post-processing rules
─────────────────────
Beyonic
  PhoneNumber   → +256XXXXXXXXX  (spaces stripped)
  BeyonicTxnId  → MUST start with T.
                   Priority: T-prefixed in text → labelled numeric near txn/ref/id
                   → AI returned T-prefixed → AI returned bare labelled numeric.
                   NEVER blindly grabs the first long number — must be near a label
                   OR the AI explicitly confirmed it.
  NetworkTxnId  → Numeric ID near tid/txnid/id/ref/network labels, not a phone.
  PaymentDate   → "Mon DD, YYYY HH:MM" — aggressive date+time parsing.
                   Time is extracted from the reference text and combined with
                   the date when a standalone time token (HH:MM / HH:MM:SS)
                   is found nearby.

Airtel
  customerReferenceNumber / senderPhoneNumber → 256XXXXXXXXX (cross-filled)
  transactionId → plain numeric string, NO T prefix ever.
  All three date fields → YYYY-MM-DDTHH:MM:SSZ including real time if found.

Bank
  billRefNumber / mobile → 256XXXXXXXXX (cross-filled, spaces stripped)
  transactionId          → must start with S
  completionDate         → YYYY-MM-DD

Flexipay
  billRefNumber / mobile → 256XXXXXXXXX (cross-filled, spaces stripped)
  transactionId          → MUST start with 3000; fallback regex scan
  completionDate         → YYYY-MM-DD
"""

import http.client
import json
import re
import ssl
from datetime import datetime, timedelta

GROQ_HOST     = "api.groq.com"
GROQ_PATH     = "/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.1-8b-instant"

# ─── Compiled patterns ────────────────────────────────────────────────────────

_UG_PHONE_RE = re.compile(
    r'(?<!\d)'
    r'(?:\+?256\s*|0\s*)?'
    r'(7[\d\s]{9,14})'
    r'(?!\d)'
)

_BEYO_TXN_T_RE   = re.compile(r'\bT\d{6,}\b')
_BEYO_TXN_NUM_RE = re.compile(
    r'(?:txn\s*(?:id)?|transaction\s*(?:id)?|ref(?:erence)?|tid)\s*[:#\-]?\s*(\d{6,14})',
    re.IGNORECASE
)
_NET_TXN_RE = re.compile(
    r'(?:network\s*(?:txn|transaction|ref|id)?|tid|txnid|id|ref(?:erence)?)'
    r'\s*[:#\-]?\s*(\d{6,14})',
    re.IGNORECASE
)
_FLEX_TXN_RE   = re.compile(r'(?<!\d)(3000\d+)(?!\d)')
_GENERIC_ID_RE = re.compile(r'(?<!\d)(\d{8,14})(?!\d)')

# Time token: HH:MM or HH:MM:SS  (24-hour, 00-23 : 00-59)
_TIME_RE = re.compile(r'\b([01]\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?\b')

_AIRTEL_DATE_FIELDS = (
    "creationDate",
    "agentAssignmentDateTime",
    "paymentTransactionDateTime",
)

_MONTH_PAT = (
    r'jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
    r'jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?'
)


# ═══════════════════════════════════════════════════════════════════════════
# PHONE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _strip_spaces(s: str) -> str:
    return re.sub(r'\s+', '', s)


def _extract_ug_phone_local(text: str) -> str:
    """Return 9-digit local Ugandan number (7XXXXXXXX) or ''."""
    for m in _UG_PHONE_RE.finditer(text):
        digits = _strip_spaces(m.group(1))
        if re.fullmatch(r'7\d{8}', digits):
            return digits
    collapsed = _strip_spaces(text)
    for pat in [r'(?:\+?256)(7\d{8})', r'0(7\d{8})', r'(?<!\d)(7\d{8})(?!\d)']:
        m = re.search(pat, collapsed)
        if m:
            return m.group(1)
    return ""


def _is_valid_ug_local(d: str) -> bool:
    return bool(re.fullmatch(r'7\d{8}', d))


def _to_256(local9: str) -> str:
    return "256" + local9


def _to_plus256(local9: str) -> str:
    return "+256" + local9


def _normalise_256(raw: str) -> str:
    collapsed = _strip_spaces(raw.strip())
    digits = collapsed.lstrip("+")
    if re.fullmatch(r'256\d{9}', digits):
        return digits
    if digits.startswith("256") and len(digits) > 9:
        local = digits[3:]
    elif digits.startswith("0") and len(digits) == 10:
        local = digits[1:]
    else:
        local = digits
    if _is_valid_ug_local(local):
        return _to_256(local)
    found = _extract_ug_phone_local(raw)
    return _to_256(found) if found else ""


def _normalise_plus256(raw: str) -> str:
    collapsed = _strip_spaces(raw.strip())
    digits = collapsed.lstrip("+")
    if re.fullmatch(r'256\d{9}', digits):
        return "+" + digits
    if digits.startswith("256") and len(digits) > 9:
        local = digits[3:]
    elif digits.startswith("0") and len(digits) == 10:
        local = digits[1:]
    else:
        local = digits
    if _is_valid_ug_local(local):
        return _to_plus256(local)
    found = _extract_ug_phone_local(raw)
    return _to_plus256(found) if found else ""


# ═══════════════════════════════════════════════════════════════════════════
# TRANSACTION ID HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _extract_beyonic_txn_id(raw_val: str, raw_text: str) -> str:
    """
    Find BeyonicTxnId — MUST start with T.

    Rules (strict — never blindly grabs a number):
      1. AI returned T\\d+ → accept directly
      2. Raw text contains T\\d{6,} → use it
      3. Raw text has labelled numeric (txn id / ref / tid + number) → prepend T
      4. AI returned bare numeric AND it was near a label in the prompt →
         check raw_text for the same number near a label first
      5. AI returned bare numeric that isn't a phone/amount → prepend T
         (only if no other candidate was found)

    We do NOT fall back to "first generic long number" to avoid grabbing
    amounts, phone numbers, or network IDs.
    """
    v = (raw_val or "").strip()

    # 1. AI returned a proper T-prefixed ID
    if re.fullmatch(r'[Tt]\d+', v):
        return "T" + v.lstrip("Tt")

    # 2. Scan raw text for T-prefixed ID
    m = _BEYO_TXN_T_RE.search(raw_text)
    if m:
        return m.group()

    # 3. Labelled numeric in raw text
    m = _BEYO_TXN_NUM_RE.search(raw_text)
    if m:
        cand = m.group(1)
        if not _is_valid_ug_local(cand):
            return "T" + cand

    # 4 & 5. AI returned a bare numeric — only accept if not a phone/amount
    if re.fullmatch(r'\d{6,14}', v):
        if not _is_valid_ug_local(v):
            # Double-check: is this number actually in the text near a label?
            # If yes, safe to use. If not labelled, still use if 8+ digits.
            labelled = re.search(
                r'(?:txn(?:id)?|transaction\s*(?:id)?|ref(?:erence)?|tid)'
                r'\s*[:#\-]?\s*' + re.escape(v),
                raw_text, re.IGNORECASE
            )
            if labelled or len(v) >= 8:
                return "T" + v

    return ""


def _extract_network_txn_id(raw_val: str, raw_text: str) -> str:
    """
    Find NetworkTxnId — numeric ID near a label. NOT a phone. NO T prefix.
    """
    v = (raw_val or "").strip()
    if re.fullmatch(r'\d{6,14}', v) and not _is_valid_ug_local(v):
        return v
    m = _NET_TXN_RE.search(raw_text)
    if m:
        cand = m.group(1)
        if not _is_valid_ug_local(cand):
            return cand
    # Last resort: first long numeric that isn't a phone or Flexipay ID
    for m2 in _GENERIC_ID_RE.finditer(raw_text):
        cand = m2.group(1)
        if _is_valid_ug_local(cand):
            continue
        if cand.startswith("3000"):
            continue
        return cand
    return ""


# ═══════════════════════════════════════════════════════════════════════════
# DATE + TIME PARSING
# ═══════════════════════════════════════════════════════════════════════════

_DATE_FMTS = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M",
    "%d-%m-%Y %H:%M",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d %b %Y %H:%M",
    "%d %B %Y %H:%M",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y %H:%M",
    "%B %d, %Y %H:%M",
    "%b %d, %Y",
    "%B %d, %Y",
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%b %d %Y",
    "%B %d %Y",
]


def _parse_date(raw: str) -> datetime | None:
    """
    Parse a single string into a datetime.
    Handles standard formats, compact DDMMYYYY/YYYYMMDD/DDMMYY,
    and natural language (today/yesterday/tomorrow).
    """
    if not raw:
        return None
    s = raw.strip()
    sl = s.lower()

    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if sl in ("today", "now"):
        return now
    if sl == "yesterday":
        return now - timedelta(days=1)
    if sl == "tomorrow":
        return now + timedelta(days=1)

    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass

    digits = re.sub(r'\D', '', s)
    if len(digits) == 8:
        for fmt in ("%d%m%Y", "%Y%m%d"):
            try:
                d = datetime.strptime(digits, fmt)
                if 2000 <= d.year <= 2099:
                    return d
            except ValueError:
                pass
    if len(digits) == 6:
        try:
            d = datetime.strptime(digits, "%d%m%y")
            if 2000 <= d.year <= 2099:
                return d
        except ValueError:
            pass
    return None


def _extract_time(text: str) -> tuple[int, int, int] | None:
    """
    Scan text for the first valid HH:MM or HH:MM:SS token.
    Handles both standalone "10:03" and ISO "T11:39:23Z" forms.
    Returns (hour, minute, second) or None.
    """
    # 1. ISO format: T followed by HH:MM:SS (with optional Z)
    iso_m = re.search(r'T([01]\d|2[0-3]):([0-5]\d):([0-5]\d)Z?', text)
    if iso_m:
        return (int(iso_m.group(1)), int(iso_m.group(2)), int(iso_m.group(3)))

    # 2. Standalone HH:MM:SS or HH:MM
    for m in _TIME_RE.finditer(text):
        h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
        return (h, mi, s)

    return None


def _scan_date_in_text(text: str) -> datetime | None:
    """
    Scan free text for ANY recognisable date+time.
    Extracts date tokens, then tries to combine with a nearby time token.
    """
    # Helper: try to find a time token near a given position in text
    def _nearby_time(pos: int, window: int = 120) -> tuple[int, int, int] | None:
        snippet = text[max(0, pos - window): pos + window]
        return _extract_time(snippet)

    def _with_time(dt: datetime, pos: int) -> datetime:
        t = _nearby_time(pos)
        if t:
            return dt.replace(hour=t[0], minute=t[1], second=t[2])
        return dt

    # 1. Month-name multi-word tokens
    for pat in [
        rf'\d{{1,2}}\s+(?:{_MONTH_PAT})\s+\d{{4}}(?:\s+\d{{1,2}}:\d{{2}}(?::\d{{2}})?)?',
        rf'(?:{_MONTH_PAT})\s+\d{{1,2}},?\s+\d{{4}}(?:\s+\d{{1,2}}:\d{{2}}(?::\d{{2}})?)?',
    ]:
        for m in re.finditer(pat, text, re.IGNORECASE):
            dt = _parse_date(m.group())
            if dt:
                return _with_time(dt, m.start())

    # 2a. ISO: YYYY-MM-DD[T ]HH:MM[:SS][Z]
    for m in re.finditer(
        r'\d{4}[-/]\d{2}[-/]\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?Z?)?', text
    ):
        dt = _parse_date(m.group())
        if dt:
            return _with_time(dt, m.start())

    # 2b. DD/MM/YYYY or DD-MM-YYYY [HH:MM[:SS]]
    for m in re.finditer(
        r'\d{2}[-/]\d{2}[-/]\d{4}(?:\s+\d{2}:\d{2}(?::\d{2})?)?', text
    ):
        dt = _parse_date(m.group())
        if dt:
            return _with_time(dt, m.start())

    # 3. Compact 8-digit (DDMMYYYY or YYYYMMDD) — sanity-checked
    for m in re.finditer(r'(?<!\d)(\d{8})(?!\d)', text):
        cand = m.group(1)
        day, tail, yr4 = int(cand[:2]), int(cand[4:]), int(cand[:4])
        is_dmy = 1 <= day <= 31 and 2000 <= tail <= 2099
        is_ymd = 2000 <= yr4 <= 2099 and 1 <= int(cand[4:6]) <= 12
        if not (is_dmy or is_ymd):
            continue
        dt = _parse_date(cand)
        if dt:
            return _with_time(dt, m.start())

    # 4. Natural language
    for m in re.finditer(r'\b(today|yesterday|tomorrow|now)\b', text, re.IGNORECASE):
        dt = _parse_date(m.group())
        if dt:
            return _with_time(dt, m.start())

    return None


# ═══════════════════════════════════════════════════════════════════════════
# PER-TYPE FIELD SPECS
# ═══════════════════════════════════════════════════════════════════════════

_TYPE_SPECS = {
    "Beyonic": [
        ("BeyonicWallet", "string",
         'Wallet / recipient name, e.g. "KUZA". Look for labels like "wallet", '
         '"account", "recipient", or a capitalised service name.'),
        ("BeyonicTxnId",  "string",
         'Transaction ID — MUST start with the letter T, e.g. "T91592568". '
         'Look for a T-prefixed code, OR a label like "Txn id", "TxnId", '
         '"transaction id", "ref" followed by a number (output that number — '
         'post-processing adds T). Do NOT output if only an amount or phone exists.'),
        ("Name",          "string", 'Full name of the sender / payer.'),
        ("PhoneNumber",   "string",
         'PHONE RULE: starts with 0/07/7/+256/256; 9 digits after prefix (7XXXXXXXX). '
         'Spaces OK — strip them. Output with +256 prefix, e.g. "+256751046941". '
         'Not an ID, amount, or date.'),
        ("Amount",        "NUMBER", 'Payment amount — numeric only, no symbols.'),
        ("Network",       "string", '"MTN Uganda" or "Airtel Uganda".'),
        ("NetworkTxnId",  "string",
         'Network-side numeric reference (6-14 digits) near labels like "Tid", '
         '"TxnId", "Id", "Ref", "Network ref". NOT a phone number.'),
        ("PaymentDate",   "string",
         'DATE + TIME: Find any date AND any time (HH:MM or HH:MM:SS) in the text. '
         'Compact "28032026" = 28 March 2026. "today" = today\'s date. '
         'If a time like "10:03" appears anywhere near the date, include it. '
         'Output: "Mon DD, YYYY HH:MM" e.g. "Mar 28, 2026 10:03". '
         'Use 00:00 only if absolutely no time is found.'),
    ],
    "Airtel": [
        ("creationDate",               "string",
         'DATE + TIME: find any date and time. '
         'Format: "YYYY-MM-DDTHH:MM:SSZ" e.g. "2026-03-21T11:39:23Z". '
         'Use T00:00:00Z only if no time found.'),
        ("agentAssignmentDateTime",    "string",
         'DATE + TIME: same value as creationDate. '
         'Format: "YYYY-MM-DDTHH:MM:SSZ".'),
        ("customerReferenceNumber",    "string",
         'PHONE RULE: starts with 0/07/7/+256/256; 9 digits after prefix; spaces OK. '
         'Output digits only with 256 prefix, e.g. "256702987351". Not an ID.'),
        ("transactionId",              "string",
         'Plain numeric transaction ID — digits only, NO letter prefix, '
         'e.g. "143363767927". Do NOT prepend T or any letter.'),
        ("customerReferenceType",      "string", 'Always "PHONE_NUMBER".'),
        ("paymentAmount",              "NUMBER", 'Numeric — no quotes, no symbols.'),
        ("paymentTransactionDateTime", "string",
         'DATE + TIME: same value as creationDate. '
         'Format: "YYYY-MM-DDTHH:MM:SSZ".'),
        ("senderPhoneNumber",          "string",
         'PHONE RULE: same as customerReferenceNumber. 256 prefix, digits only.'),
    ],
    "Bank": [
        ("name",          "string", 'CONSTANT: always "FOURTH".'),
        ("amount",        "string", '2 decimal places, e.g. "651000.00".'),
        ("transactionId", "string",
         'Must start with "S". Prepend S if missing. e.g. "S34111201".'),
        ("billRefNumber", "string",
         'PHONE RULE: starts with 0/07/7/+256/256; 9 digits after prefix; spaces OK. '
         'Output digits only with 256 prefix, e.g. "256774718807". Not an ID.'),
        ("countryCode",   "string", '"UG".'),
        ("completionDate","string",
         'DATE RULE: Find any date. Output: "YYYY-MM-DD" e.g. "2026-03-28".'),
        ("mobile",        "string",
         'PHONE RULE: same as billRefNumber. 256 prefix, digits only.'),
        ("loanAccountId", "string", 'UUID format.'),
    ],
    "Flexipay": [
        ("name",          "string", 'CONSTANT: always "FOURTH".'),
        ("amount",        "string", 'Whole number, no decimals, e.g. "1140000".'),
        ("transactionId", "string",
         'CRITICAL: ONLY a number starting with "3000" e.g. "300068579130". '
         'Ignore ALL other IDs. Output "" if none found.'),
        ("billRefNumber", "string",
         'PHONE RULE: starts with 0/07/7/+256/256; 9 digits after prefix; spaces OK. '
         'Output digits only with 256 prefix, e.g. "256759762086". Not an ID.'),
        ("countryCode",   "string", '"UG".'),
        ("completionDate","string",
         'DATE RULE: Find any date. Output: "YYYY-MM-DD" e.g. "2026-03-28".'),
        ("mobile",        "string",
         'PHONE RULE: same as billRefNumber. 256 prefix, digits only.'),
        ("loanAccountId", "string", 'UUID format.'),
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# PROMPT TEMPLATE
# ═══════════════════════════════════════════════════════════════════════════

_PROMPT_TEMPLATE = """\
You are a payment data extraction assistant.
Payment type: {json_type}

Extract field values from the source text. Return ONLY a flat JSON object:
{field_lines}

═══ CRITICAL EXTRACTION RULES ═══

PHONE NUMBERS  (PhoneNumber, customerReferenceNumber, senderPhoneNumber,
                billRefNumber, mobile)
- Valid Ugandan mobile: starts with 07 / 0 / 7 / +256 / 256
- Exactly 9 digits after the prefix  (local format: 7XXXXXXXX)
- Spaces within the number are OK — strip them
- Examples: "0751 046 941" = "0751046941" = "+256751046941"
- NEVER use amounts, IDs, or dates as phone numbers

DATE AND TIME
- Search the ENTIRE text for any date AND any time token (HH:MM or HH:MM:SS)
- Even if date and time appear separately, combine them
- Compact "28032026" = DD MM YYYY = 28 March 2026
- "today" / "now" = today's date
- If a real time is found (e.g. "10:03"), ALWAYS include it — do not default to 00:00
- Use 00:00 / T00:00:00Z ONLY when absolutely no time token exists in the text
- Beyonic PaymentDate   : "Mon DD, YYYY HH:MM"       e.g. "Mar 28, 2026 10:03"
- Airtel date fields    : "YYYY-MM-DDTHH:MM:SSZ"     e.g. "2026-03-21T11:39:23Z"
- Bank/Flexipay dates   : "YYYY-MM-DD"               e.g. "2026-03-28"

BEYONIC BeyonicTxnId
- MUST start with T  (e.g. T91592568)
- Look for T-prefixed codes OR labels "Txn id / TxnId / transaction id / ref"
  followed by a number — output that number, post-processing adds T
- Do NOT output if only an amount or phone number exists with no ID label

AIRTEL transactionId
- Plain numeric digits ONLY — e.g. "143363767927"
- Do NOT add any letter prefix (no T, no S, nothing)

BEYONIC NetworkTxnId
- Numeric ID (6-14 digits) near labels "Tid / TxnId / Id / Ref / Network ref"
- Must NOT look like a phone number (9 digits starting with 7)

FLEXIPAY transactionId
- ONLY a number starting with "3000"  e.g. "300068579130"
- IGNORE all other IDs — output "" if none found

OTHER
- Bank/Flexipay name: always "FOURTH"
- Bank transactionId: must start with S — prepend S if missing
- amount: numeric only, no quotes, no symbols
- Missing value: output ""
"""

_HEADERS = {
    "Content-Type":    "application/json",
    "Accept":          "application/json",
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection":      "keep-alive",
}


def _build_prompt(json_type: str) -> str:
    lines = [
        f'  "{key}": {kind}  // {hint}'
        for key, kind, hint in _TYPE_SPECS[json_type]
    ]
    return _PROMPT_TEMPLATE.format(
        json_type=json_type,
        field_lines="{\n" + "\n".join(lines) + "\n}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# POST-PROCESSING
# ═══════════════════════════════════════════════════════════════════════════

def _apply_rules(json_type: str, processed: dict, raw_text: str = "") -> dict:

    def _v256(raw_val: str) -> str:
        candidate = _normalise_256(raw_val) if raw_val else ""
        if candidate and re.fullmatch(r'256\d{9}', candidate):
            return candidate
        found = _extract_ug_phone_local(raw_text)
        return _to_256(found) if found else ""

    def _v_plus256(raw_val: str) -> str:
        candidate = _normalise_plus256(raw_val) if raw_val else ""
        if candidate and re.fullmatch(r'\+256\d{9}', candidate):
            return candidate
        found = _extract_ug_phone_local(raw_text)
        return _to_plus256(found) if found else ""

    # ── Beyonic ──────────────────────────────────────────────────────────
    if json_type == "Beyonic":

        # PhoneNumber
        phone = processed.get("PhoneNumber", "").strip()
        vp = _v_plus256(phone)
        if vp:
            processed["PhoneNumber"] = vp
        else:
            processed.pop("PhoneNumber", None)

        # BeyonicTxnId
        txn_raw = processed.get("BeyonicTxnId", "").strip()
        txn = _extract_beyonic_txn_id(txn_raw, raw_text)
        if txn:
            processed["BeyonicTxnId"] = txn
        else:
            processed.pop("BeyonicTxnId", None)

        # NetworkTxnId
        net_raw = processed.get("NetworkTxnId", "").strip()
        net = _extract_network_txn_id(net_raw, raw_text)
        if net:
            processed["NetworkTxnId"] = net
        else:
            processed.pop("NetworkTxnId", None)

        # PaymentDate — parse AI value first; fall back to full text scan
        # Both paths try to attach a real time from the raw text
        pd_raw = processed.get("PaymentDate", "").strip()
        dt = _parse_date(pd_raw) if pd_raw else None
        if dt is not None:
            # Try to enhance with a real time from the raw text
            t = _extract_time(raw_text)
            if t and dt.hour == 0 and dt.minute == 0:
                dt = dt.replace(hour=t[0], minute=t[1], second=t[2])
        else:
            dt = _scan_date_in_text(raw_text)

        if dt:
            processed["PaymentDate"] = dt.strftime("%b %d, %Y %H:%M")
        else:
            processed.pop("PaymentDate", None)

    # ── Airtel ───────────────────────────────────────────────────────────
    elif json_type == "Airtel":

        # Phone cross-fill
        crn = processed.get("customerReferenceNumber", "").strip()
        spn = processed.get("senderPhoneNumber", "").strip()
        master_phone = _v256(crn or spn)
        if master_phone:
            processed["customerReferenceNumber"] = master_phone
            processed["senderPhoneNumber"]        = master_phone
        else:
            processed.pop("customerReferenceNumber", None)
            processed.pop("senderPhoneNumber", None)

        # transactionId — strip any accidental T/S prefix the AI might add
        tid = processed.get("transactionId", "").strip()
        if tid and not re.fullmatch(r'\d+', tid):
            # Remove leading non-digit characters
            tid = re.sub(r'^\D+', '', tid)
        if tid:
            processed["transactionId"] = tid

        # Date cross-fill with real time
        dt = None
        for df in _AIRTEL_DATE_FIELDS:
            val = processed.get(df, "").strip()
            dt = _parse_date(val) if val else None
            if dt:
                break
        if dt is not None:
            # Enhance with time from raw text if AI gave only date
            t = _extract_time(raw_text)
            if t and dt.hour == 0 and dt.minute == 0:
                dt = dt.replace(hour=t[0], minute=t[1], second=t[2])
        else:
            dt = _scan_date_in_text(raw_text)

        if dt:
            fmt = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            for df in _AIRTEL_DATE_FIELDS:
                processed[df] = fmt

    # ── Bank ─────────────────────────────────────────────────────────────
    elif json_type == "Bank":
        processed["name"] = "FOURTH"

        tid = processed.get("transactionId", "").strip()
        if tid and not tid.upper().startswith("S"):
            processed["transactionId"] = "S" + tid

        brn    = processed.get("billRefNumber", "").strip()
        mobile = processed.get("mobile", "").strip()
        mp = _v256(brn or mobile)
        if mp:
            processed["billRefNumber"] = mp
            processed["mobile"]        = mp
        else:
            processed.pop("billRefNumber", None)
            processed.pop("mobile", None)

        cd_raw = processed.get("completionDate", "").strip()
        dt = _parse_date(cd_raw) if cd_raw else None
        if dt is None:
            dt = _scan_date_in_text(raw_text)
        processed["completionDate"] = dt.strftime("%Y-%m-%d") if dt else processed.pop("completionDate", None) or ""

    # ── Flexipay ─────────────────────────────────────────────────────────
    elif json_type == "Flexipay":
        processed["name"] = "FOURTH"

        tid = processed.get("transactionId", "").strip()
        if not tid.startswith("3000"):
            m = _FLEX_TXN_RE.search(raw_text)
            tid = m.group(1) if m else ""
        processed["transactionId"] = tid

        brn    = processed.get("billRefNumber", "").strip()
        mobile = processed.get("mobile", "").strip()
        mp = _v256(brn or mobile)
        if mp:
            processed["billRefNumber"] = mp
            processed["mobile"]        = mp
        else:
            processed.pop("billRefNumber", None)
            processed.pop("mobile", None)

        cd_raw = processed.get("completionDate", "").strip()
        dt = _parse_date(cd_raw) if cd_raw else None
        if dt is None:
            dt = _scan_date_in_text(raw_text)
        processed["completionDate"] = dt.strftime("%Y-%m-%d") if dt else processed.pop("completionDate", None) or ""

    return processed


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def groq_extract(
    text: str,
    json_type: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Call the Groq API then apply all normalisation and business rules."""
    if not api_key or not api_key.strip():
        raise ValueError("No API key provided. Enter your Groq API key in Settings.")
    if json_type not in _TYPE_SPECS:
        raise ValueError(f"Unknown payment type: {json_type!r}")

    body_bytes = json.dumps({
        "model":    model,
        "messages": [
            {"role": "system", "content": _build_prompt(json_type)},
            {"role": "user",   "content": text},
        ],
        "temperature":     0,
        "max_tokens":      700,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    headers = dict(_HEADERS)
    headers["Authorization"]  = f"Bearer {api_key.strip()}"
    headers["Content-Length"] = str(len(body_bytes))

    ctx = ssl.create_default_context()
    try:
        conn = http.client.HTTPSConnection(GROQ_HOST, timeout=20, context=ctx)
        conn.request("POST", GROQ_PATH, body=body_bytes, headers=headers)
        resp     = conn.getresponse()
        raw_resp = resp.read().decode("utf-8", errors="replace")
    except OSError as exc:
        raise ConnectionError(f"Network error: {exc}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

    if resp.status not in (200, 201):
        raise ConnectionError(f"Groq API error {resp.status}: {raw_resp[:200]}")

    try:
        envelope    = json.loads(raw_resp)
        raw_content = envelope["choices"][0]["message"]["content"].strip()
        result      = json.loads(raw_content)
    except Exception as exc:
        raise ValueError(f"Failed to parse AI response: {exc}")

    processed = {
        k: str(v).strip()
        for k, v in result.items()
        if str(v).strip()
    }

    processed = _apply_rules(json_type, processed, raw_text=text)
    return processed