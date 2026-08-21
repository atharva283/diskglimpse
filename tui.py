"""
tui.py - Real-time Terminal User Interface using Rich and Questionary

Provides:
- Real-time progress bar with file count, ETA, and throughput
- Status spinner for perceived responsiveness
- Post-scan summary table with top largest items
- Interactive drill-down navigation with questionary
- Tree visualization of directory contents
"""

import os
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.progress import (Progress, TextColumn, BarColumn, TaskProgressColumn, 
                         TimeRemainingColumn, TransferSpeedColumn, MofNCompleteColumn)
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.text import Text
import questionary


console = Console()


def format_size(size_bytes: int) -> str:
    """Format size in bytes to human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.2f} {size_names[i]}"


class ScanProgress:
    """Context manager for displaying real-time scan progress."""
    
    def __init__(self, total_files: Optional[int] = None):
        self.total_files = total_files
        self.progress = None
        self.task_id = None
        self.file_count = 0
    
    def __enter__(self):
        self.progress = Progress(
            TextColumn("[bold blue]{task.description}", justify="right"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            TransferSpeedColumn(),
            console=console,
            refresh_per_second=2
        )
        self.progress.start()
        
        self.task_id = self.progress.add_task(
            "[cyan]Scanning...",
            total=self.total_files,
            completed=0
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.progress:
            self.progress.stop()
    
    def update(self, current_path: str, count: int):
        """Update progress with current file count and path."""
        self.file_count = count
        
        # Update every 500 files to avoid UI bottlenecks
        if count % 500 == 0 or self.total_files is None:
            truncate_path = current_path[-60:] if len(current_path) > 60 else current_path
            self.progress.update(
                self.task_id,
                description=f"[cyan]Scanning... {truncate_path}",
                completed=count,
                total=self.total_files
            )
            self.progress.refresh()
    
    def complete(self, total: int):
        """Mark the task as complete."""
        if self.progress and self.task_id is not None:
            self.progress.update(
                self.task_id,
                description="[green]✓ Scan Complete!",
                completed=total,
                total=total
            )
            self.progress.refresh()


def show_status(message: str):
    """Display a spinning status indicator."""
    with console.status(f"[bold green]{message}", spinner="dots"):
        # This is a context manager - calling code should use it as such
        pass


def display_summary_table(results: List[Dict[str, Any]], top_n: int = 20,
                          junk_flags: Optional[Dict[str, str]] = None) -> None:
    """
    Display a summary table of the top N largest directories/files.
    
    Args:
        results: List of file/directory dictionaries from scanner
        top_n: Number of top items to display
        junk_flags: Optional dict mapping paths to junk type labels
    """
    # Sort by size descending
    sorted_results = sorted(
        results,
        key=lambda x: x.get('size', 0) or x.get('total_size', 0),
        reverse=True
    )[:top_n]
    
    table = Table(title=f"\n[bold magenta]Top {top_n} Largest Items", 
                  show_header=True,
                  header_style="bold cyan")
    
    table.add_column("Rank", style="dim", width=5)
    table.add_column("Type", width=6)
    table.add_column("Size", justify="right", width=12)
    table.add_column("Path", overflow="ellipsis")
    
    if junk_flags:
        table.add_column("Flags", width=15)
    
    for idx, item in enumerate(sorted_results, 1):
        item_type = "DIR" if item.get('is_dir') else "FILE"
        size = item.get('total_size', item.get('size', 0))
        size_str = format_size(size)
        path = item.get('path', 'Unknown')
        
        # Truncate long paths
        if len(path) > 70:
            path = "..." + path[-67:]
        
        row_data = [
            str(idx),
            f"[yellow]{item_type}" if item_type == "DIR" else f"[green]{item_type}",
            f"[white]{size_str}",
            f"[blue]{path}"
        ]
        
        if junk_flags:
            flag = junk_flags.get(item.get('path', ''), '')
            if flag:
                if flag == 'Developer Cache':
                    row_data.append(f"[orange1]{flag}")
                elif flag == 'System Junk':
                    row_data.append(f"[red]{flag}")
                else:
                    row_data.append(f"[magenta]{flag}")
            else:
                row_data.append("")
        
        table.add_row(*row_data)
    
    console.print(table)


def build_directory_tree(node_data: Dict[str, Any], junk_flags: Optional[Dict[str, str]] = None) -> Tree:
    """
    Build a Rich Tree representation of a directory's contents.
    
    Args:
        node_data: Dictionary containing directory info with children
        junk_flags: Optional dict mapping paths to junk type labels
    
    Returns:
        Rich Tree object
    """
    name = node_data.get('name', 'Unknown')
    path = node_data.get('path', '')
    size = node_data.get('total_size', node_data.get('size', 0))
    is_dir = node_data.get('is_dir', False)
    
    # Build label with size
    size_str = format_size(size)
    label = f"[bold blue]{name}[/]" if is_dir else f"[green]{name}[/]"
    label += f" [dim]({size_str})[/]"
    
    # Add junk flag if present
    if junk_flags and path in junk_flags:
        flag = junk_flags[path]
        if flag == 'Developer Cache':
            label += f" [orange1][Junk: Dev][/]"
        elif flag == 'System Junk':
            label += f" [red][Junk: Sys][/]"
        else:
            label += f" [magenta][{flag}][/]"
    
    tree = Tree(label)
    
    # Add children
    children = node_data.get('children', [])
    for child in sorted(children, key=lambda x: x.get('total_size', x.get('size', 0)), reverse=True):
        child_name = child.get('name', 'Unknown')
        child_path = child.get('path', '')
        child_size = child.get('total_size', child.get('size', 0))
        child_is_dir = child.get('is_dir', False)
        
        child_label = f"[bold blue]{child_name}[/]" if child_is_dir else f"[green]{child_name}[/]"
        child_label += f" [dim]({format_size(child_size)})[/]"
        
        # Add junk flag
        if junk_flags and child_path in junk_flags:
            flag = junk_flags[child_path]
            if flag == 'Developer Cache':
                child_label += f" [orange1][Junk: Dev][/]"
            elif flag == 'System Junk':
                child_label += f" [red][Junk: Sys][/]"
            else:
                child_label += f" [magenta][{flag}][/]"
        
        tree.add(child_label)
    
    return tree


def select_directory_to_explore(options: List[str]) -> Optional[str]:
    """
    Present user with a list of directories to explore.
    
    Args:
        options: List of directory paths
    
    Returns:
        Selected path or None if cancelled
    """
    if not options:
        console.print("[yellow]No directories available to explore.[/]")
        return None
    
    choice = questionary.select(
        "Which directory would you like to explore?",
        choices=options,
        qmark="📁",
        pointer="➤ "
    ).ask()
    
    return choice


def navigate_directory_menu() -> Optional[str]:
    """
    Present navigation menu for drill-down interface.
    
    Returns:
        Action: 'view_subfolder', 'go_back', 'exit', or None
    """
    action = questionary.select(
        "What would you like to do?",
        choices=[
            "View contents of a subfolder",
            "Go back up",
            "Exit analysis"
        ],
        qmark="🔍",
        pointer="➤ "
    ).ask()
    
    if action == "View contents of a subfolder":
        return 'view_subfolder'
    elif action == "Go back up":
        return 'go_back'
    else:
        return 'exit'


def confirm_deletion(items: List[str]) -> bool:
    """
    Ask user to confirm deletion of selected items.
    
    Args:
        items: List of paths to delete
    
    Returns:
        True if confirmed, False otherwise
    """
    if not items:
        return False
    
    message = f"Are you sure you want to delete {len(items)} item(s)?"
    for item in items[:5]:  # Show first 5
        message += f"\n  - {item}"
    if len(items) > 5:
        message += f"\n  ... and {len(items) - 5} more"
    
    return questionary.confirm(
        message,
        default=False,
        qmark="⚠️"
    ).ask()


def display_junk_cleanup_menu(junk_items: Dict[str, str]) -> List[str]:
    """
    Display interactive menu for selecting junk items to clean.
    
    Args:
        junk_items: Dict mapping paths to junk type labels
    
    Returns:
        List of selected paths for deletion
    """
    if not junk_items:
        console.print("[green]✓ No junk items found to clean.[/]")
        return []
    
    console.print(Panel(
        f"[bold yellow]Found {len(junk_items)} potential junk items[/]\n\n"
        "You can selectively remove these items. Only folders you explicitly\n"
        "select will be deleted.",
        title="🗑️ Junk Cleanup",
        border_style="yellow"
    ))
    
    wants_cleanup = questionary.confirm(
        "Would you like to review and clean up these junk items?",
        default=False
    ).ask()
    
    if not wants_cleanup:
        return []
    
    # Create choices with junk type indicators
    choices = []
    for path, junk_type in sorted(junk_items.items()):
        name = os.path.basename(path.rstrip('/\\'))
        if junk_type == 'Developer Cache':
            label = f"{name} [orange1](Developer Cache)[/]"
        elif junk_type == 'System Junk':
            label = f"{name} [red](System Junk)[/]"
        else:
            label = f"{name} [magenta]({junk_type})[/]"
        
        choices.append(questionary.Choice(title=label, value=path))
    
    # Allow multi-select
    selected = questionary.checkbox(
        "Select items to delete (Press Enter without selecting any to SKIP)",
        choices=choices,
        qmark="🧹",
        pointer="➤ ",
        instruction="(Space to select/deselect, Enter to confirm or skip)"
    ).ask()
    
    return selected if selected else []


def prompt_for_export(results: List[Dict[str, Any]]) -> None:
    """Prompt the user if they want to export the scan results."""
    choice = questionary.select(
        "Would you like to export the scan results?",
        choices=[
            "No, exit",
            "Export to CSV",
            "Export to JSON",
            "Export to Both"
        ],
        qmark="💾",
        pointer="➤ "
    ).ask()
    
    if choice == "No, exit" or not choice:
        return
        
    import exporter
    import time
    
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    
    if choice in ["Export to CSV", "Export to Both"]:
        csv_path = questionary.text(
            "Enter CSV filename:", 
            default=f"diskglimpse_report_{timestamp}.csv"
        ).ask()
        if csv_path:
            exporter.export_to_csv(results, csv_path)
            console.print(f"[green]✓ CSV exported to {csv_path}[/]")
            
    if choice in ["Export to JSON", "Export to Both"]:
        json_path = questionary.text(
            "Enter JSON filename:", 
            default=f"diskglimpse_report_{timestamp}.json"
        ).ask()
        if json_path:
            exporter.export_to_json(results, json_path)
            console.print(f"[green]✓ JSON exported to {json_path}[/]")
