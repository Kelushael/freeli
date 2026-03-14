#!/bin/bash
# Freeli Installer (Linux/Termux/MacOS)
# Usage: curl -L https://raw.githubusercontent.com/Kelushael/freeli/master/install.sh | bash

set -e

echo "Installing Freeli Sovereign Client..."

# 1. Check Dependencies
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required. Please install it."
    exit 1
fi

if ! command -v ssh &> /dev/null; then
    if command -v pkg &> /dev/null; then 
        echo "Detected Termux/Android."
        pkg update -y && pkg install openssh termux-api git wget python -y
    elif command -v apt &> /dev/null; then 
        echo "Detected Debian/Ubuntu."
        sudo apt update && sudo apt install openssh-client git wget python3 -y
    fi
fi

# 2. Setup Directories
FREELI_HOME="$HOME/.freeli"
mkdir -p "$FREELI_HOME/bin" "$FREELI_HOME/config" "$FREELI_HOME/workspace"

# 3. Download Freeli CLI
REPO_URL="https://raw.githubusercontent.com/Kelushael/freeli/master/.freeli/freeli.py"
echo "Downloading Freeli from $REPO_URL..."
curl -sL "$REPO_URL" -o "$FREELI_HOME/bin/freeli.py"

# 4. Create Wrapper Script
WRAPPER="$FREELI_HOME/bin/freeli"
cat << 'EOF' > "$WRAPPER"
#!/bin/sh
# Freeli Wrapper
exec python3 "$HOME/.freeli/bin/freeli.py" "$@"
EOF
chmod +x "$WRAPPER"

# 5. Add to PATH
SHELL_RC="$HOME/.bashrc"
if [ -n "$ZSH_VERSION" ]; then SHELL_RC="$HOME/.zshrc"; fi

if [[ ":$PATH:" != *":$FREELI_HOME/bin:"* ]]; then
    echo "Adding $FREELI_HOME/bin to PATH in $SHELL_RC"
    echo 'export PATH="$HOME/.freeli/bin:$PATH"' >> "$SHELL_RC"
fi

# 6. Pre-configure Remote (Auto-Connect to Axis Mundi)
CONFIG_FILE="$FREELI_HOME/config/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo '{
    "remote": {
        "url": "http://187.77.208.28:8000",
        "ssh_host": "root@187.77.208.28"
    }
}' > "$CONFIG_FILE"
    echo "Configured default remote: http://187.77.208.28:8000"
fi

echo ""
echo "==========================================="
echo "  Freeli Installed Successfully!"
echo "  Restart your shell or run: source $SHELL_RC"
echo "  Then type: freeli"
echo "==========================================="
