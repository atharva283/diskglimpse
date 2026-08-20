from __future__ import annotations
"""
reporter.py — Rich terminal output: tables, bars, progress, colors.
All display-only. No filesystem modifications.
"""
import sys
import os
import time
from datetime import datetime
from typing import Optional

from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn, MofNCompleteColumn, Progress, SpinnerColumn,
    TextColumn, TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text
from rich import print as rprint
from rich.columns import Columns
from rich.rule import Rule
from rich.style import Style
from rich.padding import Padding

from config import human_size
from scanner import ScanStats, FileEntry
from analyzer import DuplicateGroup

console = Console(force_terminal=True, highlight=False)

# ─────────────────────────────────────────────
# COLOR PALETTE
# ─────────────────────────────────────────────
C_TITLE   = "bold cyan"
C_HEAD    = "bold white"
C_PATH    = "bright_blue"
C_SIZE    = "bright_green"
C_WARN    = "yellow"
C_ERR     = "red"
C_DIM     = "dim white"
C_ACCENT  = "magenta"
C_GOOD    = "green"
C_BAR_FG  = "cyan"


# ─────────────────────────────────────────────
# BANNER
# ─────────────────────────────────────────────
def print_banner(version: str = "1.0.0") -> None:
    banner = Text()
    banner.append("\n  ================================================\n", style="bold cyan")
    banner.append("       C Drive Disk Analyzer\n", style="bold white")
    banner.append(f"       Version {version}  |  Read-Only  |  Safe  |  Fast\n", style="bold cyan")
    banner.append("  ================================================\n", style="bold cyan")
    console.print(Panel(banner, border_style="cyan", padding=(0, 2)))


# ─────────────────────────────────────────────
# PROGRESS BAR (returned as context manager)
# ─────────────────────────────────────────────
def make_progress() -> Progress:
    return Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[cyan]Scanning[/cyan] {task.description}"),
        BarColumn(bar_width=40, style="cyan", complete_style="bright_cyan"),
        TextColumn("[bright_green]{task.fields[files]:>8,}[/bright_green] files"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )


# ─────────────────────────────────────────────
# DRIVE OVERVIEW
# ─────────────────────────────────────────────
def print_drive_overview(
    drive: str,
    total_bytes: int,
    used_bytes: int,
    free_bytes: int,
    scanned_bytes: int,
    stats: ScanStats,
) -> None:
    used_pct  = (used_bytes / total_bytes * 100) if total_bytes else 0
    bar_len   = 50
    filled    = int(bar_len * used_pct / 100)
    bar       = "#" * filled + "-" * (bar_len - filled)

    if used_pct >= 90:
        bar_color = "red"
    elif used_pct >= 70:
        bar_color = "yellow"
    else:
        bar_color = "bright_green"

    console.print(Rule(f"[{C_TITLE}] Drive Overview: {drive} [/]", style="cyan"))

    table = Table(box=box.ROUNDED, border_style="cyan", show_header=False, padding=(0, 2))
    table.add_column("Label", style=C_HEAD, width=20)
    table.add_column("Value", style=C_SIZE)

    table.add_row("Total Capacity",  human_size(total_bytes))
    table.add_row("Used Space",      f"{human_size(used_bytes)}  ({used_pct:.1f}%)")
    table.add_row("Free Space",      human_size(free_bytes))
    table.add_row("Scanned (visible)", human_size(scanned_bytes))
    table.add_row("Files Found",     f"{stats.files_found:,}")
    table.add_row("Folders Scanned", f"{stats.dirs_found:,}")
    table.add_row("Scan Time",       f"{stats.elapsed_sec:.1f}s")
    table.add_row("Errors Skipped",  f"{stats.errors_skipped}")

    console.print(table)

    # Visual bar
    bar_text = Text()
    bar_text.append("  [", style="dim")
    bar_text.append(bar, style=bar_color)
    bar_text.append(" ]", style="dim")
    bar_text.append(f"  {used_pct:.1f}% used", style=bar_color)
    console.print(bar_text)
    console.print()


# ─────────────────────────────────────────────
# TOP FILES TABLE
# ─────────────────────────────────────────────
def print_top_files(files: list[FileEntry], n: int = 15) -> None:
    console.print(Rule(f"[{C_TITLE}] Top {n} Largest Files [/]", style="cyan"))

    table = Table(box=box.ROUNDED, border_style="blue", show_lines=False)
    table.add_column("#",    style="dim", width=4, justify="right")
    table.add_column("Size", style=C_SIZE, width=12, justify="right")
    table.add_column("Type", style=C_ACCENT, width=8)
    table.add_column("Path", style=C_PATH, no_wrap=False)

    for i, f in enumerate(files[:n], 1):
        ext  = f.ext if f.ext else "—"
        table.add_row(str(i), human_size(f.size), ext, f.path)

    console.print(table)
    console.print()


# ─────────────────────────────────────────────
# TOP FOLDERS TABLE
# ─────────────────────────────────────────────
def print_top_folders(folders: list[tuple[str, int]], n: int = 15, total_bytes: int = 1) -> None:
    console.print(Rule(f"[{C_TITLE}] Top {n} Largest Folders [/]", style="cyan"))

    table = Table(box=box.ROUNDED, border_style="blue", show_lines=False)
    table.add_column("#",       style="dim", width=4, justify="right")
    table.add_column("Size",    style=C_SIZE, width=12, justify="right")
    table.add_column("% Drive", style=C_WARN, width=8, justify="right")
    table.add_column("Bar",     width=22)
    table.add_column("Path",    style=C_PATH, no_wrap=False)

    for i, (path, size) in enumerate(folders[:n], 1):
        pct     = (size / total_bytes * 100) if total_bytes else 0
        bar_len = int(pct / 5)     # max 20 chars = 100%
        bar     = "|" * bar_len + "." * (20 - bar_len)
        table.add_row(str(i), human_size(size), f"{pct:.1f}%", f"[cyan]{bar}[/cyan]", path)

    console.print(table)
    console.print()


# ─────────────────────────────────────────────
# FILE TYPE BREAKDOWN
# ─────────────────────────────────────────────
def print_file_types(data: list[tuple[str, int, int]], limit: int = 20) -> None:
    console.print(Rule(f"[{C_TITLE}] File Type Breakdown (Top {limit}) [/]", style="cyan"))

    table = Table(box=box.ROUNDED, border_style="blue")
    table.add_column("Extension", style=C_ACCENT, width=12)
    table.add_column("Count",     style=C_HEAD, width=10, justify="right")
    table.add_column("Total Size",style=C_SIZE, width=14, justify="right")

    for ext, count, size in data[:limit]:
        table.add_row(ext, f"{count:,}", human_size(size))

    console.print(table)
    console.print()


# ─────────────────────────────────────────────
# CATEGORY BREAKDOWN
# ─────────────────────────────────────────────
def print_category_breakdown(data: list[tuple[str, int, int]], total_bytes: int = 1) -> None:
    console.print(Rule(f"[{C_TITLE}] Category Summary [/]", style="cyan"))

    table = Table(box=box.ROUNDED, border_style="blue")
    table.add_column("Category", style=C_ACCENT, width=14)
    table.add_column("Files",    style=C_HEAD, width=10, justify="right")
    table.add_column("Size",     style=C_SIZE, width=14, justify="right")
    table.add_column("% Total",  style=C_WARN, width=8, justify="right")
    table.add_column("Bar",      width=24)

    for cat, count, size in data:
        pct     = (size / total_bytes * 100) if total_bytes else 0
        bar_len = int(pct / 5)
        bar     = "|" * bar_len + "." * (20 - bar_len)
        table.add_row(cat, f"{count:,}", human_size(size), f"{pct:.1f}%", f"[magenta]{bar}[/magenta]")

    console.print(table)
    console.print()


# ─────────────────────────────────────────────
# OLD FILES
# ─────────────────────────────────────────────
def print_old_files(files: list[FileEntry], days: int, n: int = 20) -> None:
    console.print(Rule(f"[{C_TITLE}] Files Not Modified in {days}+ Days (Top {n}) [/]", style="cyan"))

    if not files:
        console.print(f"  [dim]No files older than {days} days found.[/dim]\n")
        return

    table = Table(box=box.ROUNDED, border_style="blue")
    table.add_column("#",            style="dim", width=4, justify="right")
    table.add_column("Size",         style=C_SIZE, width=12, justify="right")
    table.add_column("Last Modified",style=C_WARN, width=18)
    table.add_column("Path",         style=C_PATH, no_wrap=False)

    for i, f in enumerate(files[:n], 1):
        dt = datetime.fromtimestamp(f.mtime).strftime("%Y-%m-%d")
        table.add_row(str(i), human_size(f.size), dt, f.path)

    console.print(table)
    console.print()


# ─────────────────────────────────────────────
# DUPLICATES
# ─────────────────────────────────────────────
def print_duplicates(groups: list[DuplicateGroup], n: int = 10) -> None:
    console.print(Rule(f"[{C_TITLE}] Potential Duplicate Files (Top {n} Groups) [/]", style="cyan"))

    if not groups:
        console.print("  [dim]No duplicates found (by name + size).[/dim]\n")
        return

    console.print(f"  [dim]Detection: same filename + same size. No file content read.[/dim]\n")

    for i, group in enumerate(groups[:n], 1):
        wasted = group.size * (len(group.paths) - 1)
        console.print(
            f"  [bold]{i}.[/bold] "
            f"[{C_ACCENT}]{os.path.basename(group.paths[0])}[/]  "
            f"[{C_SIZE}]{human_size(group.size)} × {len(group.paths)} copies[/]  "
            f"[{C_WARN}]~{human_size(wasted)} wasted[/]"
        )
        for p in group.paths:
            console.print(f"       [{C_PATH}]{p}[/]")
        console.print()


# ─────────────────────────────────────────────
# TEMP / LOG SUGGESTIONS  (read-only: just display)
# ─────────────────────────────────────────────
def print_cleanup_suggestions(
    temp_data: dict[str, int],
    log_files: list[FileEntry],
    downloads_size: int,
    recycle_size: int,
) -> None:
    console.print(Rule(f"[{C_TITLE}] Cleanup Suggestions (Read-Only — No Files Deleted) [/]", style="cyan"))
    console.print("  [dim]These are suggestions only. Use Windows Disk Cleanup or Storage Sense to act.[/dim]\n")

    table = Table(box=box.ROUNDED, border_style="yellow", show_header=False, padding=(0, 2))
    table.add_column("Item", style=C_WARN, width=38)
    table.add_column("Size", style=C_SIZE, width=14, justify="right")
    table.add_column("Action", style=C_DIM)

    if temp_data:
        total_temp = sum(temp_data.values())
        table.add_row("Temp / Cache folders", human_size(total_temp),
                      "Settings → Storage → Temp files")

    if log_files:
        total_log = sum(f.size for f in log_files)
        table.add_row(f"Old .log files (30+ days old)", human_size(total_log),
                      "Review and delete manually")

    if downloads_size:
        table.add_row("Downloads folder", human_size(downloads_size),
                      "Review C:\\Users\\*\\Downloads")

    if recycle_size:
        table.add_row("Recycle Bin", human_size(recycle_size),
                      "Empty Recycle Bin")

    console.print(table)
    console.print()


# ─────────────────────────────────────────────
# SCAN SUMMARY FOOTER
# ─────────────────────────────────────────────
def print_scan_summary(stats: ScanStats) -> None:
    console.print(Rule(style="dim"))
    console.print(
        f"  [{C_GOOD}][OK][/] Scan complete in [bold]{stats.elapsed_sec:.1f}s[/bold]  |  "
        f"[{C_SIZE}]{stats.files_found:,}[/] files  |  "
        f"[{C_HEAD}]{stats.dirs_found:,}[/] folders  |  "
        f"[{C_WARN}]{stats.errors_skipped}[/] paths skipped (permission/locked)\n"
    )


# ─────────────────────────────────────────────
# SKIPPED PATHS LOG
# ─────────────────────────────────────────────
def print_skipped_paths(skipped: list[str], verbose: bool = False) -> None:
    if not skipped or not verbose:
        return
    console.print(Rule(f"[{C_WARN}] Skipped Paths (Permission / Locked) [/]", style="yellow"))
    for p in skipped[:50]:
        console.print(f"  [dim]{p}[/dim]")
    if len(skipped) > 50:
        console.print(f"  [dim]... and {len(skipped) - 50} more[/dim]")
    console.print()
