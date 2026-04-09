# reconcile.py
import pandas as pd

def perform_reconciliation(mpesa_df, shujaa_df, m_col, s_col):
    # Ensure ref columns are treated as clean strings
    mpesa_df[m_col] = mpesa_df[m_col].astype(str).str.strip()
    shujaa_df[s_col] = shujaa_df[s_col].astype(str).str.strip()

    m_ids = set(mpesa_df[m_col].unique())
    s_ids = set(shujaa_df[s_col].unique())

    # Only in Shujaa, NOT in M-Pesa
    diff_shujaa = shujaa_df[~shujaa_df[s_col].isin(m_ids)].copy()
    
    # Only in M-Pesa, NOT in Shujaa
    diff_mpesa = mpesa_df[~mpesa_df[m_col].isin(s_ids)].copy()

    return diff_shujaa, diff_mpesa