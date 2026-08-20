"""
analyzer.py — Pure analysis and aggregation on scan results.

All functions are read-only. Input: list[FileEntry]. Output: dicts/lists.
No filesystem operations happen here.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from scanner import FileEntry


# ─────────────────────────────────────────────
# FILE CATEGORY MAP
# ─────────────────────────────────────────────
CATEGORY_MAP: dict[str, str] = {
    # Videos
    ".mp4": "Video", ".mkv": "Video", ".avi": "Video", ".mov": "Video",
    ".wmv": "Video", ".flv": "Video", ".webm": "Video", ".m4v": "Video",
    ".mpg": "Video", ".mpeg": "Video", ".3gp": "Video", ".ts": "Video",
    # Audio
    ".mp3": "Audio", ".wav": "Audio", ".flac": "Audio", ".aac": "Audio",
    ".ogg": "Audio", ".wma": "Audio", ".m4a": "Audio", ".opus": "Audio",
    # Images
    ".jpg": "Image", ".jpeg": "Image", ".png": "Image", ".gif": "Image",
    ".bmp": "Image", ".webp": "Image", ".tiff": "Image", ".svg": "Image",
    ".heic": "Image", ".raw": "Image", ".ico": "Image",
    # Documents
    ".pdf": "Document", ".doc": "Document", ".docx": "Document",
    ".xls": "Document", ".xlsx": "Document", ".ppt": "Document",
    ".pptx": "Document", ".txt": "Document", ".odt": "Document",
    ".rtf": "Document", ".csv": "Document", ".md": "Document",
    # Archives
    ".zip": "Archive", ".rar": "Archive", ".7z": "Archive",
    ".tar": "Archive", ".gz": "Archive", ".bz2": "Archive",
    ".xz": "Archive", ".cab": "Archive", ".iso": "Archive",
    # Executables / Installers
    ".exe": "Executable", ".msi": "Executable", ".dll": "Executable",
    ".sys": "Executable", ".bat": "Executable", ".cmd": "Executable",
    ".ps1": "Executable", ".vbs": "Executable",
    # Code
    ".py": "Code", ".js": "Code", ".ts": "Code", ".java": "Code",
    ".cpp": "Code", ".c": "Code", ".cs": "Code", ".go": "Code",
    ".rs": "Code", ".php": "Code", ".rb": "Code", ".swift": "Code",
    ".html": "Code", ".css": "Code", ".json": "Code", ".xml": "Code",
    ".sql": "Code", ".sh": "Code",
    # Logs / Temp
    ".log": "Log/Temp", ".tmp": "Log/Temp", ".temp": "Log/Temp",
    ".dmp": "Log/Temp", ".bak": "Log/Temp",
    # Databases
    ".db": "Database", ".sqlite": "Database", ".sqlite3": "Database",
    ".mdf": "Database", ".ldf": "Database", ".accdb": "Database",
}

def get_category(ext: str) -> str:
    return CATEGORY_MAP.get(ext.lower(), "Other")


# ─────────────────────────────────────────────
# ANALYSIS FUNCTIONS
# ─────────────────────────────────────────────

def top_files(files: list[FileEntry], n: int = 15) -> list[FileEntry]:
    """Return top-N largest files sorted by size descending."""
    return sorted(files, key=lambda f: f.size, reverse=True)[:n]


def top_folders(files: list[FileEntry], n: int = 15) -> list[tuple[str, int]]:
    """
    Aggregate sizes by top-level folder under the root.
    Returns list of (folder_path, total_size) sorted descending.
    """
    folder_sizes: dict[str, int] = defaultdict(int)
    for f in files:
        # Use the immediate parent directory
        parent = os.path.dirname(f.path)
        folder_sizes[parent] += f.size

    # Bubble up: also attribute size to grandparent folders
    # We do a two-pass approach: raw per-directory sums first,
    # then compute cumulative sizes going up the tree.
    cumulative: dict[str, int] = defaultdict(int)
    for dir_path, size in folder_sizes.items():
        parts = dir_path.replace("/", "\\").split("\\")
        # Walk up the tree and add size to each ancestor
        for i in range(len(parts), 0, -1):
            ancestor = "\\".join(parts[:i])
            if ancestor:
                cumulative[ancestor] += size

    sorted_dirs = sorted(cumulative.items(), key=lambda x: x[1], reverse=True)
    return sorted_dirs[:n]


def file_type_breakdown(files: list[FileEntry]) -> list[tuple[str, int, int]]:
    """
    Return list of (extension, count, total_size) sorted by size descending.
    """
    ext_data: dict[str, list] = defaultdict(lambda: [0, 0])
    for f in files:
        ext = f.ext if f.ext else "(no ext)"
        ext_data[ext][0] += 1
        ext_data[ext][1] += f.size

    result = [(ext, d[0], d[1]) for ext, d in ext_data.items()]
    return sorted(result, key=lambda x: x[2], reverse=True)


def category_breakdown(files: list[FileEntry]) -> list[tuple[str, int, int]]:
    """
    Return list of (category, count, total_size) sorted by size descending.
    """
    cat_data: dict[str, list] = defaultdict(lambda: [0, 0])
    for f in files:
        cat = get_category(f.ext)
        cat_data[cat][0] += 1
        cat_data[cat][1] += f.size

    result = [(cat, d[0], d[1]) for cat, d in cat_data.items()]
    return sorted(result, key=lambda x: x[2], reverse=True)


def old_files(files: list[FileEntry], days: int = 365) -> list[FileEntry]:
    """Return files not modified in `days` days, sorted by mtime ascending."""
    cutoff = time.time() - (days * 86400)
    old = [f for f in files if f.mtime < cutoff]
    return sorted(old, key=lambda f: f.mtime)


def large_files_in_folder(
    files: list[FileEntry], folder_pattern: str, n: int = 15
) -> list[FileEntry]:
    """Return top-N files whose path contains folder_pattern (case-insensitive)."""
    pattern = folder_pattern.lower()
    matched = [f for f in files if pattern in f.path.lower()]
    return sorted(matched, key=lambda f: f.size, reverse=True)[:n]


def temp_files_report(files: list[FileEntry]) -> dict[str, int]:
    """
    Return dict of temp-related folder → total size.
    Covers: %TEMP%, C:\\Windows\\Temp, common cache folders.
    """
    temp_patterns = [
        "\\temp\\", "\\tmp\\", "\\cache\\", "\\thumbnailcache",
        "appdata\\local\\temp", "windows\\temp",
        "appdata\\local\\microsoft\\windows\\inetcache",
        "appdata\\roaming\\microsoft\\windows\\recent",
        "appdata\\local\\crashdumps",
        "appdata\\local\\microsoft\\edge\\user data\\default\\cache",
        "appdata\\local\\google\\chrome\\user data\\default\\cache",
    ]
    result: dict[str, int] = defaultdict(int)
    for f in files:
        path_lower = f.path.lower()
        for pat in temp_patterns:
            if pat in path_lower:
                result[pat] += f.size
                break
    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))


def log_files_report(files: list[FileEntry], older_than_days: int = 30) -> list[FileEntry]:
    """Return .log files older than given days, sorted by size desc."""
    cutoff = time.time() - (older_than_days * 86400)
    logs = [f for f in files if f.ext == ".log" and f.mtime < cutoff]
    return sorted(logs, key=lambda f: f.size, reverse=True)


@dataclass
class DuplicateGroup:
    size:  int
    paths: list[str]

def find_duplicates(
    files: list[FileEntry], min_size: int = 1024 * 1024
) -> list[DuplicateGroup]:
    """
    Find files with identical (name + size) — lightweight duplicate detection.
    Uses (filename_lower, size) as key. No file content read (read-only).
    Only considers files >= min_size (default 1 MB) to avoid noise.
    """
    seen: dict[tuple[str, int], list[str]] = defaultdict(list)
    for f in files:
        if f.size < min_size:
            continue
        key = (os.path.basename(f.path).lower(), f.size)
        seen[key].append(f.path)

    groups = [
        DuplicateGroup(size=size, paths=paths)
        for (_, size), paths in seen.items()
        if len(paths) > 1
    ]
    return sorted(groups, key=lambda g: g.size * len(g.paths), reverse=True)
