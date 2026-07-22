#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# GRACE Context Manager — One-click installer for Linux & macOS
# ──────────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
DOT="\033[0;34m • \033[0m"
OK="${GREEN}✔${NC}"
INFO="${BLUE}ℹ${NC}"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}     GRACE Context Manager — Installer${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

OS="$(uname -s)"

# ── Step 1: Check / install Python ────────────────────────────
echo -e "${DOT}Checking Python..."
PYTHON=""

for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
        major=$(echo "$ver" | cut -d. -f1)
        if [ "$major" -ge 3 ]; then
            PYTHON="$cmd"
            echo -e "  ${OK} Found $cmd $ver"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    case "$OS" in
        Linux)
            echo -e "  ${INFO} Python 3 not found. Attempting install via system package manager..."
            if command -v apt-get &>/dev/null; then
                sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip
            elif command -v dnf &>/dev/null; then
                sudo dnf install -y python3 python3-pip
            elif command -v pacman &>/dev/null; then
                sudo pacman -S --noconfirm python python-pip
            else
                echo -e "  ${RED}✘ Cannot detect package manager. Install Python 3 manually:${NC}"
                echo -e "     https://www.python.org/downloads/"
                exit 1
            fi
            PYTHON="python3"
            ;;
        Darwin)
            if command -v brew &>/dev/null; then
                brew install python@3
                PYTHON="python3"
            else
                echo -e "  ${RED}✘ Install Python from: https://www.python.org/downloads/${NC}"
                exit 1
            fi
            ;;
        *)
            echo -e "  ${RED}✘ Unsupported OS. Install Python 3 manually: https://www.python.org/downloads/${NC}"
            exit 1
            ;;
    esac
    echo -e "  ${OK} Python installed"
fi

# ── Step 2: Install GRACE ──────────────────────────────────────
echo ""
echo -e "${DOT}Installing GRACE Context Manager..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Install PyQt6 + GRACE in user site
"$PYTHON" -m pip install --user --quiet PyQt6

"$PYTHON" -m pip install --user --quiet -e "$SCRIPT_DIR" 2>&1 | tail -2

# Verify
if "$PYTHON" -c "import grace_app" 2>/dev/null; then
    echo -e "  ${OK} GRACE installed successfully"
else
    echo -e "  ${RED}✘ Installation failed${NC}"
    exit 1
fi

# ── Step 3: Create launcher ────────────────────────────────────
echo ""
echo -e "${DOT}Creating desktop launcher..."

if [ "$OS" = "Linux" ]; then
    DESKTOP_FILE="$HOME/.local/share/applications/grace.desktop"
    mkdir -p "$(dirname "$DESKTOP_FILE")"
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=GRACE Context Manager
Comment=Smart context assembly for LLM workflows
Exec=$PYTHON -m grace_app.main
Icon=${SCRIPT_DIR}/grace_app/assets/icon.png
Terminal=false
Type=Application
Categories=Development;Utility;
EOF
    echo -e "  ${OK} Desktop shortcut created"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}   Done! Run with:  grace${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Quick start:"
echo -e "    ${BLUE}grace${NC}          — Launch the app"
echo ""
echo -e "  Or search 'GRACE' in your application menu."
echo ""
