# DiskGlimpse 🚀

A blazing fast, memory-efficient Windows disk space analyzer with an interactive TUI. Built for power users, developers, and system administrators who prefer the terminal.

It analyzes ANY drive (`C:\`, `D:\`, etc.) or specific folder, identifies the largest files and directories, detects junk/cache with smart heuristics, and offers a **safe, user-controlled cleanup** — all without ever touching your system files automatically.

## 📸 Screenshots

![Interactive Menu](menu.png)

![Scan in Progress](scan.png)

![Report View](report.png)

---

## 🌟 Key Features

- **Smart Junk Detection:** Automatically identifies Developer Cache (`node_modules`, `__pycache__`, `venv`, `build`, `dist`, etc.) and System Junk (`Temp`, `.log`, `.tmp`, browser caches). Flags them for review — never deletes anything automatically.
- **Safe, User-Controlled Cleanup:** After scanning, you get an interactive checkbox menu to **manually select** which flagged items to delete. A final `⚠️ Are you sure?` confirmation (default: No) is always shown before anything is removed.
- **Zero-Crash Engineering:** Safely skips Windows locked files, protected system folders (`System Volume Information`, `$RECYCLE.BIN`), and infinite junction/symlink loops (ReparsePoints) that typically crash Python scripts.
- **Memory Efficient:** Uses Breadth-First Search (BFS) with Generators. Scans millions of files without loading them all into RAM.
- **Blazing Fast:** Leverages `os.scandir()` with cached `DirEntry` attributes to minimize expensive OS-level kernel calls.
- **Interactive TUI:** Real-time progress bar, drill-down directory navigation, and a beautiful summary table — all in your terminal.
- **Flexible CLI:** Use flags for scripting and automation — filter by size, extension, depth, and more.
- **Export Reports:** Export your scan results to `JSON` or `CSV`.

---

## 📥 Quick Start (No Installation Required)

Download and run the standalone Windows executable — no Python needed!

1. Go to the [Releases](https://github.com/atharva283/diskglimpse/releases/latest) page.
2. Download `disk-analyzer-cli.exe`.
3. Open PowerShell in the same folder and run:

```powershell
.\disk-analyzer-cli.exe C:\ --interactive
```

---

## 👨‍💻 For Developers (Run from Source)

### Requirements
- Python **3.9+**
- Windows (designed and tested for Windows; BFS skip-list targets Windows system paths)

### Install

```bash
git clone https://github.com/atharva283/diskglimpse.git
cd diskglimpse
pip install .
```

Or install in editable/developer mode with dev tools (PyInstaller, pytest, black, ruff):

```bash
pip install -e ".[dev]"
```

### Run

```bash
python main.py C:\ --interactive
```

---

## 🎮 Usage

### Interactive Mode (Recommended)

Launch the full TUI with drill-down navigation and junk cleanup:

```bash
python main.py C:\ --interactive
```

```bash
# Scan a specific folder interactively
python main.py D:\Projects --interactive

# Scan only 3 levels deep (much faster on large drives)
python main.py C:\ --interactive --max-depth 3

# Include hidden files and folders
python main.py C:\ --interactive --include-hidden

# Enable junk detection panel
python main.py C:\ --interactive --detect-junk
```

### CLI / Automation Mode

Run without `--interactive` for plain output — great for scripts:

```bash
# Scan D:\ and show top 10 largest items
python main.py D:\ --top 10

# Filter: only show files larger than 500MB
python main.py C:\ --min-size 500MB

# Filter: only .mp4 files larger than 1GB
python main.py D:\Videos --ext .mp4 --min-size 1GB

# Filter by filename pattern
python main.py C:\Users --pattern "*.log"

# Export scan results to JSON and CSV
python main.py C:\ --export-json report.json --export-csv report.csv

# Combine: deep scan, verbose, export
python main.py C:\ --max-depth 5 --detect-junk --export-json scan.json --verbose
```

### All Available Flags

| Flag | Default | Description |
|---|---|---|
| `path` | `C:\` | Target drive or directory to scan |
| `--interactive`, `-i` | off | Launch full interactive TUI mode |
| `--max-depth N` | unlimited | Maximum directory depth to traverse |
| `--min-size SIZE` | none | Minimum file size filter (e.g. `1KB`, `50MB`, `2GB`) |
| `--max-size SIZE` | none | Maximum file size filter |
| `--ext .EXT` | none | Filter by extension (repeatable: `--ext .mp4 --ext .mkv`) |
| `--pattern PATTERN` | none | Filter by filename glob pattern (e.g. `*.log`) |
| `--include-hidden` | off | Include hidden files and folders |
| `--detect-junk` | off | Enable smart junk detection panel |
| `--top N` | `20` | Number of top items to show in summary table |
| `--export-json PATH` | none | Export results to a JSON file |
| `--export-csv PATH` | none | Export results to a CSV file |
| `-v`, `--verbose` | off | Print full tracebacks on errors |
| `--version` | — | Show version and exit |

---

## 🗑️ How the Cleanup Feature Works

DiskGlimpse includes an **opt-in, user-controlled** cleanup flow — nothing is ever deleted automatically.

**The 4-layer safety process:**

```
1. junk_detector.py   →  Scans results and ONLY flags potential junk (never deletes)
2. Checkbox Menu      →  YOU manually select which flagged items to include
3. Confirmation Prompt →  "⚠️ Are you sure?" shown with item list (default answer: No)
4. Deletion           →  Only executes if you explicitly confirm Yes
```

**What gets flagged as junk:**

| Category | Examples |
|---|---|
| Developer Cache | `node_modules`, `__pycache__`, `venv`, `.venv`, `env`, `build`, `dist`, `.pytest_cache`, `.gradle`, `target` |
| System Junk | `Temp`, `tmp`, `Cache`, browser caches (Chrome/Edge/Firefox), `.log`, `.tmp`, `.bak` files |

> **Note:** System-critical directories (`System Volume Information`, `$RECYCLE.BIN`, `ProgramData`, `AppData`, `Windows.old`) are **never scanned** — they are silently skipped at the BFS engine level.

---

## 🛠️ Build Standalone EXE

To build `disk-analyzer-cli.exe` yourself using PyInstaller:

```bash
pip install -e ".[dev]"
pyinstaller disk-analyzer-cli.spec
```

The `.exe` will appear in the `dist/` folder. See [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) for full details.

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.9+ |
| TUI / Tables | [`rich`](https://github.com/Textualize/rich) ≥ 13.0 |
| Interactive Menus | [`questionary`](https://github.com/tmbo/questionary) ≥ 2.0 |
| Packaging | `pyproject.toml` (PEP 517/518, setuptools) |
| CI/CD | GitHub Actions — auto-builds Windows `.exe` on every release tag |
| Scan Engine | Iterative BFS with `os.scandir()` + `DirEntry` cached attributes |

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
