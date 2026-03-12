# Freeli - Sovereign AI Agent

A local-first, agentic AI runtime for your terminal. Supports local inference (llama.cpp) and remote API connections.

## 🚀 Installation

### Windows (PowerShell)
Run this command in PowerShell:
```powershell
iwr -useb https://raw.githubusercontent.com/Kelushael/free-li/master/install.ps1 | iex
```

### Mac / Linux / Termux
Run this command in your terminal:
```bash
curl -fsSL https://raw.githubusercontent.com/Kelushael/free-li/master/install.sh | bash
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
