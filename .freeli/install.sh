#!/bin/bash
set -e

REPO="https://raw.githubusercontent.com/Kelushael/free-li/master"
DIR="$HOME/.freeli"
BIN="$DIR/bin"

echo "Installing Freeli..."

# Create dirs
mkdir -p "$BIN"

# Download source
echo "Downloading core files..."
curl -fsSL "$REPO/freeli.py" -o "$DIR/freeli.py"

# Create wrapper
echo '#!/bin/bash' > "$BIN/freeli"
echo 'python3 "$HOME/.freeli/freeli.py" "$@"' >> "$BIN/freeli"
chmod +x "$BIN/freeli"

# Path advice
echo ""
echo "[SUCCESS] Freeli installed to $BIN"
echo "To use it, add this to your PATH:"
echo ""
echo "  export PATH=\"\$PATH:$BIN\""
echo ""
echo "Then type 'freeli' to start."
