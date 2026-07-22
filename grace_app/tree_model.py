from __future__ import annotations

import os
from typing import Dict

from PyQt6.QtCore import (
    QAbstractItemModel, QModelIndex, Qt, pyqtSignal, QObject,
)
from PyQt6.QtGui import QColor

from .models import TreeNode
from .engine import FileScanner


class FileTreeModel(QAbstractItemModel):
    """Lazy-loading file-tree model with checkboxes for QTreeView."""

    checkedChanged = pyqtSignal()

    def __init__(self, root_path: str, parent: QObject | None = None):
        super().__init__(parent)
        self.root_path = os.path.abspath(root_path)
        self.ignore_dirs: set = set()
        self.ignore_files: set = set()
        self.extensions: list = []
        self.content_filter: str = ""
        self.search_text: str = ""

        self._root = TreeNode(path=self.root_path, name=os.path.basename(self.root_path) or self.root_path, is_dir=True, depth=0)
        self._node_index: Dict[str, TreeNode] = {self.root_path: self._root}
        self._checked_paths: Dict[str, bool] = {}

    def set_filters(self, extensions: list, ignore_dirs: set, ignore_files: set, content_filter: str = ""):
        self.extensions = [e.lower() for e in extensions]
        self.ignore_dirs = ignore_dirs
        self.ignore_files = ignore_files
        self.content_filter = content_filter

    def set_search(self, text: str):
        self.search_text = text.lower()
        self._recompute_visibility(self._root)
        self._rebuild()
        self.layoutChanged.emit()

    def checked_paths(self) -> list:
        result = []
        for path, checked in self._checked_paths.items():
            if checked:
                result.append(path)
        result.sort()
        return result

    def set_checked_paths(self, paths: list):
        self._checked_paths.clear()
        for p in paths:
            self._checked_paths[p] = True
        self._propagate_checks_down(self._root)
        self.checkedChanged.emit()
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount(self.index(0, 0)) - 1, 0),
            [Qt.ItemDataRole.CheckStateRole]
        )

    def set_all_checked(self, checked: bool):
        self._checked_paths.clear()
        if checked:
            all_files = FileScanner.list_entries(
                self.root_path, self.extensions, self.ignore_dirs,
                self.ignore_files, self.content_filter
            )
            for f in all_files:
                self._checked_paths[f] = True
                d = os.path.dirname(f)
                while d and d.startswith(self.root_path):
                    self._checked_paths[d] = True
                    if d == self.root_path:
                        break
                    d = os.path.dirname(d)
        self._propagate_checks_down(self._root)
        self.checkedChanged.emit()
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount(self.index(0, 0)) - 1, 0),
            [Qt.ItemDataRole.CheckStateRole]
        )

    def refresh_check_states(self):
        self._checked_paths = {p: True for p in self.checked_paths()}
        self._propagate_checks_down(self._root)
        self.checkedChanged.emit()

    def get_stale_files(self) -> list:
        stale = []
        def _check(node: TreeNode):
            if not node.is_dir and self._checked_paths.get(node.path):
                try:
                    if os.path.getmtime(node.path) != node.mtime:
                        stale.append(node.path)
                except OSError:
                    pass
            for child in node.children:
                _check(child)
        _check(self._root)
        return stale

    def refresh_mtimes(self):
        def _refresh(node: TreeNode):
            if not node.is_dir:
                try:
                    node.mtime = os.path.getmtime(node.path)
                except OSError:
                    pass
            for child in node.children:
                _refresh(child)
        _refresh(self._root)

    def change_root(self, new_path: str):
        self.beginResetModel()
        self.root_path = os.path.abspath(new_path)
        self._root = TreeNode(path=self.root_path, name=os.path.basename(self.root_path) or self.root_path, is_dir=True, depth=0)
        self._node_index = {self.root_path: self._root}
        self._checked_paths.clear()
        self.endResetModel()

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid():
            node = self._root
        else:
            node = parent.internalPointer()
        child = node.visible_child_at(row)
        if child:
            return self.createIndex(row, column, child)
        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()
        node = index.internalPointer()
        if not node or not node.parent:
            return QModelIndex()
        if node.parent == self._root:
            return self.createIndex(0, 0, self._root)
        row = node.parent.row()
        return self.createIndex(row, 0, node.parent)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.column() > 0:
            return 0
        node = parent.internalPointer() if parent.isValid() else self._root
        if not node:
            return 0
        if not node.loaded and node.is_dir:
            self._load_children(node)
        return node.visible_child_count()

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        node = index.internalPointer()
        if not node:
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            return node.name
        elif role == Qt.ItemDataRole.CheckStateRole:
            checked = self._checked_paths.get(node.path, False)
            return Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        elif role == Qt.ItemDataRole.UserRole:
            return node.path
        elif role == Qt.ItemDataRole.UserRole + 1:
            return node.is_dir
        elif role == Qt.ItemDataRole.UserRole + 2:
            return node.size
        elif role == Qt.ItemDataRole.UserRole + 3:
            return node.depth
        elif role == Qt.ItemDataRole.ForegroundRole:
            if not node.visible:
                return QColor("#4a4a5a")
        elif role == Qt.ItemDataRole.ToolTipRole:
            return node.path
        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid():
            return False
        node = index.internalPointer()
        if not node:
            return False
        if role == Qt.ItemDataRole.CheckStateRole:
            checked = value == Qt.CheckState.Checked.value if hasattr(value, 'value') else bool(value)
            self._set_node_checked(node, checked)
            self.checkedChanged.emit()
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable
        return flags

    def canFetchMore(self, parent: QModelIndex) -> bool:
        node = parent.internalPointer() if parent.isValid() else self._root
        return node is not None and node.is_dir and not node.loaded

    def fetchMore(self, parent: QModelIndex):
        node = parent.internalPointer() if parent.isValid() else self._root
        if node and node.is_dir and not node.loaded:
            self._load_children(node)
            self._recompute_visibility(node)
            self._rebuild()

    def hasChildren(self, parent: QModelIndex) -> bool:
        node = parent.internalPointer() if parent.isValid() else self._root
        if not node or not node.is_dir:
            return False
        if not node.loaded:
            self._load_children(node)
        return any(c.visible for c in node.children)

    def _rebuild(self):
        self.layoutChanged.emit()

    def _load_children(self, node: TreeNode):
        if node.loaded or not node.is_dir:
            return
        node.loaded = True
        try:
            entries = sorted(os.listdir(node.path))
        except (PermissionError, OSError):
            return

        dirs, files = [], []
        for entry in entries:
            full = os.path.join(node.path, entry)
            if os.path.isdir(full):
                if entry in self.ignore_dirs or entry.startswith('.'):
                    continue
                dirs.append(full)
            else:
                if entry in self.ignore_files or entry.startswith('.'):
                    continue
                ext = os.path.splitext(entry)[1].lower()
                if self.extensions and ext not in self.extensions:
                    continue
                if self.content_filter:
                    try:
                        with open(full, 'r', encoding='utf-8', errors='ignore') as fh:
                            if self.content_filter not in fh.read():
                                continue
                    except Exception:
                        continue
                files.append(full)

        parent_checked = self._checked_paths.get(node.path, False)

        for d in sorted(dirs):
            child = TreeNode(path=d, name=os.path.basename(d), is_dir=True, parent=node, depth=node.depth + 1)
            if parent_checked:
                self._checked_paths[d] = True
            node.children.append(child)
            self._node_index[d] = child

        for f in sorted(files):
            child = TreeNode(path=f, name=os.path.basename(f), is_dir=False, parent=node, depth=node.depth + 1)

            if parent_checked:
                self._checked_paths[f] = True

            try:
                child.size = os.path.getsize(f)
                child.mtime = os.path.getmtime(f)
            except OSError:
                pass
            node.children.append(child)
            self._node_index[f] = child

    def _recompute_visibility(self, node: TreeNode):
        for child in node.children:
            if child.is_dir:
                self._recompute_visibility(child)
                child.visible = any(c.visible for c in child.children) if child.loaded else True
            else:
                if self.search_text:
                    rel_path = os.path.relpath(child.path, self.root_path).lower()
                    child.visible = self.search_text in child.name.lower() or self.search_text in rel_path
                else:
                    child.visible = True

    def _set_node_checked(self, node: TreeNode, checked: bool):
        if checked:
            self._checked_paths[node.path] = True
        else:
            self._checked_paths.pop(node.path, None)

        if node.is_dir:
            for child in node.children:
                self._set_node_checked(child, checked)

    def _propagate_checks_down(self, node: TreeNode):
        checked = self._checked_paths.get(node.path, False)
        if node.is_dir:
            for child in node.children:
                if checked:
                    self._checked_paths[child.path] = True
                else:
                    self._checked_paths.pop(child.path, None)
                self._propagate_checks_down(child)
