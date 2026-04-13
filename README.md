# 4G Workbench — CSV Payment Reconciliation Tool

A desktop application for editing and reconciling CSV payment files, built for both Windows and macOS.

---

## What It Does

4G Workbench is a payment reconciliation tool that lets you load, edit, and process CSV files to match and verify payment records. It is designed for finance and operations teams who need a reliable, offline desktop tool for reconciliation workflows.

---

## Features

- Load and edit CSV payment files
- Reconcile payment records across multiple sources
- Flag mismatches and discrepancies
- Export cleaned and reconciled CSV output
- Settings management for custom reconciliation rules
- JSON data support for extended workflows
- Cross-platform: works on Windows and macOS

---

## Supported Platforms

| Platform | Status |
|----------|--------|
| Windows 10 / 11 | ✅ Supported |
| macOS (Intel & Apple Silicon) | ✅ Supported |

---

## Installation

### Windows

1. Download the installer from the `Installer/` folder or the releases page.
2. Run the `.exe` installer and follow the on-screen steps.
3. Launch **4G Workbench** from the Start Menu or desktop shortcut.

### macOS

1. Download the `.dmg` or `.pkg` file from the releases page.
2. Open the installer and drag the app to your **Applications** folder.
3. On first launch, right-click the app and select **Open** to bypass Gatekeeper if prompted.

---

## Getting Started

1. Open the application.
2. Go to the **CSV** tab and load your payment CSV file.
3. Review and edit records in the table view.
4. Switch to the **Reconcile** tab to run the reconciliation process.
5. Review flagged discrepancies and resolve them manually or automatically.
6. Export the final reconciled CSV file.


---

## Requirements

No additional software is required. The installer bundles all dependencies.

For development, the app is built with Python and packaged using PyInstaller.

---

## License

See `LICENSE.txt` for full terms.

---

## Notes

Before installing, please read `Before You Install.txt` for any pre-installation requirements or known issues on your platform.