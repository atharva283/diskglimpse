"""
scanner.py - Core Disk Scanning Engine

Provides iterative BFS directory traversal with crash-proof handling
for reparse points, permission errors, and system directories.
"""

import os
import stat
from collections import deque
from typing import Dict, List, Generator, Any, Optional, Set


# Unified O(1) Skip List for Windows system directories
# Using a static set for constant-time lookups
SYSTEM_SKIP_DIRS: Set[str] = frozenset({
    '$RECYCLE.BIN',
    'System Volume Information',
    'Windows.old',
    'Documents and Settings',
    'ProgramData',
    'AppData',
    'Temp',
    'Prefetch',
})


def _is_reparse_point(path: str) -> bool:
    """
    Check if a path is a reparse point (symlink, junction, or mount point).
    
    Args:
        path: Full path to check
        
    Returns:
        True if the path is a reparse point, False otherwise
    """
    try:
        # Use lstat to not follow symlinks
        file_stat = os.lstat(path)
        return stat.S_ISLNK(file_stat.st_mode) or \
               (hasattr(file_stat, 'st_reparse_tag') and file_stat.st_reparse_tag != 0)
    except (OSError, AttributeError):
        # On some systems, st_reparse_tag may not be available
        # Fall back to checking if it's a symlink
        try:
            return os.path.islink(path)
        except OSError:
            return False


def _should_skip_directory(dir_name: str, full_path: str) -> bool:
    """
    Determine if a directory should be skipped based on skip list or reparse point status.
    
    Args:
        dir_name: Name of the directory (basename)
        full_path: Full absolute path to the directory
        
    Returns:
        True if the directory should be skipped, False otherwise
    """
    # Check against unified skip list (O(1) lookup)
    if dir_name in SYSTEM_SKIP_DIRS:
        return True
    
    # Check if it's a reparse point that should be avoided
    if _is_reparse_point(full_path):
        return True
    
    return False


def scan_directory(
    root_path: str,
    include_hidden: bool = False,
    max_depth: Optional[int] = None
) -> Generator[Dict[str, Any], None, None]:
    """
    Perform iterative BFS directory traversal using os.scandir.
    
    Yields structured file information dictionaries safely, handling:
    - Permission errors
    - Reparse points (symlinks, junctions)
    - System directories via O(1) skip list
    - Circular references
    
    Args:
        root_path: Root directory path to start scanning from
        include_hidden: Whether to include hidden files (default: False)
        max_depth: Maximum directory depth to traverse (None for unlimited)
        
    Yields:
        Dict containing file information:
        - path: Absolute file path
        - name: File/directory name
        - size: Size in bytes (0 for directories)
        - is_file: Boolean indicating if it's a file
        - is_dir: Boolean indicating if it's a directory
        - is_symlink: Boolean indicating if it's a symlink/junction
        - depth: Directory depth from root
        - error: Error message if access failed, None otherwise
    """
    # Normalize and validate root path
    root_path = os.path.abspath(root_path)
    
    if not os.path.exists(root_path):
        raise FileNotFoundError(f"Root path does not exist: {root_path}")
    
    if not os.path.isdir(root_path):
        raise NotADirectoryError(f"Root path is not a directory: {root_path}")
    
    # BFS queue: (path, depth)
    queue: deque = deque()
    queue.append((root_path, 0))
    
    # Track visited paths to prevent circular references
    visited: Set[str] = set()
    visited.add(root_path)
    
    while queue:
        current_path, current_depth = queue.popleft()
        
        # Yield directory info (except for root which was already processed)
        if current_path != root_path:
            try:
                dir_stat = os.lstat(current_path)
                yield {
                    'path': current_path,
                    'name': os.path.basename(current_path),
                    'size': 0,
                    'is_file': False,
                    'is_dir': True,
                    'is_symlink': _is_reparse_point(current_path),
                    'depth': current_depth,
                    'error': None,
                }
            except OSError as e:
                yield {
                    'path': current_path,
                    'name': os.path.basename(current_path),
                    'size': 0,
                    'is_file': False,
                    'is_dir': True,
                    'is_symlink': False,
                    'depth': current_depth,
                    'error': str(e),
                }
        
        # Check max depth
        if max_depth is not None and current_depth >= max_depth:
            continue
        
        # Scan current directory
        try:
            with os.scandir(current_path) as entries:
                for entry in entries:
                    try:
                        entry_path = entry.path
                        
                        # Skip hidden files/dirs if not requested
                        if not include_hidden and entry.name.startswith('.'):
                            continue
                        
                        # Check if entry is a file
                        try:
                            is_file = entry.is_file(follow_symlinks=False)
                        except OSError:
                            is_file = False
                        
                        if is_file:
                            try:
                                file_stat = entry.stat(follow_symlinks=False)
                                yield {
                                    'path': entry_path,
                                    'name': entry.name,
                                    'size': file_stat.st_size,
                                    'is_file': True,
                                    'is_dir': False,
                                    'is_symlink': _is_reparse_point(entry_path),
                                    'depth': current_depth + 1,
                                    'error': None,
                                }
                            except OSError as e:
                                yield {
                                    'path': entry_path,
                                    'name': entry.name,
                                    'size': 0,
                                    'is_file': True,
                                    'is_dir': False,
                                    'is_symlink': False,
                                    'depth': current_depth + 1,
                                    'error': str(e),
                                }
                        
                        # Check if entry is a directory
                        elif entry.is_dir(follow_symlinks=False):
                            # Check skip conditions
                            if _should_skip_directory(entry.name, entry_path):
                                continue
                            
                            # Prevent circular references
                            real_path = os.path.realpath(entry_path)
                            if real_path in visited:
                                continue
                            
                            visited.add(real_path)
                            queue.append((entry_path, current_depth + 1))
                    
                    except PermissionError as e:
                        yield {
                            'path': entry.path,
                            'name': entry.name,
                            'size': 0,
                            'is_file': False,
                            'is_dir': False,
                            'is_symlink': False,
                            'depth': current_depth + 1,
                            'error': f"Permission denied: {e}",
                        }
                    except OSError as e:
                        yield {
                            'path': entry.path,
                            'name': entry.name,
                            'size': 0,
                            'is_file': False,
                            'is_dir': False,
                            'is_symlink': False,
                            'depth': current_depth + 1,
                            'error': f"OS error: {e}",
                        }
        
        except PermissionError as e:
            yield {
                'path': current_path,
                'name': os.path.basename(current_path),
                'size': 0,
                'is_file': False,
                'is_dir': True,
                'is_symlink': False,
                'depth': current_depth,
                'error': f"Permission denied accessing directory: {e}",
            }
        except OSError as e:
            yield {
                'path': current_path,
                'name': os.path.basename(current_path),
                'size': 0,
                'is_file': False,
                'is_dir': True,
                'is_symlink': False,
                'depth': current_depth,
                'error': f"OS error accessing directory: {e}",
            }


def scan_to_list(
    root_path: str,
    include_hidden: bool = False,
    max_depth: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Scan directory and return results as a list instead of generator.
    
    Convenience wrapper around scan_directory for cases where
    all results need to be in memory at once.
    
    Args:
        root_path: Root directory path to start scanning from
        include_hidden: Whether to include hidden files
        max_depth: Maximum directory depth to traverse
        
    Returns:
        List of file information dictionaries
    """
    return list(scan_directory(root_path, include_hidden, max_depth))


def get_directory_summary(root_path: str) -> Dict[str, Any]:
    """
    Get a summary of directory statistics without storing all file details.
    
    Args:
        root_path: Root directory path to analyze
        
    Returns:
        Dictionary with summary statistics:
        - total_files: Count of files
        - total_dirs: Count of directories
        - total_size: Total size in bytes
        - error_count: Number of errors encountered
        - scanned_path: The path that was scanned
    """
    summary = {
        'total_files': 0,
        'total_dirs': 0,
        'total_size': 0,
        'error_count': 0,
        'scanned_path': os.path.abspath(root_path),
    }
    
    for item in scan_directory(root_path):
        if item['error']:
            summary['error_count'] += 1
        elif item['is_file']:
            summary['total_files'] += 1
            summary['total_size'] += item['size']
        elif item['is_dir']:
            summary['total_dirs'] += 1
    
    return summary
