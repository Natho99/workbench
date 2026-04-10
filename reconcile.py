#!/usr/bin/env python
# coding: utf-8
# reconcile.py ── Data Matching Logic (macOS & Cross-Platform Optimized)
# ════════════════════════════════════════════════════════════════════════

import pandas as pd

def perform_reconciliation(mpesa_df, shujaa_df, m_col, s_col):
    """
    Compares two dataframes based on unique transaction identifiers.
    Returns:
        diff_shujaa: Rows found in Shujaa but missing from M-Pesa.
        diff_mpesa:  Rows found in M-Pesa but missing from Shujaa.
    """
    
    # Safety Check: If either dataframe is None or empty, return empty results
    if mpesa_df is None or mpesa_df.empty:
        return shujaa_df.copy() if shujaa_df is not None else pd.DataFrame(), pd.DataFrame()
    if shujaa_df is None or shujaa_df.empty:
        return pd.DataFrame(), mpesa_df.copy()

    # 1. Clean M-Pesa IDs
    # - Cast to string
    # - Strip whitespace
    # - Remove hidden carriage returns (common in Windows-to-Mac file transfers)
    # - Convert to Uppercase for case-insensitive matching
    mpesa_df[m_col] = (mpesa_df[m_col]
                       .astype(str)
                       .str.strip()
                       .str.replace('\r', '', regex=False)
                       .str.upper())

    # 2. Clean Shujaa IDs
    shujaa_df[s_col] = (shujaa_df[s_col]
                        .astype(str)
                        .str.strip()
                        .str.replace('\r', '', regex=False)
                        .str.upper())

    # 3. Create Unique Sets for high-speed comparison
    m_ids = set(mpesa_df[m_col].unique())
    s_ids = set(shujaa_df[s_col].unique())

    # 4. Identification Logic
    
    # "The Shujaa Gaps": IDs present in Shujaa that do NOT appear in M-Pesa
    # (~ is the 'NOT' operator in pandas)
    diff_shujaa = shujaa_df[~shujaa_df[s_col].isin(m_ids)].copy()
    
    # "The M-Pesa Gaps": IDs present in M-Pesa that do NOT appear in Shujaa
    diff_mpesa = mpesa_df[~mpesa_df[m_col].isin(s_ids)].copy()

    # 5. Clean up indices for the UI Treeview display
    diff_shujaa.reset_index(drop=True, inplace=True)
    diff_mpesa.reset_index(drop=True, inplace=True)

    return diff_shujaa, diff_mpesa

if __name__ == "__main__":
    # Small test case
    d1 = pd.DataFrame({ 'M_ID': ['A1', 'B2', 'C3'] })
    d2 = pd.DataFrame({ 'S_ID': ['B2', 'C3', 'D4'] })
    
    s_gaps, m_gaps = perform_reconciliation(d1, d2, 'M_ID', 'S_ID')
    print("In Shujaa not Mpesa (Should be D4):")
    print(s_gaps)
    print("\nIn Mpesa not Shujaa (Should be A1):")
    print(m_gaps)