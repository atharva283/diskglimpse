#!/usr/bin/env python3
"""
main.py - Disk Analyzer CLI Entry Point

Enterprise-grade Windows Disk Analyzer with:
- Real-time TUI using Rich
- Interactive drill-down navigation
- Smart junk detection
- Advanced filtering options
"""

import sys
import os
import argparse
from typing import List, Optional, Dict, Any


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog='disk-analyzer',
        description='Enterprise-Grade Windows Disk Analyzer CLI',
        epilog='Examples:\n  python main.py C:\\ --interactive\n  python main.py D:\\Projects --min-size 1MB --ext .log'
    )

    parser.add_argument('path', type=str, nargs='?', default='C:\\',
                        help='Target drive or directory to scan')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Enable interactive mode with TUI')
    parser.add_argument('--export-json', type=str, metavar='PATH',
                        help='Export results to JSON')
    parser.add_argument('--export-csv', type=str, metavar='PATH',
                        help='Export results to CSV')
    parser.add_argument('--include-hidden', action='store_true',
                        help='Include hidden files')
    parser.add_argument('--max-depth', type=int, metavar='N', default=None,
                        help='Maximum directory depth')
    parser.add_argument('--min-size', type=str, metavar='SIZE',
                        help='Minimum file size (e.g., 1KB, 5MB)')
    parser.add_argument('--max-size', type=str, metavar='SIZE',
                        help='Maximum file size')
    parser.add_argument('--ext', '--extension', type=str, metavar='EXT',
                        action='append', help='Filter by extension')
    parser.add_argument('--pattern', type=str, metavar='PATTERN',
                        help='Filter by filename pattern')
    parser.add_argument('--detect-junk', action='store_true',
                        help='Enable junk detection')
    parser.add_argument('--top', type=int, metavar='N', default=20,
                        help='Number of top items to display')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0')

    return parser.parse_args()


def parse_size(size_str: str) -> int:
    """Parse human-readable size string to bytes."""
    if not size_str:
        return 0
    size_str = size_str.strip().upper()
    units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
    for unit, mult in sorted(units.items(), key=lambda x: -len(x[0])):
        if size_str.endswith(unit):
            try:
                return int(float(size_str[:-len(unit)]) * mult)
            except ValueError:
                return 0
    try:
        return int(size_str)
    except ValueError:
        return 0


def apply_filters(data: List[Dict[str, Any]], min_size: int = 0,
                  max_size: Optional[int] = None,
                  extensions: Optional[List[str]] = None,
                  pattern: Optional[str] = None) -> List[Dict[str, Any]]:
    """Apply filters to scan results."""
    import fnmatch
    filtered = []
    for item in data:
        is_file = item.get('is_file', False)
        if is_file:
            size = item.get('size', 0)
            if size < min_size:
                continue
            if max_size is not None and size > max_size:
                continue
            if extensions:
                ext = os.path.splitext(item.get('name', ''))[1].lower()
                if ext not in [e.lower() for e in extensions]:
                    continue
            if pattern:
                name = item.get('name', '')
                if not fnmatch.fnmatch(name, pattern):
                    continue
        filtered.append(item)
    return filtered


def run_interactive_mode(target_path: str, args) -> int:
    """Run interactive TUI mode with drill-down navigation."""
    from scanner import scan_directory, build_tree_from_results, find_node_by_path
    from tui import (ScanProgress, display_summary_table, build_directory_tree,
                     select_directory_to_explore, navigate_directory_menu,
                     display_junk_cleanup_menu, confirm_deletion, format_size)
    from junk_detector import detect_junk, get_junk_summary, estimate_junk_size
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    try:
        with ScanProgress() as progress:
            results = []
            for item in scan_directory(root_path=target_path,
                                     include_hidden=args.include_hidden,
                                     max_depth=args.max_depth):
                results.append(item)
                if len(results) % 50 == 0:
                    progress.update(item['path'], len(results))
            progress.complete(len(results))

        min_size = parse_size(args.min_size) if args.min_size else 0
        max_size = parse_size(args.max_size) if args.max_size else None

        if min_size > 0 or max_size or args.ext or args.pattern:
            results = apply_filters(results, min_size=min_size, max_size=max_size,
                                    extensions=args.ext, pattern=args.pattern)
            console.print(f"[yellow]Filtered to {len(results)} items[/]")

        junk_flags = detect_junk(results)
        summary = get_junk_summary(junk_flags)
        total_junk_size = estimate_junk_size(junk_flags, results)

        if any(summary.values()):
            console.print(Panel(
                f"[bold yellow]Developer Cache:[/] {summary.get('Developer Cache', 0)}\n"
                f"[bold red]System Junk:[/] {summary.get('System Junk', 0)}\n"
                f"[bold green]Estimated Size:[/] {format_size(total_junk_size)}",
                title="Junk Detection Summary", border_style="yellow"))

        root_tree = build_tree_from_results(results, target_path)
        display_summary_table(results, top_n=args.top, junk_flags=junk_flags)

        while True:
            dir_options = [item['path'] for item in results
                          if item.get('is_dir') and item.get('total_size', item.get('size', 0)) > 0][:20]
            if not dir_options:
                console.print("[yellow]No directories available.[/]")
                break

            selected_path = select_directory_to_explore(dir_options)
            if not selected_path:
                break

            node = find_node_by_path(root_tree, selected_path)
            if not node:
                console.print(f"[red]Could not find: {selected_path}[/]")
                continue

            node_data = {'name': node.name, 'path': node.path, 'size': node.size,
                        'total_size': node.get_total_size(), 'is_dir': node.is_dir,
                        'children': [child.to_dict() for child in node.children]}

            tree = build_directory_tree(node_data, junk_flags)
            console.print("\n", tree)

            action = navigate_directory_menu()
            if action == 'exit':
                break
            elif action == 'go_back':
                continue
            elif action == 'view_subfolder':
                subfolders = [child.path for child in node.children if child.is_dir]
                if subfolders:
                    selected_sub = select_directory_to_explore(subfolders)
                    if selected_sub:
                        continue

        if junk_flags:
            selected_to_delete = display_junk_cleanup_menu(junk_flags)
            if selected_to_delete and confirm_deletion(selected_to_delete):
                import shutil
                deleted_count = 0
                for path in selected_to_delete:
                    try:
                        if os.path.isfile(path):
                            os.remove(path)
                        else:
                            shutil.rmtree(path)
                        deleted_count += 1
                        console.print(f"[green]Deleted:[/] {path}")
                    except Exception as e:
                        console.print(f"[red]Failed: {path}: {e}[/]")
                console.print(f"\n[bold green]Cleanup complete! Deleted {deleted_count} items.[/]")

        if args.export_json or args.export_csv:
            from exporter import export_to_both
            export_to_both(results, json_path=args.export_json, csv_path=args.export_csv)
            if args.export_json:
                console.print(f"[green]Exported JSON:[/] {args.export_json}")
            if args.export_csv:
                console.print(f"[green]Exported CSV:[/] {args.export_csv}")

        return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/]")
        return 130
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 4


def run_cli_mode(target_path: str, args) -> int:
    """Run basic CLI mode without TUI."""
    from scanner import scan_directory
    from exporter import export_to_both

    print(f"\nScanning: {target_path}\n")

    try:
        results = list(scan_directory(root_path=target_path,
                                 include_hidden=args.include_hidden,
                                 max_depth=args.max_depth))

        min_size = parse_size(args.min_size) if args.min_size else 0
        max_size = parse_size(args.max_size) if args.max_size else None

        if min_size > 0 or max_size or args.ext or args.pattern:
            results = apply_filters(results, min_size=min_size, max_size=max_size,
                                    extensions=args.ext, pattern=args.pattern)

        total_files = sum(1 for r in results if r.get('is_file'))
        total_dirs = sum(1 for r in results if r.get('is_dir'))
        total_size = sum(r.get('size', 0) for r in results if r.get('is_file'))

        print(f"\nComplete! Files: {total_files}, Dirs: {total_dirs}, Size: {total_size:,} bytes")

        if args.export_json or args.export_csv:
            export_to_both(results, args.export_json, args.export_csv)
            if args.export_json:
                print(f"  JSON: {args.export_json}")
            if args.export_csv:
                print(f"  CSV: {args.export_csv}")

        return 0

    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 4


def _is_no_args_run() -> bool:
    """
    Detect if the program was launched with no meaningful arguments —
    i.e. double-clicked from Explorer or run as bare `diskglimpse`.

    Returns True when only the default path (or nothing) was provided
    and no CLI flags were explicitly set.
    """
    import sys
    # sys.argv[0] is the script/exe name; anything beyond is a user argument
    user_args = sys.argv[1:]

    # If completely empty → definitely double-clicked
    if not user_args:
        return True

    # If the only argument looks like a drive/path (not a flag), still treat
    # it as a "no flags" run so the TUI opens on that path
    if len(user_args) == 1 and not user_args[0].startswith('-'):
        return True

    return False


def main() -> int:
    """Main entry point."""
    args = parse_arguments()
    target_path = os.path.abspath(args.path)

    if not os.path.exists(target_path):
        print(f"Error: Path does not exist: {target_path}", file=sys.stderr)
        return 1
    if not os.path.isdir(target_path):
        print(f"Error: Not a directory: {target_path}", file=sys.stderr)
        return 1

    # Auto-launch interactive TUI when:
    #   • double-clicked from Explorer
    #   • run as bare `diskglimpse` or `diskglimpse D:\`
    #   • --interactive flag explicitly passed
    try:
        if args.interactive or _is_no_args_run():
            ret = run_interactive_mode(target_path, args)
        else:
            ret = run_cli_mode(target_path, args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        ret = 1

    if _is_no_args_run():
        input("\nPress Enter to exit...")
        
    return ret

if __name__ == '__main__':
    sys.exit(main())
