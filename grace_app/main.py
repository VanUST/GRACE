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
ctk.set_default_color_theme("blue")

CONFIG_DIR = Path.home() / ".grace_manager"
PROFILES_FILE = CONFIG_DIR / "profiles.json"
PRESETS_FILE = CONFIG_DIR / "filter_presets.json"
RECENT_FILE = CONFIG_DIR / "recent_projects.json"

@dataclass
class ContextBlock:
    id: str
    name: str
    content: str
    category: str = "general"
    enabled: bool = True
    order: int = 0

@dataclass 
class FilterPreset:
    name: str
    extensions: str
    ignore_dirs: str
    ignore_files: str
    content_pattern: str = ""

@dataclass
class ProjectProfile:
    name: str
    path: str
    context_blocks: List[dict] = field(default_factory=list)
    selected_files: List[str] = field(default_factory=list)
    filter_preset: str = "default"

def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    for f in [PROFILES_FILE, PRESETS_FILE, RECENT_FILE]:
        if not f.exists():
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
        self.children: List[FileTreeNode] = []
        self.is_loaded = False
        self.is_expanded = False
        self.matches_filter = True
        
        indent = depth * 20
        self.frame = ctk.CTkFrame(widget_parent, fg_color="transparent")
        self.frame.pack(fill="x", pady=1)
        
        self.header_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.header_frame.pack(fill="x")
        
        if self.is_dir:
            self.btn_toggle = ctk.CTkButton(
                self.header_frame, text="▶", width=25, height=25,
                fg_color="transparent", text_color=("gray10", "gray90"),
                hover_color=("#e0e0e0", "#444444"),
                command=self.toggle_expand
            )
            self.btn_toggle.pack(side="left", padx=(indent, 5))
            
            self.cb = ctk.CTkCheckBox(
                self.header_frame, text=f"📁 {self.name}", variable=self.var,
                command=self.on_check, font=ctk.CTkFont(weight="bold")
            )
            self.cb.pack(side="left", pady=2)
            
            self.content_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        else:
            ext = os.path.splitext(self.name)[1].lower()
            icon = {"py": "🐍", "js": "📜", "ts": "📘", "md": "📝", "json": "📋", 
                   "yaml": "⚙️", "yml": "⚙️", "xml": "📄", "html": "🌐", "css": "🎨"}.get(ext.strip("."), "📄")
            
            self.cb = ctk.CTkCheckBox(
                self.header_frame, text=f"{icon} {self.name}", variable=self.var,
                command=self.on_check
            )
            self.cb.pack(side="left", padx=(indent + 30, 0), pady=2)
            
            size_kb = os.path.getsize(path) / 1024 if os.path.exists(path) else 0
            size_text = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb/1024:.1f}MB"
            self.size_label = ctk.CTkLabel(self.header_frame, text=size_text, text_color="gray", width=70)
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
                    except:
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
        
        # Handle edge case: if checking a closed folder, load its children first
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

class ContextBlockEditor(ctk.CTkToplevel):
    def __init__(self, parent, block: Optional[ContextBlock] = None, callback=None):
        super().__init__(parent)
        self.title("Edit Context Block" if block else "New Context Block")
        self.geometry("600x400")
        self.callback = callback
        self.block = block
        
        self.transient(parent)
        self.after(100, self._safe_grab)
        
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="Name:").pack(anchor="w")
        self.name_entry = ctk.CTkEntry(frame, placeholder_text="Block name...")
        self.name_entry.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(frame, text="Category:").pack(anchor="w")
        self.category_entry = ctk.CTkEntry(frame, placeholder_text="e.g., tech, requirements, constraints...")
        self.category_entry.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(frame, text="Content:").pack(anchor="w")
        self.content_text = ctk.CTkTextbox(frame)
        self.content_text.pack(fill="both", expand=True, pady=(0, 10))
        
        if block:
            self.name_entry.insert(0, block.name)
            self.category_entry.insert(0, block.category)
            self.content_text.insert("0.0", block.content)
        
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        ctk.CTkButton(btn_frame, text="Save", command=self.save, fg_color="#2b8a3e").pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy).pack(side="right")

    def _safe_grab(self):
        try:
            self.grab_set()
        except:
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
    def __init__(self):
        super().__init__()
        self.title("GRACE Context Manager")
        self.geometry("1400x900")
        
        self.selected_directory = os.getcwd()
        self.root_nodes: List[FileTreeNode] = []
        self.context_blocks: List[ContextBlock] = []
        self.max_file_size = 1024 * 1024
        self.preview_dirty = True
        self.cached_preview = ""
        
        ensure_config_dir()
        self._load_context_blocks()
        self._build_ui()
        self._load_recent_project()

    def _load_context_blocks(self):
        try:
            if PROFILES_FILE.exists():
                data = json.loads(PROFILES_FILE.read_text())
                self.context_blocks = [ContextBlock(**b) for b in data]
        except:
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
                    self.dir_label.configure(text=f"📁 {self.selected_directory}")
                    self.refresh_file_list()
        except:
            pass

    def _save_recent_project(self):
        try:
            recent = [self.selected_directory]
            if RECENT_FILE.exists():
                old = json.loads(RECENT_FILE.read_text())
                recent.extend([p for p in old if p != self.selected_directory][:4])
            RECENT_FILE.write_text(json.dumps(recent))
        except:
            pass

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self._build_sidebar()
        self._build_main_area()

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=320)
        sidebar.grid(row=0, column=0, sticky="ns", padx=10, pady=10)
        sidebar.grid_propagate(False)
        
        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=10)
        
        self.dir_label = ctk.CTkLabel(header, text=f"📁 {self.selected_directory}", 
                                       font=ctk.CTkFont(size=12), wraplength=280)
        self.dir_label.pack(side="left", fill="x", expand=True)
        
        ctk.CTkButton(header, text="📂", width=30, command=self.change_directory).pack(side="right")
        
        blocks_frame = ctk.CTkFrame(sidebar)
        blocks_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ctk.CTkLabel(blocks_frame, text="Context Blocks", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=5)
        
        btn_row = ctk.CTkFrame(blocks_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=5, pady=5)
        ctk.CTkButton(btn_row, text="+ New", width=60, command=self.add_context_block).pack(side="left")
        ctk.CTkButton(btn_row, text="Edit", width=50, command=self.edit_context_block).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="Del", width=40, fg_color="#b22222", command=self.delete_context_block).pack(side="left")
        
        self.blocks_list = ctk.CTkScrollableFrame(blocks_frame)
        self.blocks_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        self._refresh_blocks_list()
        
        user_frame = ctk.CTkFrame(sidebar)
        user_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(user_frame, text="Your Instruction", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=5)
        self.user_instruction = ctk.CTkTextbox(user_frame, height=100)
        self.user_instruction.pack(fill="x", padx=5, pady=5)
        self.user_instruction.insert("0.0", "Based on the context above, implement...")
        
        self.user_instruction.bind("<KeyRelease>", lambda e: self.update_preview())
        
        action_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        action_frame.pack(fill="x", padx=10, pady=10)
        
        self.copy_btn = ctk.CTkButton(action_frame, text="📋 Copy Context", height=45,
                                       command=self.copy_context, fg_color="#2b8a3e")
        self.copy_btn.pack(fill="x", pady=5)
        
        self.token_label = ctk.CTkLabel(action_frame, text="~0 tokens", text_color="gray")
        self.token_label.pack()

    def _build_main_area(self):
        main = ctk.CTkFrame(self)
        main.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(1, weight=1)
        
        filter_frame = ctk.CTkFrame(main)
        filter_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        filters_inner = ctk.CTkFrame(filter_frame, fg_color="transparent")
        filters_inner.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(filters_inner, text="Extensions:").grid(row=0, column=0, padx=5)
        self.filter_extensions = ctk.CTkEntry(filters_inner, width=150)
        self.filter_extensions.grid(row=0, column=1, padx=5)
        self.filter_extensions.insert(0, ".py, .md, .txt, .json, .yaml, .toml")
        
        ctk.CTkLabel(filters_inner, text="Ignore Dirs:").grid(row=0, column=2, padx=5)
        self.filter_dirs = ctk.CTkEntry(filters_inner, width=150)
        self.filter_dirs.grid(row=0, column=3, padx=5)
        self.filter_dirs.insert(0, ".git, __pycache__, venv, node_modules, .venv, env")
        
        ctk.CTkLabel(filters_inner, text="Ignore Files:").grid(row=1, column=0, padx=5, pady=5)
        self.filter_files = ctk.CTkEntry(filters_inner, width=150)
        self.filter_files.grid(row=1, column=1, padx=5, pady=5)
        self.filter_files.insert(0, ".env, secrets.py, credentials.json")
        
        ctk.CTkLabel(filters_inner, text="Contains:").grid(row=1, column=2, padx=5, pady=5)
        self.filter_content = ctk.CTkEntry(filters_inner, width=150, placeholder_text="text in file...")
        self.filter_content.grid(row=1, column=3, padx=5, pady=5)
        
        btn_row = ctk.CTkFrame(filters_inner, fg_color="transparent")
        btn_row.grid(row=0, column=4, rowspan=2, padx=10)
        
        ctk.CTkButton(btn_row, text="Apply", width=70, command=self.refresh_file_list).pack(pady=2)
        ctk.CTkButton(btn_row, text="Save Preset", width=70, command=self.save_filter_preset).pack(pady=2)
        
        self.preset_menu = ctk.CTkOptionMenu(filters_inner, values=["default"], command=self.load_filter_preset, width=100)
        self.preset_menu.grid(row=0, column=5, padx=5)
        self._load_filter_presets()
        
        files_frame = ctk.CTkFrame(main)
        files_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        
        files_header = ctk.CTkFrame(files_frame, fg_color="transparent")
        files_header.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(files_header, text="Project Files", font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        ctk.CTkButton(files_header, text="All", width=40, command=self.select_all).pack(side="right", padx=2)
        ctk.CTkButton(files_header, text="None", width=40, command=self.deselect_all).pack(side="right", padx=2)
        
        search_frame = ctk.CTkFrame(files_frame, fg_color="transparent")
        search_frame.pack(fill="x", padx=5, pady=5)
        
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="🔍 Search files...", 
                                         textvariable=self.search_var)
        self.search_entry.pack(fill="x")
        self.search_entry.bind("<KeyRelease>", self.filter_tree_by_search)
        
        self.files_scroll = ctk.CTkScrollableFrame(files_frame)
        self.files_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        preview_frame = ctk.CTkFrame(main)
        preview_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        
        preview_header = ctk.CTkFrame(preview_frame, fg_color="transparent")
        preview_header.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(preview_header, text="Context Preview", font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.preview_mode = ctk.CTkOptionMenu(preview_header, values=["Full", "Structure Only", "Files Only"],
                                              command=self.change_preview_mode, width=120)
        self.preview_mode.pack(side="right")
        
        self.preview_text = ctk.CTkTextbox(preview_frame, font=ctk.CTkFont(family="Courier", size=11))
        self.preview_text.pack(fill="both", expand=True, padx=5, pady=5)

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
            cat_label = ctk.CTkLabel(self.blocks_list, text=f"── {cat} ──", 
                                     text_color="gray", font=ctk.CTkFont(size=11))
            cat_label.pack(anchor="w", pady=(5, 2))
            
            for block in blocks:
                var = ctk.BooleanVar(value=block.enabled)
                self.block_vars[block.id] = var
                
                cb = ctk.CTkCheckBox(self.blocks_list, text=block.name, variable=var,
                                    command=self.update_preview)
                cb.pack(anchor="w", padx=10, pady=1)

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
            self.dir_label.configure(text=f"📁 {self.selected_directory}")
            self._save_recent_project()
            self.refresh_file_list()

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
        query = self.search_var.get().lower().strip()
        if not query:
            return
        
        def search_node(node):
            matches = query in node.name.lower()
            if node.is_dir and node.is_loaded:
                for child in node.children:
                    matches = search_node(child) or matches
            return matches
        
        for node in self.root_nodes:
            if search_node(node):
                pass

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
                # Edge case: If a directory is checked but children aren't loaded yet
                if node.var.get() and not node.is_loaded:
                    node.load_children()
                    node.set_children_state(True)
                
                if node.is_loaded:
                    for child in node.children:
                        traverse_node(child)
                        
        for root_node in self.root_nodes:
            traverse_node(root_node)
            
        return selected_files

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
        
        self.copy_btn.configure(text="✓ Copied!", fg_color="#1a7a3e")
        self.after(1500, lambda: self.copy_btn.configure(text="📋 Copy Context", fg_color="#2b8a3e"))

    def save_filter_preset(self):
        name = ctk.CTkInputDialog(text="Preset name:", title="Save Filter Preset").get_input()
        if not name:
            return
        
        preset = FilterPreset(
            name=name,
            extensions=self.filter_extensions.get(),
            ignore_dirs=self.filter_dirs.get(),
            ignore_files=self.filter_files.get(),
            content_pattern=self.filter_content.get()
        )
        
        presets = []
        if PRESETS_FILE.exists():
            try:
                presets = [FilterPreset(**p) for p in json.loads(PRESETS_FILE.read_text())]
            except:
                pass
        
        presets = [p for p in presets if p.name != name]
        presets.append(preset)
        
        PRESETS_FILE.write_text(json.dumps([asdict(p) for p in presets], indent=2))
        self._load_filter_presets()

    def _load_filter_presets(self):
        presets = ["default"]
        if PRESETS_FILE.exists():
            try:
                data = json.loads(PRESETS_FILE.read_text())
                presets.extend([p["name"] for p in data])
            except:
                pass
        self.preset_menu.configure(values=presets)

    def load_filter_preset(self, name):
        if name == "default" or not PRESETS_FILE.exists():
            return
        
        try:
            presets = [FilterPreset(**p) for p in json.loads(PRESETS_FILE.read_text())]
            preset = next((p for p in presets if p.name == name), None)
            if preset:
                self.filter_extensions.delete(0, "end")
                self.filter_extensions.insert(0, preset.extensions)
                self.filter_dirs.delete(0, "end")
                self.filter_dirs.insert(0, preset.ignore_dirs)
                self.filter_files.delete(0, "end")
                self.filter_files.insert(0, preset.ignore_files)
                self.filter_content.delete(0, "end")
                self.filter_content.insert(0, preset.content_pattern)
                self.refresh_file_list()
        except:
            pass

class CTkInputDialog(ctk.CTkToplevel):
    def __init__(self, text: str, title: str = "Input"):
        super().__init__()
        self.title(title)
        self.geometry("300x120")
        self.result = None
        
        ctk.CTkLabel(self, text=text).pack(padx=20, pady=10)
        self.entry = ctk.CTkEntry(self)
        self.entry.pack(fill="x", padx=20, pady=5)
        self.entry.bind("<Return>", lambda e: self._ok())
        
        ctk.CTkButton(self, text="OK", command=self._ok).pack(pady=10)
        
        self.transient()
        self.after(100, self._safe_grab)
        self.wait_window()
    
    def _safe_grab(self):
        try:
            self.grab_set()
        except:
            pass
    
    def _ok(self):
        self.result = self.entry.get()
        self.destroy()
    
    def get_input(self):
        return self.result

def main():
    app = GraceContextApp()
    app.mainloop()

if __name__ == "__main__":
    main()
