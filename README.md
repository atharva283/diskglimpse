# Disk Analyzer CLI 🚀

A blazing fast, memory-efficient, and **strictly read-only** disk space analyzer for Windows. Built for power users, developers, and system administrators who prefer the terminal.

It analyzes ANY drive (C:\, D:\, etc.) or specific folder, identifies massive files, highlights old/duplicate files, and suggests cleanup actions—all without ever risking your system files.

## 📸 Screenshots

![Interactive Menu](menu.png)

<img width="1920" height="569" alt="scan" src="https://github.com/user-attachments/assets/5e0e9d78-309e-4944-940c-4aefb956b0a7" />

## 🌟 Key Features

- **Safe & Read-Only:** Absolutely no `delete` or `remove` operations in the codebase. You can run this without fear of accidentally destroying system files.
- **Zero-Crash Engineering:** Safely skips Windows locked files, protected system folders (like `System Volume Information`), and infinite junction loops (ReparsePoints) that typically crash Python scripts.
- **Memory Efficient:** Uses Breadth-First Search (BFS) and Generators. Scans millions of files without eating up your RAM.
- **Blazing Fast:** Leverages `os.scandir` to minimize expensive OS-level kernel calls.
- **Interactive UI & CLI:** Run it with no arguments for a beautiful interactive menu, or use command-line flags for automation.
- **Rich Reporting:** Beautiful terminal tables showing Top Folders, File Type breakdowns, Old Files, and more.
- **Export Capabilities:** Export your reports to `JSON`, `CSV`, or `TXT`.

## 📥 Quick Start (No Installation Required)

The easiest way to use this tool is to download the standalone executable. No Python installation is needed!

1. Go to the [Releases](https://github.com/atharva283/disk-analyzer-cli/releases/latest) page.
2. Download `DiskAnalyzer.exe`.
3. Double-click to run! You will be greeted with a beautiful interactive menu.

---

## 👨‍💻 For Developers (Python Source)

If you prefer to run from source, clone the repository and install the dependencies:

```bash
git clone https://github.com/atharva283/disk-analyzer-cli.git
cd disk-analyzer-cli
pip install -r requirements.txt
```

> **Note for Windows Users:** The script automatically sets `PYTHONIOENCODING=utf-8` and enables ANSI escape sequences so the UI renders perfectly in PowerShell or CMD.

## 🎮 Usage

### 1. Interactive Mode (Recommended)
Simply run the script with no arguments. You will be greeted with an interactive, keyboard-navigable menu:
```bash
python main.py
```

### 2. Command Line Mode (For Automation)
You can bypass the interactive menu by providing specific flags:

```bash
# Full analysis of C drive (default)
python main.py

# Scan only 3 levels deep (super fast!)
python main.py --depth 3

# Show only files larger than 100MB
python main.py --min-size 100MB

# Show only the cleanup suggestions report
python main.py --mode cleanup

# Export the full report to a JSON file
python main.py --mode all --export my_report.json
```

### Available Modes (`--mode`)
- `overview`: Total disk usage, top 15 folders and files (Default).
- `filetypes`: Breakdown of space consumed by `.mp4`, `.zip`, `.py`, etc.
- `categories`: High-level summary (Video, Documents, Code, Temp).
- `oldfiles`: Files not modified in > 365 days (configurable with `--days`).
- `duplicates`: Detects potential duplicate files (based on exact name + size match).
- `cleanup`: Summarizes space taken by temp folders, logs, and downloads.
- `all`: Runs every analysis above.

## 🛠️ Tech Stack
- **Language:** Python 3.8+
- **Libraries:**
  - [`rich`](https://github.com/Textualize/rich) - For gorgeous terminal formatting, progress bars, and tables.
  - [`questionary`](https://github.com/tmbo/questionary) - For the smooth interactive CLI menu.

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
