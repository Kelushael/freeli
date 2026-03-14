#!/data/data/com.termux/files/usr/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  forge — freeli mobile CLI (runs in Termux, executes on VPS over SSH)
#
#  forge new <name>         scaffold Android project on VPS
#  forge build <name>       compile APK on VPS
#  forge serve <name>       serve APK on VPS:8080 → open in phone browser
#  forge ask "what" <name>  AI writes code (uses sov on VPS)
#  forge ssh                drop into VPS shell
#  forge apks               list all built APKs
#  forge pull <name>        download APK to Termux storage
#  forge config             edit config
# ─────────────────────────────────────────────────────────────────────────────

CONF_FILE="$HOME/.config/freeli/config.json"
LIME="\033[38;2;57;255;100m"; CYAN="\033[38;2;0;220;255m"
GRAY="\033[38;2;85;85;105m";  RED="\033[38;2;255;70;70m"
YLW="\033[38;2;255;200;50m";  RS="\033[0m"; BOLD="\033[1m"

ok()  { echo -e "  ${LIME}✓${RS}  $*"; }
err() { echo -e "  ${RED}✗${RS}  $*"; exit 1; }
h()   { echo -e "\n${LIME}${BOLD}⬡  $*${RS}\n"; }

# ── load config ───────────────────────────────────────────────────────────────
if [ ! -f "$CONF_FILE" ]; then
    err "run termux-install.sh first"
fi

VPS_HOST=$(python3 -c "import json; c=json.load(open('$CONF_FILE')); print(c.get('vps_host','root@axismundi.fun'))")
FORGE_DIR=$(python3 -c "import json; c=json.load(open('$CONF_FILE')); print(c.get('forge_dir','~/forge'))")

vps() {
    # run command on VPS, stream output live
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        -i "$HOME/.ssh/id_ed25519" "$VPS_HOST" "$@"
}

vps_bg() {
    # run on VPS in background (for serve)
    ssh -o StrictHostKeyChecking=no -f \
        -i "$HOME/.ssh/id_ed25519" "$VPS_HOST" "$@"
}

CMD="${1:-help}"
shift 2>/dev/null || true

case "$CMD" in

# ── new ───────────────────────────────────────────────────────────────────────
new)
    NAME="${1:?usage: forge new <name>}"
    h "scaffolding $NAME on VPS"
    vps "python3 /usr/local/bin/forge new $NAME" || \
    vps "python3 ~/forge-cli.py new $NAME"
    echo ""
    ok "$NAME scaffolded on VPS"
    echo -e "  ${CYAN}forge build $NAME${RS}"
    ;;

# ── build ─────────────────────────────────────────────────────────────────────
build)
    NAME="${1:?usage: forge build <name>}"
    h "building $NAME on VPS"
    echo -e "  ${GRAY}compiling... (heavy iron spinning up)${RS}\n"
    vps "cd $FORGE_DIR/$NAME && gradle assembleDebug --console=plain 2>&1"
    echo ""
    # find and report APK
    APK=$(vps "find $FORGE_DIR/$NAME -name '*.apk' 2>/dev/null | head -1")
    if [ -n "$APK" ]; then
        ok "APK ready: $APK"
        echo -e "  ${CYAN}forge serve $NAME${RS}  →  open in browser  →  install"
    else
        echo -e "  ${YLW}build finished — check output above for APK location${RS}"
    fi
    ;;

# ── serve ─────────────────────────────────────────────────────────────────────
serve)
    NAME="${1:-}"
    h "serving APK"
    if [ -n "$NAME" ]; then
        APK_DIR=$(vps "find $FORGE_DIR/$NAME -name '*.apk' -exec dirname {} \; 2>/dev/null | head -1")
    else
        APK_DIR="$FORGE_DIR"
    fi
    [ -z "$APK_DIR" ] && APK_DIR="$FORGE_DIR"

    # kill any existing server on 8080
    vps "pkill -f 'python3 -m http.server 8080' 2>/dev/null; true" 2>/dev/null

    VPS_IP=$(python3 -c "import json; c=json.load(open('$CONF_FILE')); print(c.get('vps_ip','76.13.24.113'))")

    echo -e "  ${LIME}open in phone browser:${RS}"
    echo -e "  ${CYAN}http://${VPS_IP}:8080${RS}"
    echo ""
    echo -e "  ${GRAY}tap the .apk → install  ·  ctrl+c to stop${RS}\n"
    vps "cd '$APK_DIR' && python3 -m http.server 8080"
    ;;

# ── ask ───────────────────────────────────────────────────────────────────────
ask)
    QUESTION="${1:?usage: forge ask \"question\" <name>}"
    NAME="${2:-}"
    h "asking AI: $QUESTION"
    if [ -n "$NAME" ]; then
        PROMPT="Write Android Java code for: $QUESTION. Return only valid Java for MainActivity.java, complete class, no explanation."
        JAVA_FILE=$(vps "find $FORGE_DIR/$NAME -name 'MainActivity.java' 2>/dev/null | head -1")
        if [ -n "$JAVA_FILE" ]; then
            echo -e "  ${GRAY}asking sovereign on VPS...${RS}"
            vps "python3 ~/sovereign.py --once \"$PROMPT\" > /tmp/forge_code.java 2>/dev/null && \
                 cat /tmp/forge_code.java > '$JAVA_FILE' && echo 'written: $JAVA_FILE'"
            ok "code written — run: forge build $NAME"
        else
            err "project not found: $NAME — run forge new $NAME first"
        fi
    else
        # just ask, print to terminal
        vps "python3 ~/sovereign.py --once \"$QUESTION\""
    fi
    ;;

# ── apks ─────────────────────────────────────────────────────────────────────
apks)
    h "built APKs on VPS"
    vps "find $FORGE_DIR -name '*.apk' 2>/dev/null | while read f; do
        size=\$(du -sh \"\$f\" | cut -f1)
        echo \"  \$size  \$f\"
    done"
    ;;

# ── pull ─────────────────────────────────────────────────────────────────────
pull)
    NAME="${1:?usage: forge pull <name>}"
    h "pulling APK to Termux"
    APK=$(vps "find $FORGE_DIR/$NAME -name '*.apk' 2>/dev/null | head -1")
    [ -z "$APK" ] && err "no APK found for $NAME — run forge build $NAME first"
    DEST="$HOME/storage/downloads/${NAME}.apk"
    mkdir -p "$HOME/storage/downloads" 2>/dev/null
    scp -o StrictHostKeyChecking=no \
        -i "$HOME/.ssh/id_ed25519" \
        "${VPS_HOST}:${APK}" "$DEST" && \
    ok "saved to $DEST"
    echo -e "  ${GRAY}open Files app → Downloads → install${RS}"
    ;;

# ── ssh ───────────────────────────────────────────────────────────────────────
ssh)
    h "VPS shell"
    ssh -o StrictHostKeyChecking=no \
        -i "$HOME/.ssh/id_ed25519" "$VPS_HOST"
    ;;

# ── config ───────────────────────────────────────────────────────────────────
config)
    nano "$CONF_FILE"
    ;;

# ── help ─────────────────────────────────────────────────────────────────────
*)
    echo ""
    echo -e "${LIME}${BOLD}  ⬡  FORGE MOBILE${RS}  ${GRAY}Android factory from Termux${RS}"
    echo ""
    echo -e "  ${CYAN}forge new <name>${RS}           scaffold app on VPS"
    echo -e "  ${CYAN}forge build <name>${RS}         compile APK (VPS heavy iron)"
    echo -e "  ${CYAN}forge serve <name>${RS}         serve :8080 → open in browser → install"
    echo -e "  ${CYAN}forge pull <name>${RS}          download APK to phone storage"
    echo -e "  ${CYAN}forge apks${RS}                 list all built APKs on VPS"
    echo -e "  ${CYAN}forge ask \"what\" <name>${RS}    AI writes code via sovereign"
    echo -e "  ${CYAN}forge ssh${RS}                  drop into VPS shell"
    echo -e "  ${CYAN}forge config${RS}               edit config"
    echo ""
    ;;
esac
