# json_data.py
"""
JSON field definitions for each payment type and the payload builder.

Each entry in JSON_FIELDS[type] is a tuple:
  (key, label, default_value, is_numeric)
"""

# ── Field Definitions ──────────────────────────────────────────────────────────
JSON_FIELDS: dict[str, list[tuple]] = {
    "Beyonic": [
        ("BeyonicWallet", "BeyonicWallet",  "KUZA",        False),
        ("BeyonicTxnId",  "BeyonicTxnId",   "",            False),
        ("Name",          "Name",            "",            False),
        ("PhoneNumber",   "PhoneNumber",     "+256",        False),
        ("Amount",        "Amount",          "",            True),
        ("Network",       "Network",         "MTN Uganda",  False),
        ("NetworkTxnId",  "NetworkTxnId",    "",            False),
        ("PaymentDate",   "PaymentDate",     "",            False),
    ],
    "Airtel": [
        ("creationDate",               "creationDate",               "",             False),
        ("agentAssignmentDateTime",    "agentAssignmentDateTime",    "",             False),
        ("customerReferenceNumber",    "customerReferenceNumber",    "256",          False),
        ("transactionId",              "transactionId",              "",             False),
        ("customerReferenceType",      "customerReferenceType",      "PHONE_NUMBER", False),
        ("paymentAmount",              "paymentAmount",              "",             True),
        ("paymentTransactionDateTime", "paymentTransactionDateTime", "",             False),
        ("senderPhoneNumber",          "senderPhoneNumber",          "256",          False),
    ],
    "Bank": [
        ("name",          "name",          "FOURTH", False),
        ("amount",        "amount",        "",       False),
        ("transactionId", "transactionId", "S",      False),
        ("billRefNumber", "billRefNumber", "256",    False),
        ("countryCode",   "countryCode",   "UG",     False),
        ("completionDate","completionDate","",        False),
        ("mobile",        "mobile",        "256",    False),
        ("loanAccountId", "loanAccountId", "",       False),
    ],
    "Flexipay": [
        ("name",          "name",          "FOURTH", False),
        ("amount",        "amount",        "",       False),
        ("transactionId", "transactionId", "3000",   False),   # default starts with 3000
        ("billRefNumber", "billRefNumber", "256",    False),
        ("countryCode",   "countryCode",   "UG",     False),
        ("completionDate","completionDate","",        False),
        ("mobile",        "mobile",        "256",    False),
        ("loanAccountId", "loanAccountId", "",       False),
    ],
}

# ── Hint text shown below each field ──────────────────────────────────────────
JSON_HINTS: dict[str, dict[str, str]] = {
    "Beyonic": {
        "BeyonicTxnId": "e.g. T91592568",
        "PhoneNumber":  "e.g. +256753890912",
        "Amount":       "numeric  e.g. 126500",
        "PaymentDate":  "e.g. Feb 27, 2026 10:03",
        "NetworkTxnId": "e.g. 141693582907",
    },
    "Airtel": {
        "creationDate":               "e.g. 2026-03-21T11:39:23Z",
        "agentAssignmentDateTime":    "e.g. 2026-03-21T11:39:23Z",
        "customerReferenceNumber":    "e.g. 256702987351",
        "transactionId":              "e.g. 143363767927",
        "paymentAmount":              "numeric  e.g. 32000",
        "paymentTransactionDateTime": "e.g. 2026-03-21T11:39:23Z",
        "senderPhoneNumber":          "e.g. 256702987351",
    },
    "Bank": {
        "amount":        "e.g. 651000.00",
        "transactionId": "Must start with S  e.g. S34111201",
        "billRefNumber": "e.g. 256774718807",
        "completionDate":"e.g. 2026-03-20",
        "mobile":        "e.g. 256774718807",
        "loanAccountId": "e.g. 401d0a03-419f-47b6-b3d1-2884b8128fdc",
    },
    "Flexipay": {
        "amount":        "e.g. 1140000",
        "transactionId": "Must start with 3000  e.g. 300066833232",
        "billRefNumber": "e.g. 256759762086",
        "completionDate":"e.g. 2026-03-04",
        "mobile":        "e.g. 256759762086",
        "loanAccountId": "e.g. 233ea078-1250-4a8d-985a-d3faa2407580",
    },
}


# ── Payload builder ────────────────────────────────────────────────────────────

def build_json_payload(json_type: str, values_dict: dict) -> dict:
    """Return a dict with correct Python types ready for json.dumps."""
    result = {}
    for key, _label, _default, is_numeric in JSON_FIELDS[json_type]:
        val = values_dict.get(key, "").strip()

        # Enforce transactionId prefixes
        if key == "transactionId" and val:
            if json_type == "Bank" and not val.upper().startswith("S"):
                val = "S" + val
            elif json_type == "Flexipay" and not val.startswith("3000"):
                val = "3000" + val

        # Enforce constant name
        if key == "name" and json_type in ("Bank", "Flexipay"):
            val = "FOURTH"

        if is_numeric:
            try:
                num = float(val)
                result[key] = int(num) if num == int(num) else num
            except (ValueError, TypeError):
                result[key] = val
        else:
            result[key] = val

    return result