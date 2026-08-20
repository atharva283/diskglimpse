"""
exporter.py - Data Export Module

Provides clean, decoupled export functionality for scanner data.
Supports JSON and CSV formats using Python's built-in libraries.
"""

import os
import json
import csv
from typing import Dict, List, Any, Optional


def export_to_json(
    data: List[Dict[str, Any]],
    output_path: str,
    indent: int = 2,
    include_summary: bool = True
) -> str:
    """
    Export scan data to a JSON file.
    
    Args:
        data: List of file information dictionaries from scanner
        output_path: Path to the output JSON file
        indent: JSON indentation level (default: 2)
        include_summary: Whether to include summary statistics (default: True)
        
    Returns:
        Absolute path to the created JSON file
        
    Raises:
        IOError: If unable to write to the specified path
    """
    # Ensure output directory exists
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Prepare export data
    export_data: Dict[str, Any] = {
        'files': data,
        'total_files': len([item for item in data if item.get('is_file', False)]),
        'total_directories': len([item for item in data if item.get('is_dir', False)]),
        'total_size_bytes': sum(item.get('size', 0) for item in data if item.get('is_file', False)),
        'errors': [item for item in data if item.get('error')],
    }
    
    if include_summary:
        error_count = len(export_data['errors'])
        export_data['summary'] = {
            'scan_successful': error_count == 0,
            'items_scanned': len(data),
            'error_count': error_count,
            'total_size_human': _format_size(export_data['total_size_bytes']),
        }
    
    # Write JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=indent, ensure_ascii=False)
    
    return os.path.abspath(output_path)


def export_to_csv(
    data: List[Dict[str, Any]],
    output_path: str,
    fields: Optional[List[str]] = None
) -> str:
    """
    Export scan data to a CSV file.
    
    Args:
        data: List of file information dictionaries from scanner
        output_path: Path to the output CSV file
        fields: List of fields to include (default: all available fields)
        
    Returns:
        Absolute path to the created CSV file
        
    Raises:
        IOError: If unable to write to the specified path
    """
    if not data:
        # Create empty CSV with headers if no data
        default_fields = ['path', 'name', 'size', 'is_file', 'is_dir', 'is_symlink', 'depth', 'error']
        fields = fields or default_fields
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
        
        return os.path.abspath(output_path)
    
    # Determine fields to export
    if fields is None:
        # Get all unique keys from data
        fields = []
        seen_keys = set()
        for item in data:
            for key in item.keys():
                if key not in seen_keys:
                    fields.append(key)
                    seen_keys.add(key)
    
    # Ensure output directory exists
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Write CSV file
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)
    
    return os.path.abspath(output_path)


def export_to_both(
    data: List[Dict[str, Any]],
    base_output_path: str,
    fields: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Export scan data to both JSON and CSV formats.
    
    Args:
        data: List of file information dictionaries from scanner
        base_output_path: Base path for output files (extensions will be added)
        fields: List of fields to include in CSV (default: all available fields)
        
    Returns:
        Dictionary with paths to created files:
        - 'json': Path to JSON file
        - 'csv': Path to CSV file
    """
    # Generate output paths
    base_path = os.path.splitext(base_output_path)[0]
    json_path = f"{base_path}.json"
    csv_path = f"{base_path}.csv"
    
    # Export to both formats
    json_result = export_to_json(data, json_path)
    csv_result = export_to_csv(data, csv_path, fields)
    
    return {
        'json': json_result,
        'csv': csv_result,
    }


def _format_size(size_bytes: int) -> str:
    """
    Convert bytes to human-readable size string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string (e.g., "1.5 GB")
    """
    if size_bytes < 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.2f} {units[unit_index]}"


def validate_export_path(path: str) -> bool:
    """
    Validate that an export path is writable.
    
    Args:
        path: Path to validate
        
    Returns:
        True if path is valid and writable, False otherwise
    """
    try:
        # Check if parent directory exists or can be created
        parent_dir = os.path.dirname(os.path.abspath(path))
        if parent_dir and not os.path.exists(parent_dir):
            # Try to create it
            os.makedirs(parent_dir, exist_ok=True)
        
        # Check if we can write to the location
        if os.path.exists(path):
            # File exists, check if writable
            return os.access(path, os.W_OK)
        else:
            # File doesn't exist, check if parent dir is writable
            test_dir = parent_dir if parent_dir else '.'
            return os.access(test_dir, os.W_OK)
            
    except (OSError, PermissionError):
        return False
