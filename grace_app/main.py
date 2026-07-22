"""Main GRACE application — PyQt6-based context manager.

Uses QThreadPool for non-blocking file I/O and context assembly.
Cross-platform: Linux, macOS, Windows.
"""

from __future__ import annotations

import os, sys, json, uuid, re, subprocess
from dataclasses import asdict
from typing import Dict, List, Optional, Set
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeView, QPlainTextEdit, QPushButton, QLabel,
    QLineEdit, QComboBox, QCheckBox, QScrollArea, QFrame,
    QDialog, QTextEdit, QGridLayout, QGroupBox,
    QMessageBox, QFileDialog, QMenu, QSlider,
)
from PyQt6.QtGui import (
    QKeySequence, QShortcut, QAction,
    QIcon,
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QObject, QTimer, pyqtSlot
)

from .config import (
    CONFIG_DIR, PROFILES_FILE, RECENT_FILE, SETTINGS_FILE,
    DEFAULT_EXTENSIONS, DEFAULT_IGNORE_DIRS, DEFAULT_IGNORE_FILES,
    SCALE_STEPS, MAX_FILE_SIZE,
)
from .models import ContextBlock
from .engine import TokenEstimator, FileScanner, ContextBuilder
from .tree_model import FileTreeModel

# ── Central QSS Stylesheet ────────────────────────────────────────────────

_STYLESHEET = """
QMainWindow { background-color: #0d1117; }
QWidget { background-color: #0d1117; color: #c9d1d9; font-family: "Segoe UI", "SF Pro Display", "Inter", sans-serif; font-size: 13px; }
QSplitter::handle { background-color: #21262d; width: 2px; }
QSplitter::handle:hover { background-color: #30363d; }
QFrame#panel, QGroupBox { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 8px; }
QGroupBox { margin-top: 12px; padding-top: 16px; font-weight: bold; color: #8b949e; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #c9d1d9; }
QTreeView { background-color: #0d1117; alternate-background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; outline: none; show-decoration-selected: 1; }
QTreeView::item { padding: 3px 6px; border-radius: 4px; min-height: 22px; }
QTreeView::item:hover { background-color: #1c2128; }
QTreeView::item:selected { background-color: #1f2a3a; color: #e6edf3; }
QPlainTextEdit#preview { background-color: #0d1117; border: 1px solid #30363d; border-radius: 6px; font-family: "JetBrains Mono","Fira Code","Cascadia Code","Consolas",monospace; font-size: 12px; line-height: 1.6; selection-background-color: #264f78; }
QLineEdit { background-color: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 5px 10px; color: #c9d1d9; selection-background-color: #264f78; }
QLineEdit:focus { border-color: #58a6ff; }
QComboBox { background-color: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 4px 8px; color: #c9d1d9; }
QComboBox:hover { border-color: #58a6ff; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 20px; border-left: 1px solid #30363d; }
QComboBox QAbstractItemView { background-color: #161b22; border: 1px solid #30363d; selection-background-color: #1f2a3a; }
QPushButton { background-color: #21262d; border: 1px solid #30363d; border-radius: 6px; padding: 6px 14px; color: #c9d1d9; font-weight: 500; }
QPushButton:hover { background-color: #30363d; border-color: #8b949e; }
QPushButton:pressed { background-color: #1c2128; }
QPushButton#primary { background-color: #238636; border-color: #2ea043; color: white; }
QPushButton#primary:hover { background-color: #2ea043; }
QPushButton#accent { background-color: #1f6feb; border-color: #388bfd; color: white; }
QPushButton#accent:hover { background-color: #388bfd; }
QPushButton#danger { background-color: transparent; border-color: #f85149; color: #f85149; }
QPushButton#danger:hover { background-color: #490202; }
QPushButton#copyBtn { background-color: #1f6feb; border-color: #388bfd; color: white; font-weight: bold; padding: 8px 20px; font-size: 14px; }
QPushButton#copyBtn:hover { background-color: #388bfd; }
QCheckBox { spacing: 6px; color: #c9d1d9; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #30363d; border-radius: 4px; background-color: #0d1117; }
QCheckBox::indicator:checked { background-color: #1f6feb; border-color: #388bfd; }
QCheckBox::indicator:hover { border-color: #58a6ff; }
QScrollBar:vertical { background-color: #0d1117; width: 10px; margin: 0; border-radius: 5px; }
QScrollBar::handle:vertical { background-color: #30363d; min-height: 30px; border-radius: 5px; }
QScrollBar::handle:vertical:hover { background-color: #484f58; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background-color: #0d1117; height: 10px; margin: 0; border-radius: 5px; }
QScrollBar::handle:horizontal { background-color: #30363d; min-width: 30px; border-radius: 5px; }
QScrollBar::handle:horizontal:hover { background-color: #484f58; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollArea { border: none; background: transparent; }
QSlider::groove:horizontal { background-color: #21262d; height: 6px; border-radius: 3px; margin: 2px 0; }
QSlider::handle:horizontal { background-color: #58a6ff; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }
QSlider::handle:horizontal:hover { background-color: #79c0ff; }
QSlider::sub-page:horizontal { background-color: #1f6feb; border-radius: 3px; }
QToolTip { background-color: #161b22; color: #e6edf3; border: 1px solid #30363d; padding: 4px 8px; border-radius: 4px; font-size: 11px; }
QMenu { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 24px; border-radius: 4px; }
QMenu::item:selected { background-color: #1f6feb; }
QDialog { background-color: #161b22; }
QTextEdit { background-color: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; selection-background-color: #264f78; font-family: "JetBrains Mono","Fira Code",monospace; font-size: 12px; }
QLabel#statusLabel { color: #484f58; font-size: 11px; }
QLabel#dirLabel { color: #8b949e; font-size: 12px; padding: 2px 8px; background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; }
"""


# ── Background Worker for Context Building ─────────────────────────────────

class ContextBuildWorker(QObject):
    finished = pyqtSignal(str, int)
    error = pyqtSignal(str)

    def __init__(self, blocks, files, base_dir, mode, instruction, max_size):
        super().__init__()
        self.blocks = blocks
        self.files = files
        self.base_dir = base_dir
        self.mode = mode
        self.instruction = instruction
        self.max_size = max_size

    @pyqtSlot()
    def run(self):
        try:
            text = ContextBuilder.build(
                self.blocks, self.files, self.base_dir,
                self.mode, self.instruction, self.max_size
            )
            tokens = TokenEstimator.estimate(text)
            self.finished.emit(text, tokens)
        except Exception as e:
            self.error.emit(str(e))


# ── Quick Add Block Dialog (name only, content = current context) ───────

class QuickAddBlockDialog(QDialog):
    """Minimal dialog: only asks for a name. Content is the current preview."""

    def __init__(self, parent: QWidget | None = None, preview_content: str = ""):
        super().__init__(parent)
        self.result_block: ContextBlock | None = None
        self._preview_content = preview_content.strip()

        self.setWindowTitle("Save Current Context as Block")
        self.setMinimumSize(400, 120)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        hint = QLabel("Content from current preview will be saved.")
        hint.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(hint)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Block name...")
        name_row.addWidget(self.name_edit, 1)
        layout.addLayout(name_row)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Save Block")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Required", "Block name is required.")
            return

        self.result_block = ContextBlock(
            id=uuid.uuid4().hex[:12], name=name,
            content=self._preview_content, category="snapshot",
            order=0
        )
        self.accept()


# ── Context Block Editor Dialog (full: edit name, category, content) ─────

class BlockEditorDialog(QDialog):
    """Modal dialog for editing an existing ContextBlock or full manual creation."""

    def __init__(self, parent: QWidget | None = None,
                 block: ContextBlock | None = None):
        super().__init__(parent)
        self.block = block
        self.result_block: ContextBlock | None = None

        self.setWindowTitle("Edit Context Block" if block else "New Context Block")
        self.setMinimumSize(550, 420)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Block name...")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Category:"))
        self.cat_edit = QLineEdit()
        self.cat_edit.setPlaceholderText("e.g., tech, requirements, constraints...")
        layout.addWidget(self.cat_edit)

        layout.addWidget(QLabel("Content:"))
        self.content_edit = QTextEdit()
        layout.addWidget(self.content_edit, 1)

        if block:
            self.name_edit.setText(block.name)
            self.cat_edit.setText(block.category)
            self.content_edit.setPlainText(block.content)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _save(self):
        name = self.name_edit.text().strip()
        content = self.content_edit.toPlainText().strip()
        category = self.cat_edit.text().strip() or "general"

        if not name or not content:
            QMessageBox.warning(self, "Required", "Name and content are required.")
            return

        block_id = self.block.id if self.block else uuid.uuid4().hex[:12]
        self.result_block = ContextBlock(
            id=block_id, name=name, content=content, category=category,
            order=self.block.order if self.block else 0
        )
        self.accept()


# ── Extension Scanner Thread ──────────────────────────────────────────────

class ExtensionScanThread(QThread):
    """Dedicated thread for discovering file extensions in a project."""
    resultReady = pyqtSignal(list)
    errorOccurred = pyqtSignal(str)

    def __init__(self, root_path: str, ignore_dirs: set, parent=None):
        super().__init__(parent)
        self.root_path = root_path
        self.ignore_dirs = ignore_dirs

    def run(self):
        try:
            exts = FileScanner.scan_extensions(self.root_path, self.ignore_dirs)
            self.resultReady.emit(exts)
        except Exception as e:
            self.errorOccurred.emit(str(e))


# ── Main Application Window ──────────────────────────────────────────────

class GraceContextApp(QMainWindow):
    """GRACE Context Manager — assemble LLM context from your project."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GRACE Context Manager")
        self.setMinimumSize(1200, 750)
        self.resize(1500, 920)

        self._scaling = 100
        self._selected_directory = os.getcwd()
        self._context_blocks: List[ContextBlock] = []
        self._block_checkboxes: Dict[str, QCheckBox] = {}
        self._preview_mode = "Full"
        self._build_timer = QTimer()
        self._build_timer.setSingleShot(True)
        self._build_timer.setInterval(250)
        self._build_timer.timeout.connect(self._rebuild_preview)
        self._ext_thread: QThread | None = None
        self._build_thread: QThread | None = None

        self._ensure_config()
        self._load_settings()
        self._load_context_blocks()

        self._setup_ui()
        self._setup_shortcuts()
        self._load_recent_project()
        self._apply_scaling()

    # ── Config management ──────────────────────────────────────────────

    def _ensure_config(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        for f, default in [(PROFILES_FILE, "[]"), (RECENT_FILE, "[]"),
                            (SETTINGS_FILE, '{"scaling": 100}')]:
            if not f.exists():
                f.write_text(default)

    def _load_settings(self):
        try:
            if SETTINGS_FILE.exists():
                data = json.loads(SETTINGS_FILE.read_text())
                sc = int(data.get("scaling", 100))
                closest = min(SCALE_STEPS, key=lambda v: abs(v - sc))
                self._scaling = closest
        except Exception:
            self._scaling = 100

    def _save_settings(self):
        try:
            SETTINGS_FILE.write_text(json.dumps({"scaling": self._scaling}, indent=2))
        except Exception:
            pass

    def _load_context_blocks(self):
        try:
            if PROFILES_FILE.exists():
                data = json.loads(PROFILES_FILE.read_text())
                self._context_blocks = [ContextBlock(**b) for b in data]
        except Exception:
            self._context_blocks = [
                ContextBlock("tech", "Tech Stack", "Python 3.10+, FastAPI, PostgreSQL", "tech"),
                ContextBlock("rules", "Coding Rules", "Use type hints. Write docstrings. No global state.", "constraints"),
            ]

    def _save_context_blocks(self):
        try:
            data = [asdict(b) for b in self._context_blocks]
            PROFILES_FILE.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def _load_recent_project(self):
        try:
            if RECENT_FILE.exists():
                recent = json.loads(RECENT_FILE.read_text())
                if recent and os.path.isdir(recent[0]):
                    self._selected_directory = recent[0]
                    self._dir_label.setText(f" {self._selected_directory}")
                    self._apply_filters_to_model()
        except Exception:
            pass

    def _save_recent_project(self):
        try:
            recent = [self._selected_directory]
            if RECENT_FILE.exists():
                old = json.loads(RECENT_FILE.read_text())
                recent.extend([p for p in old if p != self._selected_directory][:4])
            RECENT_FILE.write_text(json.dumps(recent))
        except Exception:
            pass

    # ── UI Setup ───────────────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        splitter.addWidget(self._build_sidebar())
        splitter.addWidget(self._build_main_area())
        splitter.setSizes([340, 1100])
        main_layout.addWidget(splitter)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("panel")
        sidebar.setMinimumWidth(280)
        sidebar.setMaximumWidth(420)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ── Directory ──
        dir_row = QHBoxLayout()
        self._dir_label = QLabel(f" {self._selected_directory}")
        self._dir_label.setObjectName("dirLabel")
        self._dir_label.setWordWrap(True)
        dir_row.addWidget(self._dir_label, 1)

        self._recent_btn = QPushButton("Recent")
        self._recent_btn.clicked.connect(self._show_recent_menu)
        dir_row.addWidget(self._recent_btn)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_directory)
        dir_row.addWidget(browse_btn)
        layout.addLayout(dir_row)

        # ── Context Blocks ──
        blocks_group = QGroupBox("Context Blocks")
        blocks_inner = QVBoxLayout(blocks_group)
        blocks_inner.setContentsMargins(6, 18, 6, 6)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Block")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add_block)
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        blocks_inner.addLayout(btn_row)

        self._blocks_scroll = QScrollArea()
        self._blocks_scroll.setWidgetResizable(True)
        self._blocks_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._blocks_container = QWidget()
        self._blocks_container_layout = QVBoxLayout(self._blocks_container)
        self._blocks_container_layout.setContentsMargins(0, 0, 0, 0)
        self._blocks_container_layout.setSpacing(2)
        self._blocks_container_layout.addStretch()
        self._blocks_scroll.setWidget(self._blocks_container)
        blocks_inner.addWidget(self._blocks_scroll, 1)
        self._refresh_blocks_ui()

        layout.addWidget(blocks_group, 1)

        # ── Scale ──
        scale_group = QGroupBox("UI Scale")
        scale_inner = QVBoxLayout(scale_group)
        scale_inner.setContentsMargins(6, 18, 6, 6)

        scale_row = QHBoxLayout()
        scale_row.setSpacing(8)

        self._scale_slider = QSlider(Qt.Orientation.Horizontal)
        self._scale_slider.setMinimum(0)
        self._scale_slider.setMaximum(len(SCALE_STEPS) - 1)
        self._scale_slider.setPageStep(1)
        self._scale_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._scale_slider.setTickInterval(1)
        self._scale_slider.valueChanged.connect(self._on_slider_changed)
        scale_row.addWidget(self._scale_slider, 1)

        self._scale_label = QLabel(f"{self._scaling}%")
        self._scale_label.setFixedWidth(42)
        self._scale_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scale_label.setStyleSheet(
            "color: #58a6ff; font-weight: bold; font-size: 12px; background: transparent;"
        )
        scale_row.addWidget(self._scale_label)
        scale_inner.addLayout(scale_row)

        # Snap slider to current scale
        try:
            idx = SCALE_STEPS.index(self._scaling)
        except ValueError:
            idx = 2  # default 100%
        self._scale_slider.setValue(idx)

        layout.addWidget(scale_group)

        # ── Instruction ──
        inst_group = QGroupBox("Your Instruction / Task")
        inst_inner = QVBoxLayout(inst_group)
        inst_inner.setContentsMargins(6, 18, 6, 6)
        self._instruction_edit = QPlainTextEdit()
        self._instruction_edit.setPlaceholderText("Based on the context above, implement...")
        self._instruction_edit.setMaximumHeight(120)
        self._instruction_edit.setTabChangesFocus(True)
        self._instruction_edit.textChanged.connect(self._schedule_preview_rebuild)
        inst_inner.addWidget(self._instruction_edit)
        layout.addWidget(inst_group)

        # ── Actions ──
        self._copy_btn = QPushButton("Copy Context")
        self._copy_btn.setObjectName("copyBtn")
        self._copy_btn.clicked.connect(self._copy_context)
        layout.addWidget(self._copy_btn)

        self._token_label = QLabel("~0 tokens")
        self._token_label.setObjectName("statusLabel")
        self._token_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._token_label)

        return sidebar

    def _build_main_area(self) -> QWidget:
        main = QWidget()
        layout = QVBoxLayout(main)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(6)

        # ── Filter bars ──

        self._selected_extensions: Set[str] = set()
        self._extension_checkboxes: Dict[str, QCheckBox] = {}
        self._ignored_patterns: Set[str] = set()
        self._ignore_checkboxes: Dict[str, QCheckBox] = {}
        self._default_ignores: Set[str] = set()

        ext_frame = QFrame()
        ext_frame.setObjectName("panel")
        ext_layout = QVBoxLayout(ext_frame)
        ext_layout.setContentsMargins(10, 6, 10, 6)
        ext_layout.setSpacing(4)

        ext_hdr = QHBoxLayout()
        ext_hdr.addWidget(QLabel("Extensions"))
        ext_hdr.addStretch()
        detect_btn = QPushButton("Detect")
        detect_btn.setObjectName("accent")
        detect_btn.clicked.connect(self._detect_extensions)
        ext_hdr.addWidget(detect_btn)
        all_ext_btn = QPushButton("All")
        all_ext_btn.clicked.connect(lambda: self._set_all_extensions(True))
        ext_hdr.addWidget(all_ext_btn)
        none_ext_btn = QPushButton("None")
        none_ext_btn.clicked.connect(lambda: self._set_all_extensions(False))
        ext_hdr.addWidget(none_ext_btn)
        ext_layout.addLayout(ext_hdr)

        self._ext_scroll = QScrollArea()
        self._ext_scroll.setMaximumHeight(50)
        self._ext_scroll.setWidgetResizable(True)
        self._ext_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._ext_container = QWidget()
        self._ext_container.setStyleSheet("background: transparent;")
        self._ext_chk_layout = QHBoxLayout(self._ext_container)
        self._ext_chk_layout.setContentsMargins(2, 2, 2, 2)
        self._ext_chk_layout.setSpacing(4)
        self._ext_chk_layout.addStretch()
        self._ext_scroll.setWidget(self._ext_container)
        ext_layout.addWidget(self._ext_scroll)

        layout.addWidget(ext_frame)

        ign_frame = QFrame()
        ign_frame.setObjectName("panel")
        ign_layout = QVBoxLayout(ign_frame)
        ign_layout.setContentsMargins(10, 6, 10, 6)
        ign_layout.setSpacing(4)

        ign_hdr = QHBoxLayout()
        ign_hdr.addWidget(QLabel("Ignored"))
        ign_hdr.addStretch()
        ign_scan_btn = QPushButton("Scan")
        ign_scan_btn.clicked.connect(self._scan_ignored)
        ign_hdr.addWidget(ign_scan_btn)
        ign_all_btn = QPushButton("All")
        ign_all_btn.clicked.connect(lambda: self._set_all_ignores(True))
        ign_hdr.addWidget(ign_all_btn)
        ign_none_btn = QPushButton("None")
        ign_none_btn.clicked.connect(lambda: self._set_all_ignores(False))
        ign_hdr.addWidget(ign_none_btn)
        ign_layout.addLayout(ign_hdr)

        self._ign_scroll = QScrollArea()
        self._ign_scroll.setMaximumHeight(50)
        self._ign_scroll.setWidgetResizable(True)
        self._ign_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._ign_container = QWidget()
        self._ign_container.setStyleSheet("background: transparent;")
        self._ign_chk_layout = QHBoxLayout(self._ign_container)
        self._ign_chk_layout.setContentsMargins(2, 2, 2, 2)
        self._ign_chk_layout.setSpacing(4)
        self._ign_chk_layout.addStretch()
        self._ign_scroll.setWidget(self._ign_container)
        ign_layout.addWidget(self._ign_scroll)

        layout.addWidget(ign_frame)

        # Content search (only remaining text field)
        srch_frame = QFrame()
        srch_frame.setObjectName("panel")
        srch_layout = QHBoxLayout(srch_frame)
        srch_layout.setContentsMargins(10, 6, 10, 6)
        srch_layout.addWidget(QLabel("Contains:"))
        self._filter_content = QLineEdit()
        self._filter_content.setPlaceholderText("filter files containing text...")
        self._filter_content.editingFinished.connect(self._apply_filters_to_model)
        srch_layout.addWidget(self._filter_content, 1)
        layout.addWidget(srch_frame)

        # ── File tree + preview splitter ──
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setHandleWidth(2)

        # File tree
        files_widget = QWidget()
        files_layout = QVBoxLayout(files_widget)
        files_layout.setContentsMargins(0, 0, 0, 0)
        files_layout.setSpacing(4)

        files_header = QHBoxLayout()
        files_header.addWidget(QLabel("Project Files"))
        files_header.addStretch()
        all_files_btn = QPushButton("All")
        all_files_btn.clicked.connect(lambda: self._set_all_files(True))
        files_header.addWidget(all_files_btn)
        none_files_btn = QPushButton("None")
        none_files_btn.clicked.connect(lambda: self._set_all_files(False))
        files_header.addWidget(none_files_btn)
        files_layout.addLayout(files_header)

        self._search_entry = QLineEdit()
        self._search_entry.setPlaceholderText("Search files or paths...")
        self._search_entry.textChanged.connect(self._on_search_changed)
        files_layout.addWidget(self._search_entry)

        self._file_model = FileTreeModel(self._selected_directory)
        self._file_model.checkedChanged.connect(self._schedule_preview_rebuild)

        self._file_tree = QTreeView()
        self._file_tree.setModel(self._file_model)
        self._file_tree.setHeaderHidden(True)
        self._file_tree.setAlternatingRowColors(True)
        self._file_tree.setAnimated(True)
        self._file_tree.setIndentation(20)
        self._file_tree.setExpandsOnDoubleClick(True)
        self._file_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._file_tree.customContextMenuRequested.connect(self._file_tree_context_menu)
        self._file_tree.doubleClicked.connect(self._on_tree_double_click)
        self._file_tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        files_layout.addWidget(self._file_tree, 1)

        content_splitter.addWidget(files_widget)

        # Preview pane
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(4)

        preview_header = QHBoxLayout()
        preview_header.addWidget(QLabel("Context Preview"))
        preview_header.addStretch()
        self._preview_mode_combo = QComboBox()
        self._preview_mode_combo.addItems(["Full", "Structure Only", "Files Only"])
        self._preview_mode_combo.currentTextChanged.connect(self._on_mode_changed)
        preview_header.addWidget(self._preview_mode_combo)
        preview_layout.addLayout(preview_header)

        self._preview_text = QPlainTextEdit()
        self._preview_text.setObjectName("preview")
        self._preview_text.setReadOnly(True)
        self._preview_text.setTabChangesFocus(True)
        preview_layout.addWidget(self._preview_text, 1)

        content_splitter.addWidget(preview_widget)
        content_splitter.setSizes([600, 550])
        layout.addWidget(content_splitter, 1)

        return main

    # ── Shortcuts ──────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        QShortcut(QKeySequence.StandardKey.Copy, self, self._copy_context)
        QShortcut(QKeySequence("Ctrl+N"), self, self._add_block)
        QShortcut(QKeySequence("Ctrl+R"), self, self._refresh_context)
        QShortcut(QKeySequence("Ctrl+O"), self, self._browse_directory)
        QShortcut(QKeySequence("Ctrl+A"), self, lambda: self._set_all_files(True))
        QShortcut(QKeySequence("Ctrl+D"), self, lambda: self._set_all_files(False))

    # ── Directory ──────────────────────────────────────────────────────

    def _browse_directory(self):
        path = QFileDialog.getExistingDirectory(self, "Select Project Directory",
                                                 self._selected_directory)
        if path:
            self._load_project(path)

    def _show_recent_menu(self):
        menu = QMenu(self)
        try:
            if RECENT_FILE.exists():
                recent = json.loads(RECENT_FILE.read_text())
                for p in recent:
                    if os.path.isdir(p):
                        action = menu.addAction(p)
                        action.triggered.connect(lambda checked, path=p: self._load_project(path))
        except Exception:
            pass
        if not menu.actions():
            menu.addAction("No recent projects").setEnabled(False)
        menu.exec(self._recent_btn.mapToGlobal(self._recent_btn.rect().bottomLeft()))

    def _load_project(self, path):
        self._selected_directory = path
        self._dir_label.setText(f" {path}")
        self._save_recent_project()
        self._apply_filters_to_model()
        self._scan_ignored()
        self._schedule_preview_rebuild()

    # ── Context Blocks ─────────────────────────────────────────────────

    def _refresh_blocks_ui(self):
        if not hasattr(self, '_blocks_container_layout'):
            return
        layout = self._blocks_container_layout
        stretch = layout.takeAt(layout.count() - 1) if layout.count() > 0 else None
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._block_checkboxes.clear()

        cats: Dict[str, list] = {}
        for b in sorted(self._context_blocks, key=lambda b: (b.category, b.order)):
            cats.setdefault(b.category, []).append(b)

        for cat, blocks in cats.items():
            lbl = QLabel(f"{cat}")
            lbl.setStyleSheet(
                "color: #484f58; font-size: 11px; font-weight: bold; "
                "padding-top: 6px; padding-left: 2px; background: transparent;"
            )
            layout.addWidget(lbl)
            for block in blocks:
                cb = QCheckBox(block.name)
                cb.setChecked(block.enabled)
                cb.toggled.connect(self._schedule_preview_rebuild)
                cb.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                cb.customContextMenuRequested.connect(lambda pos, b=block, c=cb: self._block_context_menu(pos, b, c))
                self._block_checkboxes[block.id] = cb
                layout.addWidget(cb)

        if stretch:
            layout.addItem(stretch)
        else:
            layout.addStretch()

    def _block_context_menu(self, pos, block, cb):
        menu = QMenu(self)
        edit_action = menu.addAction("Edit Block")
        delete_action = menu.addAction("Delete Block")
        menu.addSeparator()
        toggle_action = menu.addAction("Uncheck" if cb.isChecked() else "Check")

        action = menu.exec(cb.mapToGlobal(pos))
        if action == edit_action:
            self._edit_specific_block(block)
        elif action == delete_action:
            self._delete_specific_block(block)
        elif action == toggle_action:
            cb.setChecked(not cb.isChecked())

    def _add_block(self):
        preview = self._preview_text.toPlainText()
        if not preview.strip():
            QMessageBox.information(self, "No Context", "Select files to build a context first.")
            return
        dlg = QuickAddBlockDialog(self, preview_content=preview)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_block:
            block = dlg.result_block
            block.order = len(self._context_blocks)
            self._context_blocks.append(block)
            self._save_context_blocks()
            self._refresh_blocks_ui()
            self._schedule_preview_rebuild()

    def _edit_specific_block(self, block):
        dlg = BlockEditorDialog(self, block=block)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_block:
            idx = next(i for i, b in enumerate(self._context_blocks) if b.id == block.id)
            self._context_blocks[idx] = dlg.result_block
            self._save_context_blocks()
            self._refresh_blocks_ui()
            self._schedule_preview_rebuild()

    def _delete_specific_block(self, block):
        if QMessageBox.question(self, "Confirm Delete", f"Delete block '{block.name}'?") == QMessageBox.StandardButton.Yes:
            self._context_blocks = [b for b in self._context_blocks if b.id != block.id]
            self._save_context_blocks()
            self._refresh_blocks_ui()
            self._schedule_preview_rebuild()

    # ── Extensions ─────────────────────────────────────────────────────

    def _detect_extensions(self):
        t = getattr(self, '_ext_thread', None)
        if t is not None:
            try:
                if t.isRunning():
                    t.quit()
                    t.wait(500)
            except RuntimeError:
                pass
            self._ext_thread = None

        ignore_dirs = self._ignored_patterns
        thread = ExtensionScanThread(self._selected_directory, ignore_dirs, self)
        thread.resultReady.connect(self._on_extensions_detected)
        thread.errorOccurred.connect(self._on_worker_error)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: setattr(self, '_ext_thread', None))
        self._ext_thread = thread
        thread.start()

    def _on_extensions_detected(self, extensions):
        self._repopulate_checkboxes(
            self._ext_chk_layout, self._extension_checkboxes,
            extensions, set(extensions),
            self._on_extension_toggled
        )
        self._selected_extensions = set(extensions)
        self._apply_filters_to_model()

    def _set_all_extensions(self, checked: bool):
        for ext, cb in self._extension_checkboxes.items():
            cb.setChecked(checked)
        self._apply_filters_to_model()

    def _on_extension_toggled(self):
        self._selected_extensions = {ext for ext, cb in self._extension_checkboxes.items() if cb.isChecked()}
        self._apply_filters_to_model()

    # ── Ignored patterns ────────────────────────────────────────────────

    def _scan_ignored(self):
        known = {'.git', '__pycache__', 'venv', '.venv', 'env', '.env',
                 'node_modules', '.tox', 'dist', 'build', '.idea', '.vscode',
                 '.mypy_cache', '.pytest_cache', '.ruff_cache', 'egg-info',
                 '*.pyc', '*.pyo', '.DS_Store', 'Thumbs.db', '.env', '.gitignore'}
        found: Set[str] = set()
        try:
            for entry in os.listdir(self._selected_directory):
                if entry.startswith('.'):
                    found.add(entry)
                full = os.path.join(self._selected_directory, entry)
                if os.path.isdir(full) and (entry in known or entry.startswith('__')):
                    found.add(entry)
            for entry in os.listdir(self._selected_directory):
                full = os.path.join(self._selected_directory, entry)
                if os.path.isfile(full) and entry.startswith('.'):
                    found.add(entry)
        except PermissionError:
            pass

        patterns = sorted(found)
        preselected = set(patterns)
        self._repopulate_checkboxes(
            self._ign_chk_layout, self._ignore_checkboxes,
            patterns, preselected,
            self._on_ignore_toggled
        )
        self._ignored_patterns = preselected
        self._apply_filters_to_model()

    def _set_all_ignores(self, checked: bool):
        for pat, cb in self._ignore_checkboxes.items():
            cb.setChecked(checked)
        self._ignored_patterns = {pat for pat, cb in self._ignore_checkboxes.items() if cb.isChecked()}
        self._apply_filters_to_model()

    def _on_ignore_toggled(self):
        self._ignored_patterns = {pat for pat, cb in self._ignore_checkboxes.items() if cb.isChecked()}
        self._apply_filters_to_model()

    def add_ignored_pattern(self, pattern: str):
        if pattern not in self._ignore_checkboxes:
            cb = QCheckBox(pattern)
            cb.setChecked(True)
            cb.toggled.connect(self._on_ignore_toggled)
            self._ignore_checkboxes[pattern] = cb
            n = self._ign_chk_layout.count()
            self._ign_chk_layout.insertWidget(max(0, n - 1), cb)
        else:
            self._ignore_checkboxes[pattern].setChecked(True)
        self._ignored_patterns.add(pattern)
        self._apply_filters_to_model()

    # ── Checkbox helper ─────────────────────────────────────────────────

    def _repopulate_checkboxes(self, layout, storage: dict, items: list,
                                preselected: set, on_change):
        stretch = None
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                stretch = item
        storage.clear()

        for name in items:
            cb = QCheckBox(name)
            cb.setChecked(name in preselected)
            cb.toggled.connect(on_change)
            layout.addWidget(cb)
            storage[name] = cb
        if stretch:
            layout.addItem(stretch)
        else:
            layout.addStretch()

    # ── Filters ────────────────────────────────────────────────────────

    def _apply_filters_to_model(self):
        exts = sorted(self._selected_extensions)
        ignore_patterns = self._ignored_patterns
        ignore_dirs = {p for p in ignore_patterns if not p.startswith('*')}
        ignore_files = {p for p in ignore_patterns if p.startswith('*')}
        ignore_files.update({'.gitignore', '.env'})
        content = self._filter_content.text().strip()
        self._file_model.set_filters(exts, ignore_dirs, ignore_files, content)
        self._file_model.change_root(self._selected_directory)
        self._schedule_preview_rebuild()

    # ── File tree ──────────────────────────────────────────────────────

    def _set_all_files(self, checked: bool):
        self._file_model.set_all_checked(checked)

    def _on_search_changed(self, text: str):
        self._file_model.set_search(text)

    def _on_tree_double_click(self, index):
        if index.isValid() and self._file_model.hasChildren(index):
            if self._file_tree.isExpanded(index):
                self._file_tree.collapse(index)
            else:
                self._file_tree.expand(index)

    def _file_tree_context_menu(self, pos):
        index = self._file_tree.indexAt(pos)
        menu = QMenu(self)

        if index.isValid():
            path = self._file_model.data(index, Qt.ItemDataRole.UserRole)
            is_dir = self._file_model.data(index, Qt.ItemDataRole.UserRole + 1)
            is_checked = self._file_model.data(index, Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked
            entry_name = os.path.basename(path)

            check_action = menu.addAction("Uncheck" if is_checked else "Check")
            menu.addSeparator()
            copy_path_action = menu.addAction("Copy Path")
            if not is_dir:
                open_action = menu.addAction("Open File")
            if is_dir:
                ignore_action = menu.addAction(f"Ignore '{entry_name}'")
            menu.addSeparator()

        expand_all = menu.addAction("Expand All")
        collapse_all = menu.addAction("Collapse All")

        action = menu.exec(self._file_tree.viewport().mapToGlobal(pos))

        if action == expand_all:
            self._file_tree.expandAll()
        elif action == collapse_all:
            self._file_tree.collapseAll()
        elif index.isValid():
            if action == check_action:
                new_state = Qt.CheckState.Unchecked if is_checked else Qt.CheckState.Checked
                self._file_model.setData(index, new_state, Qt.ItemDataRole.CheckStateRole)
            elif action == copy_path_action:
                QApplication.clipboard().setText(path)
            elif is_dir and action == ignore_action:
                self.add_ignored_pattern(entry_name)
            elif not is_dir and action == open_action:
                try:
                    if sys.platform == "win32":
                        os.startfile(path)
                    elif sys.platform == "darwin":
                        subprocess.call(["open", path])
                    else:
                        subprocess.call(["xdg-open", path])
                except Exception:
                    pass

    # ── Preview ────────────────────────────────────────────────────────

    def _schedule_preview_rebuild(self):
        self._build_timer.start()

    def _rebuild_preview(self):
        enabled_blocks = []
        for bid, cb in self._block_checkboxes.items():
            if cb.isChecked():
                match = [b for b in self._context_blocks if b.id == bid]
                if match:
                    enabled_blocks.append(match[0])

        selected_paths = self._file_model.checked_paths()
        # Expand any checked directories to their contained matching files
        selected_files = self._expand_dirs_to_files(selected_paths)
        instruction = self._instruction_edit.toPlainText().strip()

        try:
            text = ContextBuilder.build(
                enabled_blocks, selected_files, self._selected_directory,
                self._preview_mode, instruction, MAX_FILE_SIZE
            )
            tokens = TokenEstimator.estimate(text)
            self._preview_text.setPlainText(text)
            self._token_label.setText(f"~{TokenEstimator.format_count(tokens)}")
        except Exception as e:
            self._token_label.setText(f"Error: {e}")

    def _expand_dirs_to_files(self, paths: list) -> list:
        """If a path is a directory, expand it to all matching files inside it."""
        dirs = [p for p in paths if os.path.isdir(p)]
        files = [p for p in paths if not os.path.isdir(p)]
        if not dirs:
            return sorted(set(files))

        for d in dirs:
            found = FileScanner.list_entries(
                d, self._file_model.extensions,
                self._file_model.ignore_dirs,
                self._file_model.ignore_files,
                self._file_model.content_filter
            )
            files.extend(found)
        return sorted(set(files))

    def _on_build_finished(self, text: str, tokens: int):
        self._preview_text.setPlainText(text)
        self._token_label.setText(f"~{TokenEstimator.format_count(tokens)}")

    def _on_worker_error(self, error: str):
        self._token_label.setText(f"Error: {error}")

    def _on_mode_changed(self, mode: str):
        self._preview_mode = mode
        self._schedule_preview_rebuild()

    # ── Refresh ────────────────────────────────────────────────────────

    def _refresh_context(self):
        stale = self._file_model.get_stale_files()
        self._file_model.refresh_mtimes()
        self._schedule_preview_rebuild()
        msg = f"Refreshed {len(stale)} changed file(s)" if stale else "No file changes detected"
        self._token_label.setText(msg)
        QTimer.singleShot(3000, lambda: self._update_token_count())

    def _update_token_count(self):
        try:
            t = TokenEstimator.estimate(self._preview_text.toPlainText())
            self._token_label.setText(f"~{TokenEstimator.format_count(t)}")
        except Exception:
            pass

    # ── Copy ───────────────────────────────────────────────────────────

    def _copy_context(self):
        QApplication.clipboard().setText(self._preview_text.toPlainText())
        self._copy_btn.setText("Copied!")
        self._copy_btn.setStyleSheet(
            "QPushButton { background-color: #238636; border-color: #2ea043; color: white; "
            "font-weight: bold; padding: 8px 20px; font-size: 14px; border-radius: 6px; }"
        )
        QTimer.singleShot(2000, self._reset_copy_button)

    def _reset_copy_button(self):
        self._copy_btn.setText("Copy Context")
        self._copy_btn.setStyleSheet("")

    # ── Scale ──────────────────────────────────────────────────────────

    def _get_scaled_stylesheet(self, scale: int) -> str:
        factor = scale / 100.0
        def replace_px(match):
            val = float(match.group(1))
            return f"{int(round(val * factor))}px"
        return re.sub(r'(\d+)px', replace_px, _STYLESHEET)

    def _on_slider_changed(self, idx: int):
        value = SCALE_STEPS[idx]
        self._scaling = value
        self._scale_label.setText(f"{value}%")
        self._save_settings()
        self._apply_scaling()

    def _apply_scaling(self):
        qApp = QApplication.instance()
        if qApp:
            qApp.setStyleSheet(self._get_scaled_stylesheet(self._scaling))

    # ── Window close ───────────────────────────────────────────────────

    def closeEvent(self, event):
        self._save_settings()
        self._save_context_blocks()
        for attr in ("_ext_thread", "_build_thread"):
            t = getattr(self, attr, None)
            if t and t.isRunning():
                t.quit()
                t.wait(1000)
        event.accept()


# ── Entry Point ────────────────────────────────────────────────────────────

def main():
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    app.setOrganizationName("grace-manager")
    app.setApplicationName("GRACE")
    app.setStyle("Fusion")

    icon_path = Path(__file__).parent / "assets" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = GraceContextApp()
    screen = app.primaryScreen().availableGeometry()
    window.move(
        (screen.width() - window.width()) // 2,
        (screen.height() - window.height()) // 2
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
