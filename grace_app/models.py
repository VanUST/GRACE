from dataclasses import dataclass, field, asdict
from typing import List

@dataclass
class ContextBlock:
    id: str
    name: str
    content: str
    category: str = "general"
    enabled: bool = True
    order: int = 0

@dataclass
class TreeNode:
    """Lightweight data node for the file tree model."""
    path: str
    name: str
    is_dir: bool
    parent: "TreeNode | None" = None
    children: List["TreeNode"] = field(default_factory=list)
    loaded: bool = False
    checked: bool = False
    size: int = 0
    mtime: float = 0.0
    visible: bool = True
    depth: int = 0

    def child_count(self) -> int:
        return len(self.children)

    def child_at(self, index: int) -> "TreeNode | None":
        if 0 <= index < len(self.children):
            return self.children[index]
        return None

    def row(self) -> int:
        if self.parent:
            try:
                return self.parent.children.index(self)
            except ValueError:
                return 0
        return 0

    def visible_child_count(self) -> int:
        return sum(1 for c in self.children if c.visible)

    def visible_child_at(self, index: int) -> "TreeNode | None":
        count = 0
        for c in self.children:
            if c.visible:
                if count == index:
                    return c
                count += 1
        return None
