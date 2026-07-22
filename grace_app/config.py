from pathlib import Path

CONFIG_DIR = Path.home() / ".grace_manager"
PROFILES_FILE = CONFIG_DIR / "profiles.json"
RECENT_FILE = CONFIG_DIR / "recent_projects.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

DEFAULT_EXTENSIONS = ".py, .md, .txt, .json, .yaml, .toml, .cfg, .ini"
DEFAULT_IGNORE_DIRS = ".git, __pycache__, venv, node_modules, .venv, env, .tox, dist, build"
DEFAULT_IGNORE_FILES = ".env, secrets.py, credentials.json"

SCALE_STEPS = [75, 90, 100, 110, 125, 150, 175, 200]

MAX_FILE_SIZE = 1024 * 1024

EXT_ICONS = {
    ".py": "\ue606", ".js": "JS", ".ts": "TS", ".jsx": "JS",
    ".tsx": "TS", ".md": "MD", ".json": "{}", ".yaml": "Y",
    ".yml": "Y", ".xml": "X", ".html": "H", ".css": "#",
    ".toml": "T", ".cfg": "C", ".ini": "I", ".rs": "RS",
    ".go": "Go", ".java": "Jv", ".c": "C", ".cpp": "C+",
    ".h": "H", ".rb": "Rb", ".php": "P", ".sql": "SQ",
    ".sh": "Sh", ".bash": "Sh", ".zsh": "Sh", ".fish": "Fi",
    ".ps1": "PS", ".bat": "B", ".cmake": "CM", ".make": "Mk",
    ".dockerfile": "D", ".kt": "Kt", ".swift": "Sw",
    ".r": "R", ".m": "M", ".scala": "Sc", ".lua": "Lu",
    ".vim": "Vi", ".tex": "Tx", ".gitignore": "Gi",
}
