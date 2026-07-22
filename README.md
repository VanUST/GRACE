# GRACE Context Manager

A modern GUI tool for assembling high-quality context for LLM coding assistants. Built with PyQt6.

## Key Features

- **Context Blocks**: Reusable text snippets organized by category (tech stack, constraints, rules). Toggle on/off as needed.
- **Smart File Selection**: Tree view with checkboxes, file size display, and quick select/deselect.
- **Advanced Filtering**: Filter by extension, ignore patterns, and content search.
- **Dynamic Extension Detection**: Auto-detect all file extensions in your project with select/deselect all for quick filtering.
- **Live Preview**: See assembled context with token count estimation before copying.
- **Preview Modes**: Full context, structure only, or files only.
- **Dynamic Context Refresh**: Refresh selected file contents when files change on disk without re-selecting.
- **Scalable UI**: Adjustable interface scaling (75%-200%) for different screen sizes and devices.
- **Keyboard Shortcuts**: Ctrl+C copy, Ctrl+N new block, Ctrl+R refresh, Ctrl+O browse, Ctrl+A/D select all/none.

## One-Click Install

### Windows

Download and run: **[install.bat](install.bat)** (right-click → "Run")

This installs Python (if needed), PyQt6, and GRACE automatically.

### Linux / macOS

```bash
./install.sh
```

### Manual Install

```bash
pip install -e .
```

Then run:

```bash
grace
```

## Workflow

1. **Select Project**: Click **Browse** to choose your project directory
2. **Add Context Blocks**: Create reusable blocks for tech stack, coding rules, etc.
3. **Detect Extensions**: Click **Detect** to auto-discover all file extensions in the project, then toggle what to include
4. **Filter Files**: Set extensions, ignore dirs/files, optional content filter
5. **Select Files**: Check files/directories to include in context
6. **Add Instruction**: Write your task in the instruction box
7. **Refresh**: Click **Refresh Context** to reload changed files from disk
8. **Copy**: Click **Copy Context** and paste into your LLM

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+C` | Copy context to clipboard |
| `Ctrl+N` | New context block |
| `Ctrl+R` | Refresh context |
| `Ctrl+O` | Browse directory |
| `Ctrl+A` | Select all files |
| `Ctrl+D` | Deselect all files |

## Context Blocks

Context blocks are saved in `~/.grace_manager/profiles.json`. They persist across sessions.

Organize blocks by category:
- `tech` - Technology stack info
- `constraints` - Coding rules and constraints
- `context` - Project-specific context
- Any custom category

## UI Scaling

Use the scale buttons in the sidebar to adjust the UI. Scaling preference is saved in `~/.grace_manager/settings.json` and persists across sessions.

## Configuration Files

| File | Purpose |
|------|---------|
| `~/.grace_manager/profiles.json` | Context blocks |
| `~/.grace_manager/recent_projects.json` | Recently opened projects |
| `~/.grace_manager/settings.json` | UI preferences (scaling, etc.) |
