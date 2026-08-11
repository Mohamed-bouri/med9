#!/usr/bin/env python3
"""
Med9 v2.1 - Folder Content Extractor & Tree Viewer
Extracts directory structures and text file contents into organized reports.
Interactive shell, configurable filters, and batch extraction.
By Mohamed BOURI
"""

from __future__ import annotations

import argparse
import cmd
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
APP_NAME = "Med9"
VERSION = "2.1.0"
CONFIG_DIR = Path.home() / ".config" / "med9"
CONFIG_FILE = CONFIG_DIR / "config.json"

BANNER = r"""
  __  __        _ ___ 
 |  \/  |___ __| / _ \
 | |\/| / -_) _` \_, /
 |_|  |_\___\__,_|/_/ 

Folder Content Extractor & Tree Viewer v2.1
By Mohamed BOURI

Type 'help' or '?' to list commands. Type 'exit' to quit.
"""

PROMPT = "\033[92mMed9>\033[0m "

# Detect script path and directory dynamically
try:
    SCRIPT_PATH = Path(__file__).resolve()
    SCRIPT_DIR = SCRIPT_PATH.parent
    CURRENT_SCRIPT_NAME = SCRIPT_PATH.name
except NameError:
    SCRIPT_DIR = Path.cwd()
    CURRENT_SCRIPT_NAME = ""

# Default filters
DEFAULT_IGNORE_DIRS = {
    '.git', '__pycache__', '.venv', 'venv', 'env',
    'node_modules', '.idea', '.vscode', '.build', 'dist',
    '.pytest_cache', '.mypy_cache', '.tox', 'target', 'build',
    '.eggs', '*.egg-info', '.coverage', 'htmlcov',
}

DEFAULT_IGNORE_FILES = {
    '.DS_Store', 'Thumbs.db', 'package-lock.json', 'yarn.lock',
    'Pipfile.lock', 'poetry.lock', '.env', '.env.local', 'result.txt'
}
if CURRENT_SCRIPT_NAME:
    DEFAULT_IGNORE_FILES.add(CURRENT_SCRIPT_NAME)

BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.pdf',
    '.exe', '.dll', '.so', '.dylib', '.zip', '.tar', '.gz',
    '.pyc', '.pkl', '.mp3', '.mp4', '.woff', '.ttf', '.otf',
    '.eot', '.woff2', '.bmp', '.tiff', '.webp', '.raw',
    '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.db', '.sqlite', '.sqlite3', '.class', '.o', '.obj',
    '.jar', '.war', '.ear', '.deb', '.rpm', '.msi',
    '.7z', '.rar', '.bz2', '.xz', '.lz', '.lzma',
}


# ---------------------------------------------------------------------------
# Config Manager
# ---------------------------------------------------------------------------

class ConfigManager:
    """Persistent configuration storage."""

    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        if not CONFIG_FILE.exists():
            return self._defaults()
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return self._defaults()

    def _defaults(self) -> dict:
        return {
            "ignore_dirs": sorted(DEFAULT_IGNORE_DIRS),
            "ignore_files": sorted(DEFAULT_IGNORE_FILES),
            "binary_extensions": sorted(BINARY_EXTENSIONS),
            "max_size_kb": 500,
            "output_format": "txt",
            "show_binary_notice": True,
        }

    def save(self) -> None:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value) -> None:
        self.data[key] = value
        self.save()


# ---------------------------------------------------------------------------
# Core Engine
# ---------------------------------------------------------------------------

class Med9Core:
    def __init__(self, config: ConfigManager):
        self.config = config

    def is_binary(self, file_path: Path) -> bool:
        """Check if a file is binary by extension or content inspection."""
        if file_path.suffix.lower() in set(self.config.get("binary_extensions", BINARY_EXTENSIONS)):
            return True
        try:
            with open(file_path, "tr") as f:
                f.read(1024)
                return False
        except UnicodeDecodeError:
            return True

    def generate_tree(
        self,
        dir_path: Path,
        ignore_dirs: Optional[Set[str]] = None,
        ignore_files: Optional[Set[str]] = None,
        prefix: str = "",
    ) -> List[str]:
        """Recursively generate an ASCII tree structure."""
        lines = []
        ignore_dirs = ignore_dirs or set(self.config.get("ignore_dirs", DEFAULT_IGNORE_DIRS))
        ignore_files = ignore_files or set(self.config.get("ignore_files", DEFAULT_IGNORE_FILES))

        if CURRENT_SCRIPT_NAME:
            ignore_files.add(CURRENT_SCRIPT_NAME)
        ignore_files.add("result.txt")

        try:
            entries = sorted(list(dir_path.iterdir()), key=lambda x: (x.is_file(), x.name.lower()))
        except PermissionError:
            return [f"{prefix}└── [Permission Denied]"]

        entries = [e for e in entries if e.name not in ignore_dirs and e.name not in ignore_files]

        count = len(entries)
        for i, entry in enumerate(entries):
            connector = "└── " if i == count - 1 else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                extension = "    " if i == count - 1 else "│   "
                lines.extend(self.generate_tree(entry, ignore_dirs, ignore_files, prefix + extension))

        return lines

    def extract_tree_only(
        self,
        root_dir: Path,
        output_file: Optional[Path] = None,
        ignore_dirs: Optional[Set[str]] = None,
        ignore_files: Optional[Set[str]] = None,
    ) -> List[str]:
        """Extract directory tree only. Returns output lines."""
        root = root_dir.resolve()
        if not root.exists() or not root.is_dir():
            return [f"[!] Directory not found: {root}"]

        ignore_dirs = ignore_dirs or set(self.config.get("ignore_dirs", DEFAULT_IGNORE_DIRS))
        ignore_files = ignore_files or set(self.config.get("ignore_files", DEFAULT_IGNORE_FILES))

        lines = []
        lines.append("=" * 80)
        lines.append(f"DIRECTORY TREE: {root.name}")
        lines.append(f"Absolute Path: {root}")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"{root.name}/")
        lines.extend(self.generate_tree(root, ignore_dirs, ignore_files))
        lines.append("")
        lines.append("=" * 80)
        lines.append("SUMMARY: Tree extraction complete")
        lines.append("=" * 80)

        if output_file:
            output_file.write_text("\n".join(lines), encoding="utf-8")

        return lines

    def extract(
        self,
        root_dir: Path,
        output_file: Optional[Path] = None,
        max_size_kb: Optional[int] = None,
        ignore_dirs: Optional[Set[str]] = None,
        ignore_files: Optional[Set[str]] = None,
    ) -> Tuple[int, List[str]]:
        """Full extraction: tree + file contents."""
        root = root_dir.resolve()
        if not root.exists() or not root.is_dir():
            return 0, [f"[!] Directory not found: {root}"]

        max_size = max_size_kb if max_size_kb is not None else self.config.get("max_size_kb", 500)
        ignore_dirs = ignore_dirs or set(self.config.get("ignore_dirs", DEFAULT_IGNORE_DIRS))
        ignore_files = ignore_files or set(self.config.get("ignore_files", DEFAULT_IGNORE_FILES))

        if CURRENT_SCRIPT_NAME:
            ignore_files.add(CURRENT_SCRIPT_NAME)
        ignore_files.add("result.txt")

        show_binary_notice = self.config.get("show_binary_notice", True)

        lines = []
        lines.append("=" * 80)
        lines.append(f"FOLDER CONTENT EXTRACTION: {root.name}")
        lines.append(f"Absolute Path: {root}")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        lines.append("")
        lines.append("## 1. DIRECTORY STRUCTURE")
        lines.append("")
        lines.append(f"{root.name}/")
        lines.extend(self.generate_tree(root, ignore_dirs, ignore_files))
        lines.append("")
        lines.append("=" * 80)
        lines.append("## 2. FILE CONTENTS")
        lines.append("=" * 80)
        lines.append("")

        file_count = 0
        skipped_binary = 0
        skipped_size = 0

        for current_root, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for file in sorted(files):
                if file in ignore_files:
                    continue

                file_path = Path(current_root) / file
                relative_path = file_path.relative_to(root)

                lines.append(f"\n{'='*20} FILE: {relative_path} {'='*20}\n")

                if self.is_binary(file_path):
                    if show_binary_notice:
                        lines.append("[Skipped: Binary/Non-text File]\n")
                    skipped_binary += 1
                    continue

                try:
                    size_kb = file_path.stat().st_size / 1024
                except OSError:
                    lines.append("[Skipped: Unable to stat file]\n")
                    continue

                if size_kb > max_size:
                    if show_binary_notice:
                        lines.append(f"[Skipped: Exceeds size limit of {max_size} KB ({size_kb:.1f} KB)]\n")
                    skipped_size += 1
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    lines.append(content)
                    file_count += 1
                except Exception as e:
                    lines.append(f"[Error reading file: {e}]\n")

        lines.append("")
        lines.append("=" * 80)
        lines.append(f"SUMMARY: {file_count} files extracted")
        lines.append(f"         {skipped_binary} binary files skipped")
        lines.append(f"         {skipped_size} oversized files skipped")
        lines.append("=" * 80)

        if output_file:
            output_file.write_text("\n".join(lines), encoding="utf-8")

        return file_count, lines


# ---------------------------------------------------------------------------
# Interactive Shell
# ---------------------------------------------------------------------------

class Med9Shell(cmd.Cmd):
    intro = BANNER
    prompt = PROMPT

    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.core = Med9Core(self.config)
        self.current_dir = SCRIPT_DIR
        self.last_output: Optional[Path] = None

    def _parse_path(self, arg: str) -> Path:
        p = Path(arg).expanduser()
        if not p.is_absolute():
            p = self.current_dir / p
        return p.resolve()

    def emptyline(self):
        pass

    def default(self, line):
        print(f"[!] Unknown command: '{line}'. Type 'help' for available commands.")

    def do_extract(self, arg):
        if not arg.strip():
            print("[-] Usage: extract <path> [options]")
            return

        parts = arg.split()
        target = self._parse_path(parts[0])
        if not target.exists() or not target.is_dir():
            print(f"[!] Not a directory: {target}")
            return

        output = None
        max_size = None
        include_content = "--content" in parts or "-c" in parts

        for i, p in enumerate(parts):
            if p in ("--output", "-o") and i + 1 < len(parts):
                output = self._parse_path(parts[i + 1])
            if p in ("--max-size", "-m") and i + 1 < len(parts):
                try:
                    max_size = int(parts[i + 1])
                except ValueError:
                    print(f"[!] Invalid max-size value: {parts[i + 1]}")
                    return

        if not output:
            output = self.current_dir / f"{target.name}_dump.txt"

        print(f"[*] Extracting: {target}")
        print(f"[*] Output: {output}")

        if include_content:
            count, _ = self.core.extract(target, output, max_size)
            print(f"[+] Extracted {count} files to: {output}")
        else:
            self.core.extract_tree_only(target, output)
            print(f"[+] Tree saved to: {output}")

        self.last_output = output

    def do_tree(self, arg):
        path = self._parse_path(arg.strip() if arg.strip() else ".")
        if not path.exists() or not path.is_dir():
            print(f"[!] Not a directory: {path}")
            return

        print(f"\n{path.name}/")
        for line in self.core.generate_tree(path):
            print(line)
        print()

    def do_config(self, arg):
        parts = arg.split() if arg else []
        if not parts:
            print("\n[*] Current configuration:")
            for k, v in self.config.data.items():
                print(f"    {k:<20} = {v}")
            print(f"\n[*] Config file: {CONFIG_FILE}")
            return

        key = parts[0]
        if len(parts) < 2:
            print(f"[*] {key} = {self.config.get(key, '(not set)')}")
            return

        val = " ".join(parts[1:])

        if key == "max_size_kb":
            try:
                self.config.set(key, int(val))
            except ValueError:
                print(f"[!] max_size_kb must be an integer.")
                return
        elif key in ("ignore_dirs", "ignore_files", "binary_extensions"):
            self.config.set(key, [x.strip() for x in val.split(",")])
        elif key == "show_binary_notice":
            self.config.set(key, val.lower() in ("true", "1", "yes", "on"))
        else:
            self.config.set(key, val)

        print(f"[+] {key} set to: {self.config.get(key)}")

    def do_cd(self, arg):
        if not arg.strip():
            print(f"[*] Current: {self.current_dir}")
            return
        p = self._parse_path(arg.strip())
        if p.exists() and p.is_dir():
            self.current_dir = p
            print(f"[+] Changed to: {p}")
        else:
            print(f"[!] Not a directory: {p}")

    def do_pwd(self, arg):
        print(f"[*] {self.current_dir}")

    def do_ls(self, arg):
        path = self._parse_path(arg.strip() if arg.strip() else ".")
        if not path.exists() or not path.is_dir():
            print(f"[!] Not a directory: {path}")
            return

        try:
            entries = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except PermissionError:
            print(f"[!] Permission denied: {path}")
            return

        print(f"\n  Contents of {path}:")
        for entry in entries:
            marker = "[D]" if entry.is_dir() else "[F]"
            print(f"  {marker} {entry.name}")
        print()

    def do_open(self, arg):
        target = self.last_output
        if arg.strip():
            target = self._parse_path(arg.strip())

        if not target or not target.exists():
            print(f"[!] No file to open. Use 'extract' first or specify a valid file.")
            return

        print(f"[*] Opening: {target}")
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(str(target))
            elif system == "Darwin":
                subprocess.run(["open", str(target)], check=True)
            else:
                subprocess.run(["xdg-open", str(target)], check=True)
        except Exception as e:
            print(f"[!] Could not open file: {e}")

    def do_clear(self, arg):
        os.system("cls" if platform.system() == "Windows" else "clear")

    def do_exit(self, arg):
        print("[*] Goodbye!")
        return True

    def do_quit(self, arg):
        return self.do_exit(arg)

    def do_EOF(self, arg):
        print()
        return self.do_exit(arg)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    config = ConfigManager()
    core = Med9Core(config)

    # DIRECT CLICK EXECUTION MODE
    if len(sys.argv) == 1:
        target = SCRIPT_DIR
        output_file = target / "result.txt"

        lines = core.extract_tree_only(target, output_file=output_file)

        # Print tree output directly to screen
        for line in lines:
            print(line)

        print(f"\n[+] Output saved next to script at: {output_file}")
        
        # Keep window open until user presses Enter
        try:
            input("\n[Press Enter to exit / اضغط Enter للخروج]")
        except (KeyboardInterrupt, EOFError):
            pass
        return

    # CLI ARGUMENT PARSER
    parser = argparse.ArgumentParser(
        prog="med9",
        description="Med9 - Folder Content Extractor & Tree Viewer",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    extract_parser = subparsers.add_parser("extract", help="Extract folder contents to a report")
    extract_parser.add_argument("path", help="Target directory path")
    extract_parser.add_argument("-c", "--content", action="store_true", help="Include file contents in the report")
    extract_parser.add_argument("-o", "--output", help="Output file path")
    extract_parser.add_argument("-m", "--max-size", type=int, help="Max file size in KB")

    tree_parser = subparsers.add_parser("tree", help="Show directory tree")
    tree_parser.add_argument("path", nargs="?", default=".", help="Target directory path")

    config_parser = subparsers.add_parser("config", help="View or edit configuration")
    config_parser.add_argument("key", nargs="?", help="Config key")
    config_parser.add_argument("value", nargs="?", help="Config value")

    subparsers.add_parser("shell", help="Launch interactive Med9 shell")

    args = parser.parse_args()

    if args.command == "extract":
        target = Path(args.path).expanduser().resolve()
        if not target.exists() or not target.is_dir():
            print(f"[!] Not a directory: {target}")
            sys.exit(1)

        output = Path(args.output).expanduser().resolve() if args.output else Path(f"{target.name}_dump.txt")
        max_size = args.max_size

        if args.content:
            count, _ = core.extract(target, output, max_size)
            print(f"[+] Extracted {count} files to: {output}")
        else:
            core.extract_tree_only(target, output)
            print(f"[+] Tree saved to: {output}")

    elif args.command == "tree":
        target = Path(args.path).expanduser().resolve()
        if not target.exists() or not target.is_dir():
            print(f"[!] Not a directory: {target}")
            sys.exit(1)
        print(f"\n{target.name}/")
        for line in core.generate_tree(target):
            print(line)
        print()

    elif args.command == "config":
        if not args.key:
            print("[*] Current configuration:")
            for k, v in config.data.items():
                print(f"    {k:<20} = {v}")
            print(f"\n[*] Config file: {CONFIG_FILE}")
        elif not args.value:
            print(f"[*] {args.key} = {config.get(args.key, '(not set)')}")
        else:
            val = args.value
            if args.key == "max_size_kb":
                config.set(args.key, int(val))
            elif args.key in ("ignore_dirs", "ignore_files", "binary_extensions"):
                config.set(args.key, [x.strip() for x in val.split(",")])
            elif args.key == "show_binary_notice":
                config.set(args.key, val.lower() in ("true", "1", "yes", "on"))
            else:
                config.set(args.key, val)
            print(f"[+] {args.key} set to: {config.get(args.key)}")

    elif args.command == "shell":
        try:
            Med9Shell().cmdloop()
        except KeyboardInterrupt:
            print("\n[*] Interrupted. Goodbye!")


if __name__ == "__main__":
    main()
