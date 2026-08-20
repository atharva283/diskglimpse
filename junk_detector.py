"""
junk_detector.py - Smart Junk Detection Engine

Identifies developer clutter and system junk using heuristic rules.
Does NOT automatically delete files - only flags them for user review.
"""

import os
from typing import Dict, List, Set, Any


# Developer junk patterns
DEVELOPER_JUNK_DIRS = {
    'node_modules',      # npm packages
    '.venv',             # Python virtual environments
    'venv',              # Python virtual environments (alternative name)
    'env',               # Python virtual environments (short name)
    '.idea',             # JetBrains IDEs
    '.vscode',           # VS Code settings
    'dist',              # Build output (Python/Node)
    'build',             # Build output directory
    '__pycache__',       # Python bytecode cache
    '.pytest_cache',     # pytest cache
    '.mypy_cache',       # mypy cache
    'target',            # Rust/Cargo build output
    'bin',               # Compiled binaries (context-dependent)
    'obj',               # Compiled objects (.NET)
    '.gradle',           # Gradle cache
    '.npm',              # npm cache
    '.yarn',             # Yarn cache
}

# Files that indicate a directory is developer junk
DEVELOPER_JUNK_INDICATORS = {
    'package-lock.json': 'node_modules',  # Indicates node_modules is safe to clean
    'yarn.lock': 'node_modules',
    'requirements.txt': {'venv', '.venv', 'env'},  # Indicates venv directories
    'Cargo.toml': 'target',
    'pom.xml': 'target',  # Maven
    'build.gradle': '.gradle',
    'setup.py': {'build', 'dist', '__pycache__'},
    'pyproject.toml': {'build', 'dist', '__pycache__'},
}

# System junk patterns
SYSTEM_JUNK_EXTENSIONS = {
    '.log',                # Log files
    '.tmp',                # Temporary files
    '.temp',               # Temporary files (alternative)
    '.bak',                # Backup files
    '.old',                # Old versions
    '.swp',                # Vim swap files
    '.swo',                # Vim swap files
    '~',                   # Emacs backup files
}

# System junk directory names
SYSTEM_JUNK_DIRS = {
    'Temp',
    'tmp',
    'Cache',
    'Caches',
    'Temporary Internet Files',
    'IECompatCache',
    'IEDownloadHistory',
    'History',
    'Thumbnails',
    '$Recycle.Bin',
}

# Browser cache directories
BROWSER_CACHE_DIRS = {
    'Chrome',
    'Chromium',
    'Firefox',
    'Edge',
    'Opera',
    'Brave',
    'Safari',
}

BROWSER_CACHE_SUBDIRS = {
    'Cache',
    'Caches',
    'Code Cache',
    'GPUCache',
    'Local Storage',
    'Session Storage',
    'IndexedDB',
}


def is_developer_junk(path: str, name: str, context_files: Set[str] = None) -> tuple[bool, str]:
    """
    Check if a directory is developer junk based on heuristics.
    
    Args:
        path: Full path to the directory
        name: Directory name
        context_files: Set of filenames found in parent directory
    
    Returns:
        Tuple of (is_junk: bool, reason: str)
    """
    # Check if directory name matches known developer junk patterns
    if name in DEVELOPER_JUNK_DIRS:
        # Special handling for node_modules - check for package-lock.json
        if name == 'node_modules':
            if context_files and ('package-lock.json' in context_files or 'yarn.lock' in context_files):
                return True, 'Developer Cache'
            # Without lock file, might be unsafe to flag
            return False, ''
        
        # Special handling for venv directories - check for requirements.txt
        if name in {'venv', '.venv', 'env'}:
            if context_files and 'requirements.txt' in context_files:
                return True, 'Developer Cache'
            return False, ''
        
        # Other developer directories are generally safe to flag
        return True, 'Developer Cache'
    
    return False, ''


def is_system_junk(path: str, name: str, is_dir: bool = True) -> tuple[bool, str]:
    """
    Check if a file/directory is system junk.
    
    Args:
        path: Full path to the item
        name: File/directory name
        is_dir: Whether this is a directory
    
    Returns:
        Tuple of (is_junk: bool, reason: str)
    """
    # Check directory names
    if is_dir and name in SYSTEM_JUNK_DIRS:
        return True, 'System Junk'
    
    # Check browser cache directories
    for browser in BROWSER_CACHE_DIRS:
        if browser in path:
            for cache_subdir in BROWSER_CACHE_SUBDIRS:
                if name == cache_subdir or cache_subdir in path:
                    return True, 'System Junk'
    
    # Check file extensions for system junk
    if not is_dir:
        _, ext = os.path.splitext(name)
        if ext.lower() in SYSTEM_JUNK_EXTENSIONS:
            return True, 'System Junk'
        
        # Check for log files
        if name.endswith('.log'):
            return True, 'System Junk'
    
    return False, ''


def detect_junk(scan_results: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Analyze scan results and flag potential junk files/directories.
    
    Args:
        scan_results: List of file/directory dictionaries from scanner
    
    Returns:
        Dictionary mapping paths to junk type labels
    """
    junk_flags = {}
    
    # Build a map of parent directories to their children files
    # This helps with context-aware detection (e.g., venv + requirements.txt)
    parent_to_files: Dict[str, Set[str]] = {}
    
    for item in scan_results:
        path = item.get('path', '')
        name = item.get('name', '')
        is_dir = item.get('is_dir', True)
        parent_path = os.path.dirname(path)
        
        if not is_dir and parent_path:
            if parent_path not in parent_to_files:
                parent_to_files[parent_path] = set()
            parent_to_files[parent_path].add(name)
    
    # Analyze each item
    for item in scan_results:
        path = item.get('path', '')
        name = item.get('name', '')
        is_dir = item.get('is_dir', True)
        parent_path = os.path.dirname(path)
        
        # Get context files for this parent directory
        context_files = parent_to_files.get(parent_path, set())
        
        # Check for developer junk
        is_dev_junk, dev_reason = is_developer_junk(path, name, context_files)
        if is_dev_junk:
            junk_flags[path] = dev_reason
            continue
        
        # Check for system junk
        is_sys_junk, sys_reason = is_system_junk(path, name, is_dir)
        if is_sys_junk:
            junk_flags[path] = sys_reason
    
    return junk_flags


def get_junk_summary(junk_flags: Dict[str, str]) -> Dict[str, int]:
    """
    Get summary statistics of detected junk.
    
    Args:
        junk_flags: Dictionary mapping paths to junk type labels
    
    Returns:
        Dictionary with counts by junk type
    """
    summary = {
        'Developer Cache': 0,
        'System Junk': 0,
        'Other': 0
    }
    
    for junk_type in junk_flags.values():
        if junk_type in summary:
            summary[junk_type] += 1
        else:
            summary['Other'] += 1
    
    return summary


def estimate_junk_size(junk_flags: Dict[str, str], 
                       scan_results: List[Dict[str, Any]]) -> int:
    """
    Estimate total size of junk items.
    
    Args:
        junk_flags: Dictionary mapping paths to junk type labels
        scan_results: List of file/directory dictionaries from scanner
    
    Returns:
        Total estimated size in bytes
    """
    # Create a map of paths to sizes
    path_to_size = {item.get('path', ''): item.get('total_size', item.get('size', 0)) 
                    for item in scan_results}
    
    total_size = 0
    for path in junk_flags.keys():
        total_size += path_to_size.get(path, 0)
    
    return total_size
