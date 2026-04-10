import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os
import sys
from datetime import datetime

# Import the actual logic - ensure reconcile.py is in your directory
try:
    from reconcile import perform_reconciliation
except ImportError:
    # Fallback for testing UI if logic file is missing
    def perform_reconciliation(m_df, s_df, m_col, s_col):
        return pd.DataFrame(), pd.DataFrame()

class ReconcilePanel(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#FAF3E6", **kwargs)
        self.mpesa_df = None
        self.shujaa_df = None
        self.diff_shujaa = pd.DataFrame()
        self.diff_mpesa = pd.DataFrame()
        
        # Determine best font for OS
        self.base_font = "Helvetica Neue" if sys.platform == "darwin" else "Segoe UI"
        
        self._build_ui()

    def _build_ui(self):
        # Header - Descriptive name
        header_frame = tk.Frame(self, bg="#FAF3E6")
        header_frame.pack(fill="x", pady=5)
        
        tk.Label(header_frame, text="Reconciliation Engine", 
                 font=(self.base_font, 14, "bold"), bg="#FAF3E6", fg="#3a2f24").pack()

        # --- Top Control Bar ---
        ctrl_bar = tk.Frame(self, bg="#FAF3E6")
        ctrl_bar.pack(fill="x", padx=10, pady=5)

        # M-Pesa Setup
        self.mpesa_box = tk.LabelFrame(ctrl_bar, text=" M-Pesa Setup ", bg="#FAF3E6", 
                                        fg="#2e7d32", font=(self.base_font, 10, "bold"), 
                                        highlightbackground="#2e7d32", highlightthickness=1)
        self.mpesa_box.pack(side="left", fill="both", expand=True, padx=5)
        
        tk.Button(self.mpesa_box, text="📂 Upload M-Pesa", 
                  highlightbackground="#FAF3E6", command=self.load_mpesa).pack(pady=5)
        self.lbl_mpesa = tk.Label(self.mpesa_box, text="No file selected", bg="#FAF3E6", font=(self.base_font, 9))
        self.lbl_mpesa.pack()
        
        m_ref_f = tk.Frame(self.mpesa_box, bg="#FAF3E6")
        m_ref_f.pack(pady=5)
        tk.Label(m_ref_f, text="Ref Col (Transaction Code):", bg="#FAF3E6", font=(self.base_font, 9)).pack(side="left")
        self.mpesa_col_var = tk.StringVar()
        self.mpesa_dropdown = ttk.Combobox(m_ref_f, textvariable=self.mpesa_col_var, state="readonly", width=18)
        self.mpesa_dropdown.pack(side="left", padx=5)

        # Shujaa Setup
        self.shujaa_box = tk.LabelFrame(ctrl_bar, text=" Shujaa Setup ", bg="#FAF3E6", 
                                         fg="#ef6c00", font=(self.base_font, 10, "bold"),
                                         highlightbackground="#ef6c00", highlightthickness=1)
        self.shujaa_box.pack(side="left", fill="both", expand=True, padx=5)

        tk.Button(self.shujaa_box, text="📂 Upload Shujaa", 
                  highlightbackground="#FAF3E6", command=self.load_shujaa).pack(pady=5)
        self.lbl_shujaa = tk.Label(self.shujaa_box, text="No file selected", bg="#FAF3E6", font=(self.base_font, 9))
        self.lbl_shujaa.pack()

        s_ref_f = tk.Frame(self.shujaa_box, bg="#FAF3E6")
        s_ref_f.pack(pady=5)
        tk.Label(s_ref_f, text="Ref Col (Transaction Code):", bg="#FAF3E6", font=(self.base_font, 9)).pack(side="left")
        self.shujaa_col_var = tk.StringVar()
        self.shujaa_dropdown = ttk.Combobox(s_ref_f, textvariable=self.shujaa_col_var, state="readonly", width=18)
        self.shujaa_dropdown.pack(side="left", padx=5)

        # Action Execution Bar
        exec_bar = tk.Frame(self, bg="#FAF3E6")
        exec_bar.pack(fill="x", pady=10)
        
        btn_container = tk.Frame(exec_bar, bg="#FAF3E6")
        btn_container.pack(expand=True)

        tk.Button(btn_container, text="🚀 Run Reconciliation", bg="#c9a66b", fg="white", 
                  highlightbackground="#c9a66b",
                  font=(self.base_font, 10, "bold"), padx=20, command=self.run_recon).pack(side="left", padx=10)
        
        tk.Button(btn_container, text="🔄 Reset Process", bg="#d4b896", fg="#3a2f24", 
                  highlightbackground="#d4b896",
                  font=(self.base_font, 10, "bold"), padx=20, command=self.reset_process).pack(side="left", padx=10)

        # --- Two-Column Results Area ---
        results_container = tk.Frame(self, bg="#FAF3E6")
        results_container.pack(fill="both", expand=True, padx=10, pady=5)
        results_container.grid_columnconfigure(0, weight=1, uniform="group1")
        results_container.grid_columnconfigure(1, weight=1, uniform="group1")
        results_container.grid_rowconfigure(0, weight=1)

        # Left Column Frame (M-Pesa Gaps)
        self.left_col = tk.Frame(results_container, bg="#FAF3E6", bd=1, relief="ridge")
        self.left_col.grid(row=0, column=0, sticky="nsew", padx=5)
        
        l_hdr = tk.Frame(self.left_col, bg="#e8f5e9")
        l_hdr.pack(fill="x")
        self.lbl_title_mpesa = tk.Label(l_hdr, text="M-Pesa Data", font=(self.base_font, 10, "bold"), bg="#e8f5e9", fg="#2e7d32")
        self.lbl_title_mpesa.pack(side="left", padx=5)
        self.lbl_count_mpesa = tk.Label(l_hdr, text="Rows: 0", font=(self.base_font, 9, "bold"), bg="#e8f5e9")
        self.lbl_count_mpesa.pack(side="right", padx=5)
        
        self.btn_dl_mpesa = tk.Button(self.left_col, text="📥 Download M-Pesa Gaps", state="disabled", font=(self.base_font, 9),
                                      command=self.download_mpesa_gaps)
        self.btn_dl_mpesa.pack(fill="x")
        self.tree_mpesa = self._create_tree(self.left_col)

        # Right Column Frame (Shujaa Gaps)
        self.right_col = tk.Frame(results_container, bg="#FAF3E6", bd=1, relief="ridge")
        self.right_col.grid(row=0, column=1, sticky="nsew", padx=5)
        
        r_hdr = tk.Frame(self.right_col, bg="#fff3e0")
        r_hdr.pack(fill="x")
        self.lbl_title_shujaa = tk.Label(r_hdr, text="Shujaa Data", font=(self.base_font, 10, "bold"), bg="#fff3e0", fg="#ef6c00")
        self.lbl_title_shujaa.pack(side="left", padx=5)
        self.lbl_count_shujaa = tk.Label(r_hdr, text="Rows: 0", font=(self.base_font, 9, "bold"), bg="#fff3e0")
        self.lbl_count_shujaa.pack(side="right", padx=5)
        
        self.btn_dl_shujaa = tk.Button(self.right_col, text="📥 Download Shujaa Gaps", state="disabled", font=(self.base_font, 9),
                                       command=self.download_shujaa_gaps)
        self.btn_dl_shujaa.pack(fill="x")
        self.tree_shujaa = self._create_tree(self.right_col)

    def _create_tree(self, parent):
        container = tk.Frame(parent, bg="white")
        container.pack(fill="both", expand=True)
        
        # Style treeview for Mac
        style = ttk.Style()
        if sys.platform == "darwin":
            style.configure("Treeview", rowheight=25)
            
        tree = ttk.Treeview(container, show="headings")
        vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        tree.pack(side="left", fill="both", expand=True)
        return tree

    def load_mpesa(self):
        path = filedialog.askopenfilename(title="Select M-Pesa CSV", filetypes=[("CSV", "*.csv")])
        if path:
            try:
                self.mpesa_df = pd.read_csv(path)
                cols = list(self.mpesa_df.columns)
                self.mpesa_dropdown['values'] = cols
                
                # Auto-select best guess for M-Pesa reference
                target = ""
                for c in cols:
                    if "Receipt" in c or "Transaction" in c or "Code" in c:
                        target = c
                        break
                self.mpesa_col_var.set(target if target else cols[0])
                
                self.lbl_mpesa.config(text=os.path.basename(path), fg="#2e7d32")
                self._display_df(self.tree_mpesa, self.mpesa_df)
                self.lbl_count_mpesa.config(text=f"Total: {len(self.mpesa_df)}")
                self.lbl_title_mpesa.config(text="M-Pesa Statement (Loaded)")
            except Exception as e:
                messagebox.showerror("File Error", f"Could not read M-Pesa file: {str(e)}")

    def load_shujaa(self):
        path = filedialog.askopenfilename(title="Select Shujaa CSV", filetypes=[("CSV", "*.csv")])
        if path:
            try:
                self.shujaa_df = pd.read_csv(path)
                cols = list(self.shujaa_df.columns)
                self.shujaa_dropdown['values'] = cols
                
                # Auto-select best guess for Shujaa reference
                target = ""
                for c in cols:
                    if "Receipt" in c or "Transaction" in c or "External" in c:
                        target = c
                        break
                self.shujaa_col_var.set(target if target else cols[0])
                
                self.lbl_shujaa.config(text=os.path.basename(path), fg="#ef6c00")
                self._display_df(self.tree_shujaa, self.shujaa_df)
                self.lbl_count_shujaa.config(text=f"Total: {len(self.shujaa_df)}")
                self.lbl_title_shujaa.config(text="Shujaa Statement (Loaded)")
            except Exception as e:
                messagebox.showerror("File Error", f"Could not read Shujaa file: {str(e)}")

    def run_recon(self):
        if self.mpesa_df is None or self.shujaa_df is None:
            messagebox.showwarning("Warning", "Upload both statements first.")
            return
        
        m_col = self.mpesa_col_var.get()
        s_col = self.shujaa_col_var.get()
        
        if not m_col or not s_col:
            messagebox.showwarning("Warning", "Select reference columns for both files.")
            return

        try:
            self.diff_shujaa, self.diff_mpesa = perform_reconciliation(self.mpesa_df, self.shujaa_df, m_col, s_col)
            
            # Update M-Pesa Result UI
            m_gaps, m_total = len(self.diff_mpesa), len(self.mpesa_df)
            m_perc = (m_gaps / m_total * 100) if m_total > 0 else 0
            self._display_df(self.tree_mpesa, self.diff_mpesa)
            self.lbl_title_mpesa.config(text="In M-Pesa, NOT in Shujaa")
            self.lbl_count_mpesa.config(text=f"{m_gaps}/{m_total} ({m_perc:.1f}%)")
            self.btn_dl_mpesa.config(state="normal" if not self.diff_mpesa.empty else "disabled")
            
            # Update Shujaa Result UI
            s_gaps, s_total = len(self.diff_shujaa), len(self.shujaa_df)
            s_perc = (s_gaps / s_total * 100) if s_total > 0 else 0
            self._display_df(self.tree_shujaa, self.diff_shujaa)
            self.lbl_title_shujaa.config(text="In Shujaa, NOT in M-Pesa")
            self.lbl_count_shujaa.config(text=f"{s_gaps}/{s_total} ({s_perc:.1f}%)")
            self.btn_dl_shujaa.config(state="normal" if not self.diff_shujaa.empty else "disabled")
            
            messagebox.showinfo("Success", "Reconciliation complete.")
        except Exception as e:
            messagebox.showerror("Logic Error", f"Reconciliation failed: {str(e)}")

    def reset_process(self):
        self.mpesa_df = None
        self.shujaa_df = None
        self.diff_shujaa = pd.DataFrame()
        self.diff_mpesa = pd.DataFrame()
        self.lbl_mpesa.config(text="No file selected", fg="black")
        self.lbl_shujaa.config(text="No file selected", fg="black")
        self.mpesa_dropdown['values'] = []
        self.shujaa_dropdown['values'] = []
        self.mpesa_col_var.set("")
        self.shujaa_col_var.set("")
        self.tree_mpesa.delete(*self.tree_mpesa.get_children())
        self.tree_shujaa.delete(*self.tree_shujaa.get_children())
        self.lbl_count_mpesa.config(text="Rows: 0")
        self.lbl_count_shujaa.config(text="Rows: 0")
        self.lbl_title_mpesa.config(text="M-Pesa Data")
        self.lbl_title_shujaa.config(text="Shujaa Data")
        self.btn_dl_mpesa.config(state="disabled")
        self.btn_dl_shujaa.config(state="disabled")

    def _display_df(self, tree, df):
        tree.delete(*tree.get_children())
        if df.empty:
            return
            
        cols = list(df.columns)
        tree["columns"] = cols
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=130, anchor="w")
        
        # Display first 500 rows for performance
        for _, row in df.head(500).iterrows():
            tree.insert("", "end", values=[str(x) for x in list(row)])

    def download_mpesa_gaps(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        fname = f"Mpesa_Gaps_Not_In_Shujaa_{ts}"
        self.save_csv(self.diff_mpesa, fname)

    def download_shujaa_gaps(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        fname = f"Shujaa_Gaps_Not_In_Mpesa_{ts}"
        self.save_csv(self.diff_shujaa, fname)

    def save_csv(self, df, default_name):
        path = filedialog.asksaveasfilename(defaultextension=".csv", 
                                             initialfile=default_name,
                                             filetypes=[("CSV", "*.csv")])
        if path:
            df.to_csv(path, index=False)
            messagebox.showinfo("Exported", f"Saved successfully to {os.path.basename(path)}")