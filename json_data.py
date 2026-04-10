#!/usr/bin/env python
# coding: utf-8
# json_data.py ── Data Definitions & Payload Construction (macOS Optimized)
"""
JSON field definitions for each payment type and the payload builder.
Includes sanitization logic for cross-platform clipboard data.
"""

from typing import Dict, List, Any, Tuple

# ── Field Definitions ──────────────────────────────────────────────────────────
# Format: (key, UI_label, default_value, is_numeric)
JSON_FIELDS: Dict[str, List[Tuple[str, str, str, bool]]] = {
    "Beyonic": [
        ("BeyonicWallet", "Beyonic Wallet", "KUZA",        False),
        ("BeyonicTxnId",  "Beyonic Txn Id",  "",            False),
        ("Name",          "Customer Name",   "",            False),
        ("PhoneNumber",   "Phone Number",    "+256",        False),
        ("Amount",        "Amount",          "",            True),
        ("Network",       "Network Provider","MTN Uganda",  False),
        ("NetworkTxnId",  "Network Txn Id",  "",            False),
        ("PaymentDate",   "Payment Date",    "",            False),
    ],
    "Airtel": [
        ("creationDate",               "Creation Date",               "",             False),
        ("agentAssignmentDateTime",    "Agent Assignment Time",       "",             False),
        ("customerReferenceNumber",    "Customer Ref Number",         "256",          False),
        ("transactionId",              "Transaction Id",              "",             False),
        ("customerReferenceType",      "Reference Type",              "PHONE_NUMBER", False),
        ("paymentAmount",              "Payment Amount",              "",             True),
        ("paymentTransactionDateTime", "Payment Trans Time",          "",             False),
        ("senderPhoneNumber",          "Sender Phone Number",         "256",          False),
    ],
    "Bank": [
        ("name",           "Institution Name", "FOURTH", False),
        ("amount",         "Amount (UGX)",     "",       False),
        ("transactionId",  "Transaction Id",   "S",      False),
        ("billRefNumber",  "Bill Ref Number",  "256",    False),
        ("countryCode",    "Country Code",     "UG",     False),
        ("completionDate", "Completion Date",  "",       False),
        ("mobile",         "Mobile Number",    "256",    False),
        ("loanAccountId",  "Loan Account Id",  "",       False),
    ],
    "Flexipay": [
        ("name",           "Institution Name", "FOURTH", False),
        ("amount",         "Amount (UGX)",     "",       False),
        ("transactionId",  "Transaction Id",   "3000",   False),
        ("billRefNumber",  "Bill Ref Number",  "256",    False),
        ("countryCode",    "Country Code",     "UG",     False),
        ("completionDate", "Completion Date",  "",       False),
        ("mobile",         "Mobile Number",    "256",    False),
        ("loanAccountId",  "Loan Account Id",  "",       False),
    ],
}

# ── Hint text shown below each field in the UI ────────────────────────────────
JSON_HINTS: Dict[str, Dict[str, str]] = {
    "Beyonic": {
        "BeyonicTxnId": "e.g. T91592568",
        "PhoneNumber":  "e.g. +256753890912",
        "Amount":       "numeric e.g. 126500",
        "PaymentDate":  "e.g. Feb 27, 2026 10:03",
        "NetworkTxnId": "e.g. 141693582907",
    },
    "Airtel": {
        "creationDate":               "ISO Format: 2026-03-21T11:39:23Z",
        "agentAssignmentDateTime":    "ISO Format: 2026-03-21T11:39:23Z",
        "customerReferenceNumber":    "e.g. 256702987351",
        "transactionId":              "e.g. 143363767927",
        "paymentAmount":              "numeric e.g. 32000",
        "paymentTransactionDateTime": "ISO Format: 2026-03-21T11:39:23Z",
        "senderPhoneNumber":          "e.g. 256702987351",
    },
    "Bank": {
        "amount":        "e.g. 651000.00",
        "transactionId": "Must start with S e.g. S34111201",
        "billRefNumber": "e.g. 256774718807",
        "completionDate":"YYYY-MM-DD e.g. 2026-03-20",
        "mobile":        "e.g. 256774718807",
        "loanAccountId": "UUID format e.g. 401d0a03-419f...",
    },
    "Flexipay": {
        "amount":        "e.g. 1140000",
        "transactionId": "Must start with 3000 e.g. 300066833232",
        "billRefNumber": "e.g. 256759762086",
        "completionDate":"YYYY-MM-DD e.g. 2026-03-04",
        "mobile":        "e.g. 256759762086",
        "loanAccountId": "UUID format e.g. 233ea078-1250...",
    },
}

# ── Payload builder ────────────────────────────────────────────────────────────

def build_json_payload(json_type: str, values_dict: Dict[str, str]) -> Dict[str, Any]:
    """
    Constructs a clean dictionary with correct types.
    macOS Fix: Sanitizes clipboard junk like non-breaking spaces.
    """
    result = {}
    
    if json_type not in JSON_FIELDS:
        return result

    for key, _label, _default, is_numeric in JSON_FIELDS[json_type]:
        # Get raw value, strip whitespace and non-breaking spaces
        raw_val = values_dict.get(key, "").strip().replace('\xa0', ' ')
        
        # Enforce specific business logic rules
        final_val = raw_val
        
        # 1. TransactionId Prefix Enforcement
        if key == "transactionId" and final_val:
            if json_type == "Bank" and not final_val.upper().startswith("S"):
                final_val = "S" + final_val
            elif json_type == "Flexipay" and not final_val.startswith("3000"):
                final_val = "3000" + final_val

        # 2. Constant Field Enforcement
        if key == "name" and json_type in ("Bank", "Flexipay"):
            final_val = "FOURTH"

        # 3. Type Conversion
        if is_numeric:
            try:
                # Handle cases with commas or spaces in numbers
                clean_num = final_val.replace(",", "").replace(" ", "")
                num = float(clean_num)
                # Convert to int if it's a whole number, else keep float
                result[key] = int(num) if num == int(num) else num
            except (ValueError, TypeError):
                result[key] = final_val
        else:
            result[key] = final_val

    return result