# GRACE Context Manager

A modern GUI tool for assembling high-quality context for LLM coding assistants. Built with CustomTkinter.

## Key Features

- **Context Blocks**: Reusable text snippets organized by category (tech stack, constraints, rules). Toggle on/off as needed.
- **Smart File Selection**: Tree view with checkboxes, file size display, and quick select/deselect.
- **Advanced Filtering**: Filter by extension, ignore patterns, and content search.
- **Filter Presets**: Save and load filter configurations for different project types.
- **Live Preview**: See assembled context with token count estimation before copying.
- **Preview Modes**: Full context, structure only, or files only.

## Installation

```bash
pip install -e .
```

Then run:
```bash
grace
```

## Workflow

1. **Select Project**: Click 📂 to choose your project directory
2. **Add Context Blocks**: Create reusable blocks for tech stack, coding rules, etc.
3. **Filter Files**: Set extensions, ignore dirs/files, optional content filter
4. **Select Files**: Check files/directories to include in context
5. **Add Instruction**: Write your task in the instruction box
6. **Copy**: Click "Copy Context" and paste into your LLM

## Context Blocks

Context blocks are saved in `~/.grace_manager/profiles.json`. They persist across sessions.

Organize blocks by category:
- `tech` - Technology stack info
- `constraints` - Coding rules and constraints  
- `context` - Project-specific context
- Any custom category

## Filter Presets

Save common filter configurations:
- Python project: `.py, .toml, .yaml, .md`
- Web project: `.js, .ts, .jsx, .tsx, .css, .html`
- Config only: `.yaml, .json, .toml`

Presets are saved in `~/.grace_manager/filter_presets.json`.

## Keyboard Shortcuts

- `Ctrl+A` - Select all files
- `Ctrl+D` - Deselect all files
- `Ctrl+C` - Copy context (when preview focused)
