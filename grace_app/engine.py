import os
from pathlib import Path
from typing import List, Set, Optional
from .models import ContextBlock
from .config import MAX_FILE_SIZE

class TokenEstimator:
    @staticmethod
    def estimate(text: str) -> int:
        return max(1, len(text) // 4)

    @staticmethod
    def format_count(count: int) -> str:
        if count < 1000:
            return f"{count} tokens"
        return f"{count/1000:.1f}k tokens"

class FileScanner:
    @staticmethod
    def scan_extensions(root_path: str, ignore_dirs: Set[str], max_exts: int = 60) -> List[str]:
        extensions: Set[str] = set()
        try:
            for dirpath, dirnames, filenames in os.walk(root_path):
                dirnames[:] = [d for d in dirnames if d not in ignore_dirs and not d.startswith('.')]
                for fname in filenames:
                    if fname.startswith('.'):
                        continue
                    ext = os.path.splitext(fname)[1].lower()
                    if ext:
                        extensions.add(ext)
                    if len(extensions) > max_exts:
                        break
                if len(extensions) > max_exts:
                    break
        except (PermissionError, OSError):
            pass
        return sorted(extensions)

    @staticmethod
    def list_entries(base_path: str, extensions: List[str], ignore_dirs: Set[str],
                     ignore_files: Set[str], content_filter: str = "") -> List[str]:
        exts = {e.strip().lower() for e in extensions if e.strip()}
        valid: List[str] = []
        try:
            for dirpath, dirnames, filenames in os.walk(base_path):
                dirnames[:] = [d for d in dirnames if d not in ignore_dirs and not d.startswith('.')]
                for fname in filenames:
                    if fname in ignore_files or fname.startswith('.'):
                        continue
                    ext = os.path.splitext(fname)[1].lower()
                    if exts and ext not in exts:
                        continue
                    if content_filter:
                        try:
                            with open(os.path.join(dirpath, fname), 'r', encoding='utf-8', errors='ignore') as fh:
                                if content_filter not in fh.read():
                                    continue
                        except Exception:
                            continue
                    valid.append(os.path.join(dirpath, fname))
        except (PermissionError, OSError):
            pass
        return valid

class ContextBuilder:
    @staticmethod
    def build_tree_string(tree: dict, prefix: str = "") -> List[str]:
        lines: List[str] = []
        keys = sorted(tree.keys())
        for i, key in enumerate(keys):
            is_last = i == len(keys) - 1
            connector = "\u2514\u2500\u2500 " if is_last else "\u251c\u2500\u2500 "
            if tree[key]:
                lines.append(f"{prefix}{connector}{key}/")
                ext = "    " if is_last else "\u2502   "
                lines.extend(ContextBuilder.build_tree_string(tree[key], prefix + ext))
            else:
                lines.append(f"{prefix}{connector}{key}")
        return lines

    @staticmethod
    def build(blocks: List[ContextBlock], selected_files: List[str],
              base_dir: str, mode: str, instruction: str,
              max_file_size: int = MAX_FILE_SIZE) -> str:
        parts: List[str] = []

        if blocks:
            parts.append("=== CONTEXT BLOCKS ===\n")
            for block in sorted(blocks, key=lambda b: b.order):
                parts.append(f"--- {block.name} ({block.category}) ---")
                parts.append(block.content)
                parts.append("")

        if selected_files and mode != "Files Only":
            tree_dict = {}
            for fp in sorted(selected_files):
                rel = os.path.relpath(fp, base_dir)
                curr = tree_dict
                for part in rel.split(os.sep):
                    curr = curr.setdefault(part, {})
            parts.append("=== PROJECT STRUCTURE ===")
            parts.append(".")
            parts.extend(ContextBuilder.build_tree_string(tree_dict))
            parts.append("")

        if mode != "Structure Only":
            parts.append("=== FILE CONTENTS ===\n")
            for fp in sorted(selected_files):
                rel = os.path.relpath(fp, base_dir)
                try:
                    size = os.path.getsize(fp)
                    if size > max_file_size:
                        parts.append(f"--- {rel} ---")
                        parts.append(f"[Omitted: {size/1024/1024:.1f}MB exceeds 1MB limit]\n")
                        continue
                    with open(fp, 'r', encoding='utf-8', errors='replace') as fh:
                        content = fh.read()
                    ext = os.path.splitext(rel)[1].lstrip('.') or 'text'
                    parts.append(f"--- {rel} ---")
                    parts.append(f"```{ext}")
                    parts.append(content)
                    parts.append("```\n")
                except Exception as e:
                    parts.append(f"--- {rel} ---")
                    parts.append(f"[Error: {e}]\n")

        if instruction:
            parts.append("=== YOUR TASK ===")
            parts.append(instruction)

        return "\n".join(parts)
