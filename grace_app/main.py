import os
import re
import json
import hashlib
import customtkinter as ctk
from tkinter import filedialog, messagebox
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Set
from pathlib import Path
from datetime import datetime

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

CONFIG_DIR = Path.home() / ".grace_manager"
PROFILES_FILE = CONFIG_DIR / "profiles.json"
RECENT_FILE = CONFIG_DIR / "recent_projects.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

@dataclass
class ContextBlock:
    id: str
    name: str
    content: str
    category: str = "general"
    enabled: bool = True
    order: int = 0

def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    for f in [PROFILES_FILE, RECENT_FILE, SETTINGS_FILE]:
        if not f.exists():
            if f == SETTINGS_FILE:
                f.write_text(json.dumps({"scaling": 100}))
            else:
                f.write_text("[]")

class TokenEstimator:
    @staticmethod
    def estimate(text: str) -> int:
        return max(1, len(text) // 4)

    @staticmethod
    def format_count(count: int) -> str:
        if count < 1000:
            return f"{count} tokens"
        return f"{count/1000:.1f}k tokens"

class FileTreeNode:
    def __init__(self, app, parent_node, widget_parent, path, is_dir, depth=0):
        self.app = app
        self.parent_node = parent_node
        self.widget_parent = widget_parent
        self.path = path
        self.is_dir = is_dir
        self.name = os.path.basename(path) or path
        self.depth = depth

        self.var = ctk.BooleanVar(value=False)
        self.file_mtime: float = 0
        if not is_dir:
            try:
                self.file_mtime = os.path.getmtime(path)
            except OSError:
                pass
        self.children: List[FileTreeNode] = []
        self.is_loaded = False
        self.is_expanded = False
        self.matches_filter = True

        indent = depth * 20
        self.frame = ctk.CTkFrame(widget_parent, fg_color="transparent", corner_radius=8)
        self.frame.pack(fill="x", pady=1)

        self.header_frame = ctk.CTkFrame(self.frame, fg_color="transparent", corner_radius=8)
        self.header_frame.pack(fill="x")

        if self.is_dir:
            self.btn_toggle = ctk.CTkButton(
                self.header_frame, text="▶", width=28, height=28,
                fg_color="transparent", text_color=("#6b7280", "#9ca3af"),
                hover_color=("#e5e7eb", "#374151"),
                corner_radius=6,
                command=self.toggle_expand
            )
            self.btn_toggle.pack(side="left", padx=(indent, 5))

            self.cb = ctk.CTkCheckBox(
                self.header_frame, text=f" {self.name}", variable=self.var,
                command=self.on_check, font=ctk.CTkFont(weight="bold", size=12),
                corner_radius=6
            )
            self.cb.pack(side="left", pady=2)

            self.content_frame = ctk.CTkFrame(self.frame, fg_color="transparent", corner_radius=8)
        else:
            ext = os.path.splitext(self.name)[1].lower()
            icon = {".py": "py", ".js": "js", ".ts": "ts", ".jsx": "jsx", ".tsx": "tsx",
                   ".md": "md", ".json": "{}", ".yaml": "y", ".yml": "y", ".xml": "<>",
                   ".html": "h", ".css": "#", ".toml": "t", ".cfg": "c", ".ini": "i"}.get(ext, ext.strip(".")[:2] or "..")

            self.cb = ctk.CTkCheckBox(
                self.header_frame, text=f"[{icon}] {self.name}", variable=self.var,
                command=self.on_check, font=ctk.CTkFont(size=12),
                corner_radius=6
            )
            self.cb.pack(side="left", padx=(indent + 33, 0), pady=2)

            try:
                size_kb = os.path.getsize(path) / 1024
            except OSError:
                size_kb = 0
            size_text = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb/1024:.1f}MB"
            self.size_label = ctk.CTkLabel(self.header_frame, text=size_text, text_color="#9ca3af",
                                           width=70, font=ctk.CTkFont(size=11))
            self.size_label.pack(side="right", padx=5)

    def toggle_expand(self):
        if not self.is_expanded:
            if not self.is_loaded:
                self.load_children()
            self.content_frame.pack(fill="x", padx=(25, 0))
            self.btn_toggle.configure(text="▼")
            self.is_expanded = True
        else:
            self.content_frame.pack_forget()
            self.btn_toggle.configure(text="▶")
            self.is_expanded = False

    def load_children(self):
        try:
            entries = sorted(os.listdir(self.path))
        except PermissionError:
            return

        exts = [e.strip().lower() for e in self.app.filter_extensions.get().split(',') if e.strip()]
        ig_dirs = set(d.strip() for d in self.app.filter_dirs.get().split(',') if d.strip())
        ig_files = set(f.strip() for f in self.app.filter_files.get().split(',') if f.strip())
        content_pattern = self.app.filter_content.get().strip()

        dirs, files = [], []
        for entry in entries:
            full_path = os.path.join(self.path, entry)
            if os.path.isdir(full_path):
                if entry not in ig_dirs and not entry.startswith('.'):
                    dirs.append(full_path)
            else:
                if entry in ig_files or entry.startswith('.'):
                    continue
                ext = os.path.splitext(entry)[1].lower()
                if exts and ext not in exts:
                    continue
                if content_pattern:
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            if content_pattern not in f.read():
                                continue
                    except Exception:
                        continue
                files.append(full_path)

        for d in sorted(dirs):
            child = FileTreeNode(self.app, self, self.content_frame, d, is_dir=True, depth=self.depth + 1)
            if self.var.get():
                child.var.set(True)
            self.children.append(child)

        for f in sorted(files):
            child = FileTreeNode(self.app, self, self.content_frame, f, is_dir=False, depth=self.depth + 1)
            if self.var.get():
                child.var.set(True)
            self.children.append(child)

        self.is_loaded = True

    def on_check(self):
        state = self.var.get()

        if self.is_dir and not self.is_loaded and state:
            self.load_children()

        if self.is_dir and self.is_loaded:
            self.set_children_state(state)

        if not state and self.parent_node:
            self.parent_node.uncheck_from_child()

        self.app.update_preview()

    def set_children_state(self, state):
        for child in self.children:
            child.var.set(state)
            if child.is_dir and child.is_loaded:
                child.set_children_state(state)

    def uncheck_from_child(self):
        self.var.set(False)
        if self.parent_node:
            self.parent_node.uncheck_from_child()

    def is_stale(self) -> bool:
        if self.is_dir:
            return False
        try:
            return os.path.getmtime(self.path) != self.file_mtime
        except OSError:
            return False

    def refresh_mtime(self):
        if not self.is_dir:
            try:
                self.file_mtime = os.path.getmtime(self.path)
            except OSError:
                pass

class ContextBlockEditor(ctk.CTkToplevel):
    def __init__(self, parent, block: Optional[ContextBlock] = None, callback=None):
        super().__init__(parent)
        self.title("Edit Context Block" if block else "New Context Block")
        self.geometry("600x420")
        self.callback = callback
        self.block = block

        self.configure(fg_color=("#f3f4f6", "#1f2937"))
        self.transient(parent)
        self.after(100, self._safe_grab)

        frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=12)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="Name:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        self.name_entry = ctk.CTkEntry(frame, placeholder_text="Block name...", corner_radius=8, height=36)
        self.name_entry.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(frame, text="Category:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        self.category_entry = ctk.CTkEntry(frame, placeholder_text="e.g., tech, requirements, constraints...",
                                           corner_radius=8, height=36)
        self.category_entry.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(frame, text="Content:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        self.content_text = ctk.CTkTextbox(frame, corner_radius=8, border_width=1,
                                           border_color=("#d1d5db", "#374151"))
        self.content_text.pack(fill="both", expand=True, pady=(0, 12))

        if block:
            self.name_entry.insert(0, block.name)
            self.category_entry.insert(0, block.category)
            self.content_text.insert("0.0", block.content)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy,
                      fg_color="transparent", text_color=("#374151", "#d1d5db"),
                      border_width=1, corner_radius=8, height=34).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Save", command=self.save,
                      fg_color="#059669", hover_color="#047857",
                      corner_radius=8, height=34).pack(side="right", padx=5)

    def _safe_grab(self):
        try:
            self.grab_set()
        except Exception:
            pass

    def save(self):
        name = self.name_entry.get().strip()
        content = self.content_text.get("0.0", "end").strip()
        category = self.category_entry.get().strip() or "general"

        if not name or not content:
            messagebox.showwarning("Required", "Name and content are required")
            return

        block = ContextBlock(
            id=self.block.id if self.block else hashlib.md5(name.encode()).hexdigest()[:8],
            name=name,
            content=content,
            category=category
        )

        if self.callback:
            self.callback(block)
        self.destroy()

class GraceContextApp(ctk.CTk):
    CORNER = 10
    SCALE_STEPS = [75, 100, 125, 150, 175, 200]

    def __init__(self):
        super().__init__()
        self.title("GRACE Context Manager")
        self.geometry("1400x900")
        self.minsize(900, 600)

        self.selected_directory = os.getcwd()
        self.root_nodes: List[FileTreeNode] = []
        self.context_blocks: List[ContextBlock] = []
        self.max_file_size = 1024 * 1024
        self.detected_extensions: Dict[str, ctk.BooleanVar] = {}
        self._scaling = 100

        ensure_config_dir()
        self._load_settings()
        self._load_context_blocks()
        self._build_ui()
        self._load_recent_project()

    def _load_settings(self):
        try:
            if SETTINGS_FILE.exists():
                data = json.loads(SETTINGS_FILE.read_text())
                sc = data.get("scaling", 100)
                sc = int(sc)
                valid = self.SCALE_STEPS
                closest = min(valid, key=lambda v: abs(v - sc))
                self._scaling = closest
                self._apply_scaling()
        except Exception:
            self._scaling = 100

    def _save_settings(self):
        SETTINGS_FILE.write_text(json.dumps({"scaling": self._scaling}, indent=2))

    def _apply_scaling(self):
        factor = self._scaling / 100.0
        ctk.set_widget_scaling(factor)
        ctk.set_window_scaling(factor)

    def _load_context_blocks(self):
        try:
            if PROFILES_FILE.exists():
                data = json.loads(PROFILES_FILE.read_text())
                self.context_blocks = [ContextBlock(**b) for b in data]
        except Exception:
            self.context_blocks = [
                ContextBlock("tech", "Tech Stack", "Python 3.10+, FastAPI, PostgreSQL", "tech"),
                ContextBlock("rules", "Coding Rules", "Use type hints. Write docstrings. No global state.", "constraints"),
            ]

    def _save_context_blocks(self):
        data = [asdict(b) for b in self.context_blocks]
        PROFILES_FILE.write_text(json.dumps(data, indent=2))

    def _load_recent_project(self):
        try:
            if RECENT_FILE.exists():
                recent = json.loads(RECENT_FILE.read_text())
                if recent and os.path.exists(recent[0]):
                    self.selected_directory = recent[0]
                    self.dir_label.configure(text=f" {self.selected_directory}")
                    self.refresh_file_list()
        except Exception:
            pass

    def _save_recent_project(self):
        try:
            recent = [self.selected_directory]
            if RECENT_FILE.exists():
                old = json.loads(RECENT_FILE.read_text())
                recent.extend([p for p in old if p != self.selected_directory][:4])
            RECENT_FILE.write_text(json.dumps(recent))
        except Exception:
            pass

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=340, corner_radius=self.CORNER)
        sidebar.grid(row=0, column=0, sticky="ns", padx=(12, 6), pady=12)
        sidebar.grid_propagate(False)

        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=12)

        self.dir_label = ctk.CTkLabel(header, text=f" {self.selected_directory}",
                                       font=ctk.CTkFont(size=12), wraplength=280)
        self.dir_label.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(header, text="Browse", width=32, height=32, corner_radius=8,
                       command=self.change_directory).pack(side="right")

        blocks_frame = ctk.CTkFrame(sidebar, corner_radius=self.CORNER)
        blocks_frame.pack(fill="both", expand=True, padx=12, pady=5)

        blocks_hdr = ctk.CTkFrame(blocks_frame, fg_color="transparent")
        blocks_hdr.pack(fill="x", padx=8, pady=(8, 0))

        ctk.CTkLabel(blocks_hdr, text="Context Blocks", font=ctk.CTkFont(weight="bold", size=13)).pack(side="left")

        ctk.CTkButton(blocks_hdr, text="+", width=30, height=30, corner_radius=8,
                       fg_color="#059669", hover_color="#047857",
                       command=self.add_context_block).pack(side="right", padx=2)
        ctk.CTkButton(blocks_hdr, text="✎", width=30, height=30, corner_radius=8,
                       fg_color="transparent", text_color=("#374151", "#d1d5db"),
                       border_width=1, command=self.edit_context_block).pack(side="right", padx=2)
        ctk.CTkButton(blocks_hdr, text="✕", width=30, height=30, corner_radius=8,
                       fg_color="transparent", text_color="#ef4444",
                       border_width=1, command=self.delete_context_block).pack(side="right", padx=2)

        self.blocks_list = ctk.CTkScrollableFrame(blocks_frame, corner_radius=8)
        self.blocks_list.pack(fill="both", expand=True, padx=8, pady=8)

        self._refresh_blocks_list()

        scale_frame = ctk.CTkFrame(sidebar, corner_radius=self.CORNER)
        scale_frame.pack(fill="x", padx=12, pady=(0, 5))

        scale_hdr = ctk.CTkFrame(scale_frame, fg_color="transparent")
        scale_hdr.pack(fill="x", padx=8, pady=(8, 2))
        ctk.CTkLabel(scale_hdr, text="UI Scale",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")

        self.scale_buttons: Dict[int, ctk.CTkButton] = {}
        btn_frame = ctk.CTkFrame(scale_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=8, pady=(2, 8))

        btn_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        for i, step in enumerate(self.SCALE_STEPS):
            btn = ctk.CTkButton(btn_frame, text=f"{step}%",
                                width=0, height=28, corner_radius=6,
                                font=ctk.CTkFont(size=10),
                                command=lambda s=step: self._set_scale(s))
            btn.grid(row=0, column=i, padx=1, sticky="ew")
            self.scale_buttons[step] = btn

        self._highlight_scale_button()

        user_frame = ctk.CTkFrame(sidebar, corner_radius=self.CORNER)
        user_frame.pack(fill="x", padx=12, pady=(0, 5))

        ctk.CTkLabel(user_frame, text="Your Instruction", font=ctk.CTkFont(weight="bold", size=13)).pack(anchor="w", padx=8, pady=(8, 4))
        self.user_instruction = ctk.CTkTextbox(user_frame, height=100, corner_radius=8,
                                               border_width=1,
                                               border_color=("#d1d5db", "#374151"))
        self.user_instruction.pack(fill="x", padx=8, pady=(0, 8))
        self.user_instruction.insert("0.0", "Based on the context above, implement...")

        self.user_instruction.bind("<KeyRelease>", lambda e: self.update_preview())

        action_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        action_frame.pack(fill="x", padx=12, pady=(0, 12))

        self.refresh_btn = ctk.CTkButton(action_frame, text="Refresh Context", height=40,
                                          corner_radius=10,
                                          fg_color="transparent", text_color=("#374151", "#d1d5db"),
                                          border_width=1, border_color=("#d1d5db", "#374151"),
                                          hover_color=("#e5e7eb", "#374151"),
                                          command=self.refresh_context)
        self.refresh_btn.pack(fill="x", pady=(0, 6))

        self.copy_btn = ctk.CTkButton(action_frame, text="Copy Context", height=44,
                                       corner_radius=10,
                                       command=self.copy_context,
                                       fg_color="#6366f1", hover_color="#4f46e5")
        self.copy_btn.pack(fill="x", pady=(0, 4))

        self.token_label = ctk.CTkLabel(action_frame, text="~0 tokens",
                                        text_color="#9ca3af", font=ctk.CTkFont(size=12))
        self.token_label.pack()

    def _build_main_area(self):
        main = ctk.CTkFrame(self, corner_radius=self.CORNER)
        main.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(2, weight=1)

        filter_frame = ctk.CTkFrame(main, corner_radius=self.CORNER)
        filter_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        filters_inner = ctk.CTkFrame(filter_frame, fg_color="transparent")
        filters_inner.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(filters_inner, text="Extensions:", font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=(0, 4), sticky="e")
        self.filter_extensions = ctk.CTkEntry(filters_inner, width=140, corner_radius=8, height=32,
                                              font=ctk.CTkFont(size=12))
        self.filter_extensions.grid(row=0, column=1, padx=(0, 12))
        self.filter_extensions.insert(0, ".py, .md, .txt, .json, .yaml, .toml")

        ctk.CTkLabel(filters_inner, text="Ignore Dirs:", font=ctk.CTkFont(size=11)).grid(row=0, column=2, padx=(0, 4), sticky="e")
        self.filter_dirs = ctk.CTkEntry(filters_inner, width=140, corner_radius=8, height=32,
                                        font=ctk.CTkFont(size=12))
        self.filter_dirs.grid(row=0, column=3, padx=(0, 12))
        self.filter_dirs.insert(0, ".git, __pycache__, venv, node_modules, .venv, env")

        ctk.CTkLabel(filters_inner, text="Ignore Files:", font=ctk.CTkFont(size=11)).grid(row=1, column=0, padx=(0, 4), sticky="e", pady=(8, 0))
        self.filter_files = ctk.CTkEntry(filters_inner, width=140, corner_radius=8, height=32,
                                         font=ctk.CTkFont(size=12))
        self.filter_files.grid(row=1, column=1, padx=(0, 12), pady=(8, 0))
        self.filter_files.insert(0, ".env, secrets.py, credentials.json")

        ctk.CTkLabel(filters_inner, text="Contains:", font=ctk.CTkFont(size=11)).grid(row=1, column=2, padx=(0, 4), sticky="e", pady=(8, 0))
        self.filter_content = ctk.CTkEntry(filters_inner, width=140, placeholder_text="text in file...",
                                           corner_radius=8, height=32, font=ctk.CTkFont(size=12))
        self.filter_content.grid(row=1, column=3, padx=(0, 4), pady=(8, 0))

        apply_btn = ctk.CTkButton(filters_inner, text="Apply Filters", width=100, height=32,
                                   corner_radius=8, command=self.refresh_file_list,
                                   fg_color="#6366f1", hover_color="#4f46e5")
        apply_btn.grid(row=0, column=4, rowspan=2, padx=(8, 0))

        ext_frame = ctk.CTkFrame(main, corner_radius=self.CORNER)
        ext_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ext_inner = ctk.CTkFrame(ext_frame, fg_color="transparent")
        ext_inner.pack(fill="x", padx=12, pady=6)

        ext_hdr = ctk.CTkFrame(ext_inner, fg_color="transparent")
        ext_hdr.pack(fill="x")
        ctk.CTkLabel(ext_hdr, text="Detected Extensions", font=ctk.CTkFont(weight="bold", size=12)).pack(side="left")

        self.ext_select_all_btn = ctk.CTkButton(ext_hdr, text="All", width=42, height=24,
                                                 corner_radius=6, font=ctk.CTkFont(size=10),
                                                 fg_color="transparent", text_color=("#374151", "#d1d5db"),
                                                 border_width=1, command=self.select_all_extensions)
        self.ext_select_all_btn.pack(side="right", padx=2)

        self.ext_deselect_all_btn = ctk.CTkButton(ext_hdr, text="None", width=42, height=24,
                                                   corner_radius=6, font=ctk.CTkFont(size=10),
                                                   fg_color="transparent", text_color=("#374151", "#d1d5db"),
                                                   border_width=1, command=self.deselect_all_extensions)
        self.ext_deselect_all_btn.pack(side="right", padx=2)

        ctk.CTkButton(ext_hdr, text="Detect", width=54, height=24, corner_radius=6,
                       font=ctk.CTkFont(size=10),
                       fg_color="#6366f1", hover_color="#4f46e5",
                       command=self.detect_extensions).pack(side="right", padx=4)

        self.ext_scroll = ctk.CTkScrollableFrame(ext_inner, height=60, corner_radius=8)
        self.ext_scroll.pack(fill="x", padx=(0, 0), pady=(4, 2))

        files_frame = ctk.CTkFrame(main, corner_radius=self.CORNER)
        files_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 5))

        files_header = ctk.CTkFrame(files_frame, fg_color="transparent")
        files_header.pack(fill="x", padx=8, pady=8)

        ctk.CTkLabel(files_header, text="Project Files", font=ctk.CTkFont(weight="bold", size=13)).pack(side="left")

        ctk.CTkButton(files_header, text="All", width=44, height=28, corner_radius=6,
                       font=ctk.CTkFont(size=11),
                       fg_color="transparent", text_color=("#374151", "#d1d5db"),
                       border_width=1, command=self.select_all).pack(side="right", padx=2)
        ctk.CTkButton(files_header, text="None", width=44, height=28, corner_radius=6,
                       font=ctk.CTkFont(size=11),
                       fg_color="transparent", text_color=("#374151", "#d1d5db"),
                       border_width=1, command=self.deselect_all).pack(side="right", padx=2)

        search_frame = ctk.CTkFrame(files_frame, fg_color="transparent")
        search_frame.pack(fill="x", padx=8, pady=(0, 6))

        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search files...",
                                         corner_radius=8, height=32)
        self.search_entry.pack(fill="x")
        self.search_entry.bind("<KeyRelease>", self.filter_tree_by_search)

        self.files_scroll = ctk.CTkScrollableFrame(files_frame, corner_radius=8)
        self.files_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        preview_frame = ctk.CTkFrame(main, corner_radius=self.CORNER)
        preview_frame.grid(row=2, column=1, sticky="nsew", padx=(5, 0))

        preview_header = ctk.CTkFrame(preview_frame, fg_color="transparent")
        preview_header.pack(fill="x", padx=8, pady=8)

        ctk.CTkLabel(preview_header, text="Context Preview", font=ctk.CTkFont(weight="bold", size=13)).pack(side="left")

        self.preview_mode = ctk.CTkOptionMenu(preview_header, values=["Full", "Structure Only", "Files Only"],
                                              command=self.change_preview_mode, width=130,
                                              corner_radius=8, font=ctk.CTkFont(size=12))
        self.preview_mode.pack(side="right")

        self.preview_text = ctk.CTkTextbox(preview_frame, font=ctk.CTkFont(family="Courier", size=11),
                                           corner_radius=8, border_width=1,
                                           border_color=("#d1d5db", "#374151"))
        self.preview_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _refresh_blocks_list(self):
        for w in self.blocks_list.winfo_children():
            w.destroy()

        categories = {}
        for block in sorted(self.context_blocks, key=lambda b: (b.category, b.order)):
            if block.category not in categories:
                categories[block.category] = []
            categories[block.category].append(block)

        self.block_vars = {}
        for cat, blocks in categories.items():
            cat_label = ctk.CTkLabel(self.blocks_list, text=f"  {cat}",
                                     text_color="#6b7280", font=ctk.CTkFont(size=11, weight="bold"))
            cat_label.pack(anchor="w", pady=(8, 2))

            for block in blocks:
                var = ctk.BooleanVar(value=block.enabled)
                self.block_vars[block.id] = var

                cb = ctk.CTkCheckBox(self.blocks_list, text=block.name, variable=var,
                                    command=self.update_preview,
                                    font=ctk.CTkFont(size=12),
                                    corner_radius=6)
                cb.pack(anchor="w", padx=12, pady=1)

    def add_context_block(self):
        ContextBlockEditor(self, callback=self._on_block_saved)

    def edit_context_block(self):
        selected_id = None
        for bid, var in self.block_vars.items():
            if var.get():
                selected_id = bid
                break

        if not selected_id:
            messagebox.showinfo("Select", "Check a block to edit")
            return

        block = next((b for b in self.context_blocks if b.id == selected_id), None)
        if block:
            ContextBlockEditor(self, block=block, callback=self._on_block_saved)

    def delete_context_block(self):
        to_delete = [bid for bid, var in self.block_vars.items() if var.get()]
        if not to_delete:
            messagebox.showinfo("Select", "Check blocks to delete")
            return

        if messagebox.askyesno("Confirm", f"Delete {len(to_delete)} block(s)?"):
            self.context_blocks = [b for b in self.context_blocks if b.id not in to_delete]
            self._save_context_blocks()
            self._refresh_blocks_list()
            self.update_preview()

    def _on_block_saved(self, block: ContextBlock):
        existing = next((i for i, b in enumerate(self.context_blocks) if b.id == block.id), None)
        if existing is not None:
            self.context_blocks[existing] = block
        else:
            block.order = len(self.context_blocks)
            self.context_blocks.append(block)

        self._save_context_blocks()
        self._refresh_blocks_list()
        self.update_preview()

    def change_directory(self):
        path = filedialog.askdirectory(initialdir=self.selected_directory)
        if path:
            self.selected_directory = path
            self.dir_label.configure(text=f" {self.selected_directory}")
            self._save_recent_project()
            self.refresh_file_list()

    def detect_extensions(self):
        extensions: Set[str] = set()
        ig_dirs = set(d.strip() for d in self.filter_dirs.get().split(',') if d.strip())

        try:
            for root, dirs, files in os.walk(self.selected_directory):
                dirs[:] = [d for d in dirs if d not in ig_dirs and not d.startswith('.')]
                for f in files:
                    if f.startswith('.'):
                        continue
                    ext = os.path.splitext(f)[1].lower()
                    if ext:
                        extensions.add(ext)
                if len(extensions) > 60:
                    break
        except PermissionError:
            pass

        for w in self.ext_scroll.winfo_children():
            w.destroy()

        self.detected_extensions.clear()

        sorted_exts = sorted(extensions)

        self._ext_inner_frame = ctk.CTkFrame(self.ext_scroll, fg_color="transparent")
        self._ext_inner_frame.pack(anchor="w", padx=4, pady=4)

        cols_per_row = 8
        for i, ext in enumerate(sorted_exts):
            var = ctk.BooleanVar(value=True)
            self.detected_extensions[ext] = var

            cb = ctk.CTkCheckBox(self._ext_inner_frame, text=ext, variable=var,
                                command=self._on_extension_toggle,
                                font=ctk.CTkFont(size=11),
                                corner_radius=4,
                                width=60)
            cb.grid(row=i // cols_per_row, column=i % cols_per_row, padx=3, pady=2, sticky="w")

        self._on_extension_toggle()

    def select_all_extensions(self):
        for var in self.detected_extensions.values():
            var.set(True)
        self._on_extension_toggle()

    def deselect_all_extensions(self):
        for var in self.detected_extensions.values():
            var.set(False)
        self._on_extension_toggle()

    def _on_extension_toggle(self):
        selected = sorted([ext for ext, var in self.detected_extensions.items() if var.get()])
        self.filter_extensions.delete(0, "end")
        if selected:
            self.filter_extensions.insert(0, ", ".join(selected))

    def refresh_file_list(self):
        for w in self.files_scroll.winfo_children():
            w.destroy()
        self.root_nodes.clear()

        try:
            entries = sorted(os.listdir(self.selected_directory))
        except PermissionError:
            return

        exts = [e.strip().lower() for e in self.filter_extensions.get().split(',') if e.strip()]
        ig_dirs = set(d.strip() for d in self.filter_dirs.get().split(',') if d.strip())
        ig_files = set(f.strip() for f in self.filter_files.get().split(',') if f.strip())

        dirs, files = [], []
        for entry in entries:
            full_path = os.path.join(self.selected_directory, entry)
            if os.path.isdir(full_path):
                if entry not in ig_dirs and not entry.startswith('.'):
                    dirs.append(full_path)
            else:
                if entry in ig_files or entry.startswith('.'):
                    continue
                ext = os.path.splitext(entry)[1].lower()
                if exts and ext not in exts:
                    continue
                files.append(full_path)

        for d in dirs:
            node = FileTreeNode(self, None, self.files_scroll, d, is_dir=True)
            self.root_nodes.append(node)

        for f in files:
            node = FileTreeNode(self, None, self.files_scroll, f, is_dir=False)
            self.root_nodes.append(node)

        self.update_preview()

    def filter_tree_by_search(self, event=None):
        return

    def select_all(self):
        for node in self.root_nodes:
            node.var.set(True)
            node.on_check()
        self.update_preview()

    def deselect_all(self):
        for node in self.root_nodes:
            node.var.set(False)
            node.on_check()
        self.update_preview()

    def walk_and_filter(self, base_path) -> List[str]:
        exts = [e.strip().lower() for e in self.filter_extensions.get().split(',') if e.strip()]
        ig_dirs = set(d.strip() for d in self.filter_dirs.get().split(',') if d.strip())
        ig_files = set(f.strip() for f in self.filter_files.get().split(',') if f.strip())

        valid = []
        for root, dirs, files in os.walk(base_path):
            dirs[:] = [d for d in dirs if d not in ig_dirs and not d.startswith('.')]
            for f in files:
                if f in ig_files or f.startswith('.'):
                    continue
                ext = os.path.splitext(f)[1].lower()
                if exts and ext not in exts:
                    continue
                valid.append(os.path.join(root, f))
        return valid

    def get_selected_files(self) -> List[str]:
        selected_files = []

        def traverse_node(node):
            if not node.is_dir:
                if node.var.get():
                    selected_files.append(node.path)
            else:
                if node.var.get() and not node.is_loaded:
                    node.load_children()
                    node.set_children_state(True)

                if node.is_loaded:
                    for child in node.children:
                        traverse_node(child)

        for root_node in self.root_nodes:
            traverse_node(root_node)

        return selected_files

    def get_stale_files(self) -> List[str]:
        stale = []

        def traverse_node(node):
            if not node.is_dir:
                if node.var.get() and node.is_stale():
                    stale.append(node.path)
            elif node.is_loaded:
                for child in node.children:
                    traverse_node(child)

        for root_node in self.root_nodes:
            traverse_node(root_node)
        return stale

    def refresh_context(self):
        stale_files = self.get_stale_files()
        stale_count = len(stale_files)

        for root_node in self.root_nodes:
            def refresh_node(node):
                if not node.is_dir:
                    node.refresh_mtime()
                elif node.is_loaded:
                    for child in node.children:
                        refresh_node(child)
            refresh_node(root_node)

        self.update_preview()

        self.refresh_btn.configure(text="Context Refreshed")
        msg = f"Refreshed {stale_count} changed file(s)" if stale_count > 0 else "No file changes detected"
        self.token_label.configure(text=msg, text_color="#6366f1")
        self.after(2000, lambda: self.token_label.configure(
            text=f"~{TokenEstimator.format_count(TokenEstimator.estimate(self.preview_text.get('0.0', 'end')))}",
            text_color="#9ca3af"))

    def build_tree_string(self, tree: dict, prefix: str = "") -> List[str]:
        lines = []
        keys = sorted(tree.keys())
        for i, key in enumerate(keys):
            is_last = i == len(keys) - 1
            connector = "└── " if is_last else "├── "

            if tree[key]:
                lines.append(f"{prefix}{connector}{key}/")
                ext = "    " if is_last else "│   "
                lines.extend(self.build_tree_string(tree[key], prefix + ext))
            else:
                lines.append(f"{prefix}{connector}{key}")
        return lines

    def build_context(self) -> str:
        mode = self.preview_mode.get()
        parts = []

        enabled_blocks = [b for b in self.context_blocks
                         if self.block_vars.get(b.id, ctk.BooleanVar(value=b.enabled)).get()]

        if enabled_blocks:
            parts.append("=== CONTEXT BLOCKS ===\n")
            for block in sorted(enabled_blocks, key=lambda b: b.order):
                parts.append(f"--- {block.name} ({block.category}) ---")
                parts.append(block.content)
                parts.append("")

        selected = self.get_selected_files()

        if selected and mode != "Files Only":
            tree_dict = {}
            for fp in selected:
                rel = os.path.relpath(fp, self.selected_directory)
                curr = tree_dict
                for part in rel.split(os.sep):
                    curr = curr.setdefault(part, {})

            parts.append("=== PROJECT STRUCTURE ===")
            parts.append(".")
            parts.extend(self.build_tree_string(tree_dict))
            parts.append("")

        if mode != "Structure Only":
            parts.append("=== FILE CONTENTS ===\n")

            for fp in selected:
                rel = os.path.relpath(fp, self.selected_directory)
                try:
                    size = os.path.getsize(fp)
                    if size > self.max_file_size:
                        parts.append(f"--- {rel} ---")
                        parts.append(f"[Omitted: {size/1024/1024:.1f}MB exceeds 1MB limit]\n")
                        continue

                    with open(fp, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()

                    ext = os.path.splitext(rel)[1].lstrip('.') or 'text'
                    parts.append(f"--- {rel} ---")
                    parts.append(f"```{ext}")
                    parts.append(content)
                    parts.append("```\n")
                except Exception as e:
                    parts.append(f"--- {rel} ---")
                    parts.append(f"[Error: {e}]\n")

        user_inst = self.user_instruction.get("0.0", "end").strip()
        if user_inst:
            parts.append("=== YOUR TASK ===")
            parts.append(user_inst)

        return "\n".join(parts)

    def update_preview(self):
        context = self.build_context()
        self.preview_text.delete("0.0", "end")
        self.preview_text.insert("0.0", context)

        tokens = TokenEstimator.estimate(context)
        self.token_label.configure(text=f"~{TokenEstimator.format_count(tokens)}")

    def change_preview_mode(self, mode):
        self.update_preview()

    def copy_context(self):
        context = self.build_context()
        self.clipboard_clear()
        self.clipboard_append(context)
        self.update()

        self.copy_btn.configure(text="Copied!", fg_color="#059669", hover_color="#047857")
        self.after(2000, lambda: self.copy_btn.configure(text="Copy Context", fg_color="#6366f1", hover_color="#4f46e5"))

    def _set_scale(self, value: int):
        self._scaling = value
        self._apply_scaling()
        self._save_settings()
        self._highlight_scale_button()

    def _highlight_scale_button(self):
        for step, btn in self.scale_buttons.items():
            if step == self._scaling:
                btn.configure(fg_color="#6366f1", hover_color="#4f46e5",
                              text_color="white")
            else:
                btn.configure(fg_color="transparent",
                              text_color=("#374151", "#d1d5db"),
                              border_width=1,
                              hover_color=("#e5e7eb", "#374151"))

def main():
    app = GraceContextApp()
    app.mainloop()

if __name__ == "__main__":
    main()
