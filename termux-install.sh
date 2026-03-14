#!/data/data/com.termux/files/usr/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  FREELI MOBILE — Termux install
#  curl -L https://raw.githubusercontent.com/Kelushael/freeli/master/termux-install.sh | bash
#
#  What this gives you:
#    • forge   — build Android APKs on your VPS from your phone
#    • sov     — sovereign AI terminal via VPS
#    • r1      — deep reasoning AI in your terminal
#
#  Pipeline: Termux → SSH into VPS → compile APK → serve :8080 → tap to install
# ─────────────────────────────────────────────────────────────────────────────
set -e

LIME="\033[38;2;57;255;100m"; CYAN="\033[38;2;0;220;255m"
GRAY="\033[38;2;85;85;105m";  RED="\033[38;2;255;70;70m"
RS="\033[0m"; BOLD="\033[1m"

p()  { echo -e "  $*"; }
ok() { echo -e "  ${LIME}✓${RS}  $*"; }
h()  { echo -e "\n${LIME}${BOLD}⬡  $*${RS}"; }

clear
echo ""
echo -e "${LIME}${BOLD}  ⬡  FREELI MOBILE${RS}"
echo -e "  ${GRAY}sovereign forge · from your phone · your iron${RS}"
echo ""

# ── 1. Termux packages ────────────────────────────────────────────────────────
h "packages"
pkg update -y -q 2>/dev/null
pkg install -y -q python openssh git wget curl nano 2>/dev/null
ok "python, ssh, git, curl ready"

# ── 2. Python deps ────────────────────────────────────────────────────────────
h "python deps"
pip install -q requests websockets 2>/dev/null
ok "requests, websockets"

# ── 3. Config dir ─────────────────────────────────────────────────────────────
h "config"
CONF="$HOME/.config/freeli"
mkdir -p "$CONF"

# write config if not exists
if [ ! -f "$CONF/config.json" ]; then
    cat > "$CONF/config.json" << 'CONFJSON'
{
  "vps_host":  "root@axismundi.fun",
  "vps_ip":    "76.13.24.113",
  "api_url":   "https://axismundi.fun/v1",
  "model":     "axis-model",
  "forge_dir": "~/forge"
}
CONFJSON
    ok "config written → $CONF/config.json"
else
    ok "config exists"
fi

# ── 4. SSH key setup ──────────────────────────────────────────────────────────
h "SSH key"
if [ ! -f "$HOME/.ssh/id_ed25519" ]; then
    mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
    ssh-keygen -t ed25519 -f "$HOME/.ssh/id_ed25519" -N "" -C "freeli-mobile" -q
    ok "key generated"
    echo ""
    echo -e "  ${CYAN}Add this public key to your VPS authorized_keys:${RS}"
    echo -e "  ${GRAY}ssh-copy-id -i ~/.ssh/id_ed25519.pub root@YOUR_VPS_IP${RS}"
    echo ""
    cat "$HOME/.ssh/id_ed25519.pub"
    echo ""
else
    ok "SSH key exists"
fi

# ── 5. Download mobile scripts ────────────────────────────────────────────────
h "forge mobile CLI"
BASE="https://raw.githubusercontent.com/Kelushael/freeli/master"
BINDIR="$HOME/.local/bin"
mkdir -p "$BINDIR"

curl -sL "$BASE/mobile.sh" -o "$BINDIR/forge"
chmod +x "$BINDIR/forge"
ok "forge → $BINDIR/forge"

# ── 6. PATH ───────────────────────────────────────────────────────────────────
h "PATH"
RCFILE="$HOME/.bashrc"
grep -q '\.local/bin' "$RCFILE" 2>/dev/null || \
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$RCFILE"
export PATH="$HOME/.local/bin:$PATH"
ok "PATH updated"

# ── 7. SSH config shortcut ───────────────────────────────────────────────────
mkdir -p "$HOME/.ssh"
grep -q "Host forge" "$HOME/.ssh/config" 2>/dev/null || cat >> "$HOME/.ssh/config" << 'SSHCONF'
Host forge
    HostName axismundi.fun
    User root
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 60
SSHCONF
chmod 600 "$HOME/.ssh/config" 2>/dev/null || true
ok "ssh alias 'forge' configured"

# ── done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${LIME}${BOLD}  ⬡  READY${RS}"
echo ""
echo -e "  ${CYAN}forge new myapp${RS}        ${GRAY}scaffold app on VPS${RS}"
echo -e "  ${CYAN}forge build myapp${RS}      ${GRAY}compile APK on VPS (heavy iron)${RS}"
echo -e "  ${CYAN}forge serve myapp${RS}      ${GRAY}serve APK → open in browser → tap install${RS}"
echo -e "  ${CYAN}forge ssh${RS}              ${GRAY}drop into VPS shell${RS}"
echo -e "  ${CYAN}forge ask \"what\" myapp${RS}  ${GRAY}AI writes code via sov/r1/glm${RS}"
echo ""
echo -e "  ${GRAY}restart shell or: source ~/.bashrc${RS}"
echo ""
