"""
config.py — Restricted folders, skip logic, and tool constants.
ALL skip decisions are centralized here. No delete logic anywhere.
"""

import os
import stat
from pathlib import Path

# ─────────────────────────────────────────────
# TOOL CONSTANTS
# ─────────────────────────────────────────────
TOOL_NAME    = "C Drive Disk Analyzer"
TOOL_VERSION = "1.0.0"
DEFAULT_TOP_N        = 15
DEFAULT_DEPTH        = None        # None = unlimited
DEFAULT_MIN_SIZE     = 0           # bytes
PROGRESS_BATCH_SIZE  = 500         # UI update every N files

# ─────────────────────────────────────────────
# SIZE HELPERS
# ─────────────────────────────────────────────
def parse_size(size_str: str) -> int:
    """Convert '100MB', '2GB', '500KB' -> bytes."""
    if not size_str:
        return 0
    s = size_str.strip().upper()
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    for unit, mul in sorted(units.items(), key=lambda x: -len(x[0])):
        if s.endswith(unit):
            try:
                return int(float(s[:-len(unit)]) * mul)
            except ValueError:
                raise ValueError(f"Invalid size format: '{size_str}'. Use e.g. 100MB, 2GB")
    try:
        return int(s)
    except ValueError:
        raise ValueError(f"Invalid size format: '{size_str}'")


def human_size(num_bytes: int) -> str:
    """Return human-readable size string."""
    if num_bytes < 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:,.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:,.1f} PB"


# ─────────────────────────────────────────────
# CATEGORY 1 — Root-level FOLDER names to skip
# (case-insensitive match on folder name only)
# ─────────────────────────────────────────────
SKIP_ROOT_NAMES = {
    "$recycle.bin",
    "$sysreset",
    "$winreagent",
    "$windows.~bt",
    "$windows.~ws",
    "$getcurrent",
    "system volume information",
    "recovery",
    "onedrivetemp",
    "config.msi",
    "msocache",
    "boot",
    "documents and settings",   # junction → C:\Users
}

# ─────────────────────────────────────────────
# CATEGORY 2 — Root-level LOCKED FILES to skip
# ─────────────────────────────────────────────
SKIP_ROOT_FILES = {
    "hiberfil.sys",
    "pagefile.sys",
    "swapfile.sys",
    "dumpstack.log.tmp",
    "dumpstack.log",
    "bootmgr",
    "bootsect.bak",
}

# ─────────────────────────────────────────────
# CATEGORY 3 — Absolute paths (normalized lowercase)
# Matched with os.path.normcase for case-insensitivity
# ─────────────────────────────────────────────
_SKIP_ABSOLUTE_RAW = [
    # Windows core
    r"C:\Windows\System32",
    r"C:\Windows\SysWOW64",
    r"C:\Windows\WinSxS",
    r"C:\Windows\Installer",
    r"C:\Windows\ServiceProfiles",
    r"C:\Windows\CSC",
    r"C:\Windows\assembly",
    r"C:\Windows\Microsoft.NET",
    r"C:\Windows\SoftwareDistribution\Download",
    # ProgramData junctions
    r"C:\ProgramData\Application Data",
    r"C:\ProgramData\Desktop",
    r"C:\ProgramData\Documents",
    r"C:\ProgramData\Start Menu",
    r"C:\ProgramData\Templates",
    r"C:\ProgramData\Microsoft\Windows Defender",
    r"C:\ProgramData\Microsoft\Windows Defender Advanced Threat Protection",
    # Users top-level junctions
    r"C:\Users\All Users",
    r"C:\Users\Default User",
]

SKIP_ABSOLUTE: set = {os.path.normcase(p) for p in _SKIP_ABSOLUTE_RAW}


# ─────────────────────────────────────────────
# CATEGORY 4 — Per-user junction FOLDER NAMES
# These appear inside every user profile AND Default/Public
# ─────────────────────────────────────────────
SKIP_USER_JUNCTION_NAMES = {
    "application data",
    "cookies",
    "local settings",
    "my documents",
    "nethood",
    "printhood",
    "recent",
    "sendto",
    "start menu",
    "templates",
}

# Inside Documents/ of every user
SKIP_DOCUMENTS_JUNCTION_NAMES = {
    "my music",
    "my pictures",
    "my videos",
}

# OneDrive and CrossDevice — entire subtree skipped
SKIP_SUBTREE_NAMES = {
    "onedrive",
    "crossdevice",
}


# ─────────────────────────────────────────────
# REPARSE POINT DETECTION  (Layer 1 — primary)
# ─────────────────────────────────────────────
FILE_ATTRIBUTE_REPARSE_POINT = 0x400

def is_reparse_point(entry: os.DirEntry) -> bool:
    """
    Returns True if entry is a junction, symlink, or any ReparsePoint.
    Uses cached DirEntry attributes — no extra syscall needed.
    Works on Python 3.8+.
    """
    # Fast path: symlink check (cached in DirEntry)
    try:
        if entry.is_symlink():
            return True
    except OSError:
        return True

    # Python 3.12+ has entry.is_junction()
    try:
        if hasattr(entry, "is_junction") and entry.is_junction():
            return True
    except OSError:
        return True

    # Fallback: check FILE_ATTRIBUTE_REPARSE_POINT flag
    try:
        st = entry.stat(follow_symlinks=False)
        fa = getattr(st, "st_file_attributes", 0)
        return bool(fa & FILE_ATTRIBUTE_REPARSE_POINT)
    except (PermissionError, OSError):
        return True   # Can't stat → treat as skip


def should_skip(entry: os.DirEntry, parent_path: str) -> bool:
    """
    Master skip decision. Checked in cheapest-first order:
      1. Name-based checks (O(1) dict lookup, no syscall)
      2. Absolute path check (O(1) dict lookup)
      3. ReparsePoint / symlink / junction (uses DirEntry cache)
    Returns True if this entry should be SKIPPED entirely.
    """
    name_lower = entry.name.lower()
    path_norm  = os.path.normcase(entry.path)

    # ── 1. Root-level special names ────────────────────
    parent_norm = os.path.normcase(parent_path)
    if parent_norm == os.path.normcase("C:\\"):
        if entry.is_dir(follow_symlinks=False):
            if name_lower in SKIP_ROOT_NAMES:
                return True
        else:
            if name_lower in SKIP_ROOT_FILES:
                return True

    # ── 2. Absolute path blacklist ──────────────────────
    if path_norm in SKIP_ABSOLUTE:
        return True

    # ── 3. Per-user junction names ──────────────────────
    if entry.is_dir(follow_symlinks=False):
        if name_lower in SKIP_USER_JUNCTION_NAMES:
            return True
        if name_lower in SKIP_DOCUMENTS_JUNCTION_NAMES:
            return True
        if name_lower in SKIP_SUBTREE_NAMES:
            return True

    # ── 4. ReparsePoint auto-detect (catches all junctions/symlinks) ──
    if is_reparse_point(entry):
        return True

    return False
