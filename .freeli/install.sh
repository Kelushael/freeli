#!/bin/bash
set -e

REPO_BASE="https://raw.githubusercontent.com/Kelushael/freeli/master"
INSTALL_DIR="$HOME/.freeli"
BIN_DIR="$INSTALL_DIR/bin"

# Detect OS/Environment
OS="$(uname -s)"
if [ -n "$TERMUX_VERSION" ]; then
    OS="Termux"
fi

echo "--- Installing Freeli (Target: $OS) ---"

# 1. Install Dependencies
if [ "$OS" = "Linux" ]; then
    if command -v apt-get &> /dev/null; then
        echo "Detected Debian/Ubuntu. Installing Python..."
        
        # Check for sudo
        SUDO=""
        if [ "$EUID" -ne 0 ]; then
            if command -v sudo &> /dev/null; then
                SUDO="sudo"
            else
                echo "Warning: Not root and sudo not found. Skipping apt-get."
            fi
        fi
        
        if [ -n "$SUDO" ] || [ "$EUID" -eq 0 ]; then
            ${SUDO} apt-get update -qq
            ${SUDO} apt-get install -y -qq python3 python3-pip python3-venv curl git
        fi
    fi
elif [ "$OS" = "Termux" ]; then
    echo "Detected Termux. Installing Python..."
    pkg update -y
    pkg install -y python git curl rust binutils
    # Fix for some python packages on Termux
    export CARGO_BUILD_TARGET=aarch64-linux-android
fi

# 2. Setup Directory
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# 3. Download Source
echo "Downloading core files..."
curl -fsSL "$REPO_BASE/.freeli/freeli.py" -o "$INSTALL_DIR/freeli.py"
curl -fsSL "$REPO_BASE/gguf_wrapper.py" -o "$INSTALL_DIR/gguf_wrapper.py"

# 4. Install Python Libs
echo "Installing Python libraries..."
pip3 install requests prompt_toolkit colorama rich httpx --break-system-packages 2>/dev/null || pip3 install requests prompt_toolkit colorama rich httpx

# 5. Create Wrapper
echo '#!/bin/bash' > "$BIN_DIR/freeli"
echo "python3 \"$INSTALL_DIR/freeli.py\" \"\$@\"" >> "$BIN_DIR/freeli"
chmod +x "$BIN_DIR/freeli"

# 6. Path Advice
echo ""
echo "------------------------------------------------"
echo "[SUCCESS] Freeli installed!"
echo "------------------------------------------------"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "Add this to your shell config (.bashrc / .zshrc):"
    echo "  export PATH=\"\$PATH:$BIN_DIR\""
    echo ""
    echo "Then restart your terminal."
else
    echo "Type 'freeli' to start."
fi
