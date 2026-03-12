# Freeli - Sovereign AI Agent

A local-first, agentic AI runtime for your terminal. Supports local inference (llama.cpp) and remote API connections.

## 🚀 Installation

### 🐧 Debian / Ubuntu / Linux
```bash
curl -fsSL https://raw.githubusercontent.com/Kelushael/freeli/master/.freeli/install.sh | bash
```

### 📱 Android (Termux)
1. Install Termux from F-Droid.
2. Run:
```bash
pkg update -y && pkg install -y curl
curl -fsSL https://raw.githubusercontent.com/Kelushael/freeli/master/.freeli/install.sh | bash
```

### 🪟 Windows (PowerShell)
Run as Administrator (optional, but recommended for PATH updates):
```powershell
iwr -useb https://raw.githubusercontent.com/Kelushael/freeli/master/.freeli/install.ps1 | iex
```

## ✨ Features

*   **Sovereign**: Runs locally or connects to your own private servers.
*   **Agentic Tools**: File editing, web search, SQL, code execution.
*   **Persistent Memory**: Remembers context across sessions (`/addmem`).
*   **Self-Extending**: Add new commands (`/addcmd`) or tools (`/addtool`) on the fly.
*   **Remote Spawning**: Provision remote inference servers via SSH (`/spawn`).

##  usage

```bash
freeli
```
Type `/help` or `/spawn` inside the REPL.
