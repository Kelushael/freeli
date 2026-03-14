#!/usr/bin/env python3
"""
FREELI - Sovereign Local AI Runtime
Axis Mundi Stack - Full Agentic Version + Copilot Capabilities
"""

import json
import os
import sys
import subprocess
import argparse
import socket
import time
import urllib.request
import urllib.error
import urllib.parse
import webbrowser
import http.server
import threading
import re
import sqlite3
from pathlib import Path
from datetime import datetime

# PATHS
FREELI_HOME = Path.home() / ".freeli"
CONFIG_PATH = FREELI_HOME / "config" / "config.json"
BIN_DIR = FREELI_HOME / "bin"
MODELS_DIR = Path.home() / "models"
WORKSPACE = FREELI_HOME / "workspace"
ARTIFACTS = FREELI_HOME / "artifacts"

# Ensure dirs exist
WORKSPACE.mkdir(parents=True, exist_ok=True)
ARTIFACTS.mkdir(parents=True, exist_ok=True)

# Executables
if sys.platform == "win32":
    LLAMA_SERVER = BIN_DIR / "llama-server.exe"
    LLAMA_CLI = BIN_DIR / "llama-cli.exe"
else:
    LLAMA_SERVER = BIN_DIR / "llama-server"
    LLAMA_CLI = BIN_DIR / "llama-cli"


def find_models():
    models = []
    # Search paths: ., .freeli/models, ~/models, Downloads
    search_paths = [Path.cwd(), FREELI_HOME / "models", MODELS_DIR, Path.home() / "Downloads"]
    
    for path in search_paths:
        if path.exists():
            models.extend(path.glob("*.gguf"))
            
    # Remove duplicates
    models = list(set(models))
    
    # Sort by: 1. contains 'qwen', 2. size (desc)
    def sort_key(p):
        is_qwen = "qwen" in p.name.lower()
        return (not is_qwen, -p.stat().st_size) # False < True, so Qwen comes first
        
    return sorted(models, key=sort_key)

def is_port_open(host, port, timeout=2):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except:
        return False

# ═══════════════════════════════════════════════════════════════
# TOOLS - The model can use these
# ═══════════════════════════════════════════════════════════════

class Tools:
    @staticmethod
    def execute_code(code: str, lang: str = "python") -> str:
        """Execute code and return output."""
        try:
            if lang == "python":
                result = subprocess.run([sys.executable, "-c", code], 
                    capture_output=True, text=True, timeout=60, cwd=str(WORKSPACE))
            elif lang in ["powershell", "ps1"]:
                result = subprocess.run(["powershell", "-Command", code],
                    capture_output=True, text=True, timeout=60, cwd=str(WORKSPACE))
            elif lang in ["cmd", "batch"]:
                result = subprocess.run(["cmd", "/c", code],
                    capture_output=True, text=True, timeout=60, cwd=str(WORKSPACE))
            elif lang == "node":
                result = subprocess.run(["node", "-e", code],
                    capture_output=True, text=True, timeout=60, cwd=str(WORKSPACE))
            else:
                return f"[ERROR] Unknown language: {lang}"
            
            out = result.stdout.strip()
            if result.stderr:
                out += f"\n[STDERR] {result.stderr.strip()}"
            return out or "[No output]"
        except subprocess.TimeoutExpired:
            return "[ERROR] Execution timed out (60s)"
        except Exception as e:
            return f"[ERROR] {e}"

    @staticmethod
    def write_file(path: str, content: str) -> str:
        """Write content to file."""
        try:
            p = Path(path)
            if not p.is_absolute():
                p = WORKSPACE / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8')
            return f"[OK] Written to {p}"
        except Exception as e:
            return f"[ERROR] {e}"
    
    @staticmethod
    def read_file(path: str) -> str:
        """Read file content."""
        try:
            p = Path(path)
            if not p.is_absolute():
                p = WORKSPACE / path
            return p.read_text(encoding='utf-8')
        except Exception as e:
            return f"[ERROR] {e}"
    
    @staticmethod
    def edit_file(path: str, old_str: str, new_str: str) -> str:
        """Edit file by replacing string."""
        try:
            p = Path(path)
            if not p.is_absolute(): p = WORKSPACE / path
            if not p.exists(): return f"[ERROR] File not found: {path}"
            
            content = p.read_text(encoding='utf-8')
            if old_str not in content:
                # Try sloppy match (ignore whitespace)
                return "[ERROR] old_str not found in file (exact match required)"
            
            new_content = content.replace(old_str, new_str, 1)
            p.write_text(new_content, encoding='utf-8')
            return f"[OK] File edited: {path}"
        except Exception as e:
            return f"[ERROR] {e}"

    @staticmethod
    def list_dir(path: str = ".") -> str:
        """List directory contents."""
        try:
            p = Path(path)
            if not p.is_absolute():
                p = WORKSPACE / path
            items = list(p.iterdir())
            return "\n".join(f"{'[DIR]' if i.is_dir() else '[FILE]'} {i.name}" for i in items)
        except Exception as e:
            return f"[ERROR] {e}"

    @staticmethod
    def grep_files(pattern: str, path: str = ".") -> str:
        """Grep for pattern in files."""
        try:
            p = Path(path)
            if not p.is_absolute(): p = WORKSPACE / path
            
            results = []
            if p.is_file():
                files = [p]
            else:
                files = p.rglob("*")
                
            for f in files:
                if f.is_file():
                    try:
                        content = f.read_text(encoding='utf-8', errors='ignore')
                        lines = content.splitlines()
                        for i, line in enumerate(lines):
                            if pattern in line:
                                rel_path = f.relative_to(WORKSPACE) if f.is_relative_to(WORKSPACE) else f.name
                                results.append(f"{rel_path}:{i+1}: {line.strip()}")
                    except: pass
            return "\n".join(results[:50]) or "[No matches]"
        except Exception as e:
            return f"[ERROR] {e}"

    @staticmethod
    def web_search(query: str) -> str:
        """Search the web using DuckDuckGo."""
        try:
            q = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={q}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8')
            # Parse results
            results = []
            for m in re.finditer(r'<a class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>', html):
                results.append(f"• {m.group(2)}: {m.group(1)}")
                if len(results) >= 5:
                    break
            return "\n".join(results) if results else "[No results]"
        except Exception as e:
            return f"[ERROR] {e}"

    @staticmethod
    def fetch_url(url: str) -> str:
        """Fetch URL content."""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                text = resp.read().decode('utf-8')
                return text[:10000] # Limit size
        except Exception as e:
            return f"[ERROR] {e}"

    @staticmethod
    def execute_sql(db_path: str, query: str) -> str:
        """Execute SQL query."""
        try:
            p = Path(db_path)
            if not p.is_absolute(): p = WORKSPACE / db_path
            
            # Ensure db exists
            is_new = not p.exists()
            conn = sqlite3.connect(p)
            cursor = conn.cursor()
            
            try:
                cursor.execute(query)
                if query.strip().upper().startswith("SELECT"):
                    rows = cursor.fetchall()
                    if cursor.description:
                        cols = [description[0] for description in cursor.description]
                        result = [dict(zip(cols, row)) for row in rows]
                        conn.close()
                        return json.dumps(result, indent=2)
                    else:
                        conn.close()
                        return "[]"
                else:
                    conn.commit()
                    conn.close()
                    return "[OK] Query executed"
            except Exception as e:
                conn.close()
                return f"[SQL ERROR] {e}"
        except Exception as e:
            return f"[ERROR] {e}"

    @staticmethod
    def ask_user(question: str) -> str:
        """Ask user a question."""
        print(f"\n[FREELI WANTS TO KNOW] {question}")
        try:
            ans = input("> ")
            return ans
        except EOFError:
            return ""

    @staticmethod
    def create_artifact(name: str, html_content: str, auto_open: bool = True) -> str:
        """Create an HTML artifact and optionally open in browser."""
        try:
            if not name.endswith('.html'):
                name += '.html'
            path = ARTIFACTS / name
            path.write_text(html_content, encoding='utf-8')
            
            if auto_open:
                webbrowser.open(f'file://{path}')
            return f"[OK] Artifact created: {path}"
        except Exception as e:
            return f"[ERROR] {e}"
    
    @staticmethod
    def serve_artifacts(port: int = 8888) -> str:
        """Start a local web server for artifacts."""
        if is_port_open("localhost", port):
            return f"[OK] Server already running on http://localhost:{port}"
        
        def run_server():
            os.chdir(str(ARTIFACTS))
            handler = http.server.SimpleHTTPRequestHandler
            with socketserver.TCPServer(("", port), handler) as httpd:
                httpd.serve_forever()
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        time.sleep(0.5)
        return f"[OK] Artifact server running at http://localhost:{port}"
    
    @staticmethod
    def screenshot() -> str:
        """Take a screenshot (requires pillow)."""
        try:
            from PIL import ImageGrab
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = WORKSPACE / f"screenshot_{ts}.png"
            img = ImageGrab.grab()
            img.save(path)
            return f"[OK] Screenshot saved: {path}"
        except ImportError:
            return "[ERROR] Install pillow: pip install pillow"
        except Exception as e:
            return f"[ERROR] {e}"


import socketserver

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

class Config:
    def __init__(self):
        self.path = CONFIG_PATH
        self.data = self._load()
    
    def _load(self):
        if self.path.exists():
            try:
                return json.load(open(self.path, encoding='utf-8'))
            except: pass
        return self._defaults()
    
    def _defaults(self):
        models = find_models()
        return {
            "version": "0.1.0",
            "model": {"path": str(models[0]) if models else "", "context_length": 4096, "threads": 8},
            "api": {"host": "0.0.0.0", "port": 8125},
            "remote": {
                "enabled": True, 
                "url": "http://187.77.208.28:8000",
                "key": "ocHphHIRM2BHNivGt0F34qtc2RcFq18Z7tkF1bWmQ75wQyY1abUlfxCKzXAveUJv"
            },
            "servers": {
                "origin": {
                    "url": "http://187.77.208.28:8000",
                    "key": "ocHphHIRM2BHNivGt0F34qtc2RcFq18Z7tkF1bWmQ75wQyY1abUlfxCKzXAveUJv"
                }
            },
            "tools": {
                "code_execution": True,
                "file_access": True,
                "web_search": True,
                "artifacts": True,
                "screenshot": True
            },
            "system_prompt": AGENT_SYSTEM_PROMPT,
            "inference": {"temperature": 0.7, "max_tokens": 4096}
        }
    
    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        json.dump(self.data, open(self.path, 'w', encoding='utf-8'), indent=2)
    
    def get(self, key, default=None):
        keys = key.split('.')
        val = self.data
        for k in keys:
            if isinstance(val, dict): val = val.get(k, default)
            else: return default
        return val


# ═══════════════════════════════════════════════════════════════
# AGENT SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════

AGENT_SYSTEM_PROMPT = """You are Freeli, a sovereign AI agent running on Axis Mundi.
You have access to these tools. To use them, output XML tags:

<tool name="execute">
lang: python
---
print("Hello World")
</tool>

<tool name="write_file">
path: app.html
---
<!DOCTYPE html>
<html>...</html>
</tool>

<tool name="read_file">myfile.txt</tool>

<tool name="edit_file">
path: src/main.py
old_str: def foo(): pass
---
def foo():
    print("bar")
</tool>

<tool name="list_dir">.</tool>

<tool name="grep_files">
pattern: TODO
path: src
</tool>

<tool name="web_search">latest AI news</tool>

<tool name="fetch_url">https://example.com</tool>

<tool name="execute_sql">
db: data.db
---
SELECT * FROM users
</tool>

<tool name="ask_user">What is your name?</tool>

<tool name="artifact">
name: my_app.html
---
<!DOCTYPE html>
<html>
<head><title>My App</title></head>
<body>
<h1>Hello!</h1>
<script>console.log("Running!")</script>
</body>
</html>
</tool>

<tool name="screenshot"></tool>

When creating visual apps:
1. Use <tool name="artifact"> to create HTML/JS apps
2. They auto-open in browser
3. Include all CSS/JS inline

Be helpful, direct, and take action. Don't just describe - DO."""


# ═══════════════════════════════════════════════════════════════
# FREELI AGENT
# ═══════════════════════════════════════════════════════════════

class Freeli:
    def __init__(self):
        self.config = Config()
        self.tools = Tools()
    
    def get_model(self):
        # Fix: Handle dict vs string config
        val = self.config.get("model")
        path = ""
        if isinstance(val, dict):
            path = val.get("path", "")
        elif isinstance(val, str):
            path = val
            
        if path and Path(path).exists():
            return str(path)
        models = find_models()
        return str(models[0]) if models else None
    
    def parse_tool_calls(self, text: str) -> list:
        """Parse <tool> tags from model output."""
        calls = []
        pattern = r'<tool name="(\w+)">(.*?)</tool>'
        for m in re.finditer(pattern, text, re.DOTALL):
            calls.append((m.group(1), m.group(2).strip()))
        return calls
    
    def execute_tool(self, name: str, content: str) -> str:
        """Execute a tool call."""
        if name == "execute":
            lines = content.split("\n")
            lang = "python"
            code_start = 0
            for i, line in enumerate(lines):
                if line.startswith("lang:"):
                    lang = line.split(":", 1)[1].strip()
                if line.strip() == "---":
                    code_start = i + 1
                    break
            code = "\n".join(lines[code_start:])
            return self.tools.execute_code(code, lang)
        
        elif name == "write_file":
            lines = content.split("\n")
            path = ""
            content_start = 0
            for i, line in enumerate(lines):
                if line.startswith("path:"):
                    path = line.split(":", 1)[1].strip()
                if line.strip() == "---":
                    content_start = i + 1
                    break
            file_content = "\n".join(lines[content_start:])
            return self.tools.write_file(path, file_content)
        
        elif name == "read_file":
            return self.tools.read_file(content)
        
        elif name == "edit_file":
            lines = content.split("\n")
            path = ""
            old_str = ""
            new_str_start = 0
            for i, line in enumerate(lines):
                if line.startswith("path:"):
                    path = line.split(":", 1)[1].strip()
                elif line.startswith("old_str:"):
                    old_str = line.split(":", 1)[1].strip()
                elif line.strip() == "---":
                    new_str_start = i + 1
                    break
            
            new_str = "\n".join(lines[new_str_start:])
            return self.tools.edit_file(path, old_str, new_str)

        elif name == "list_dir":
            return self.tools.list_dir(content or ".")
            
        elif name == "grep_files":
            lines = content.split("\n")
            pattern = ""
            path = "."
            for line in lines:
                if line.startswith("pattern:"):
                    pattern = line.split(":", 1)[1].strip()
                elif line.startswith("path:"):
                    path = line.split(":", 1)[1].strip()
            return self.tools.grep_files(pattern, path)
        
        elif name == "web_search":
            return self.tools.web_search(content)

        elif name == "fetch_url":
            return self.tools.fetch_url(content)
            
        elif name == "ask_user":
            return self.tools.ask_user(content)

        elif name == "execute_sql":
            lines = content.split("\n")
            db = "data.db"
            query_start = 0
            for i, line in enumerate(lines):
                if line.startswith("db:"):
                    db = line.split(":", 1)[1].strip()
                if line.strip() == "---":
                    query_start = i + 1
                    break
            query = "\n".join(lines[query_start:])
            return self.tools.execute_sql(db, query)
        
        elif name == "artifact":
            lines = content.split("\n")
            name_val = "artifact.html"
            html_start = 0
            for i, line in enumerate(lines):
                if line.startswith("name:"):
                    name_val = line.split(":", 1)[1].strip()
                if line.strip() == "---":
                    html_start = i + 1
                    break
            html = "\n".join(lines[html_start:])
            return self.tools.create_artifact(name_val, html)
        
        elif name == "screenshot":
            return self.tools.screenshot()
        
        return f"[ERROR] Unknown tool: {name}"

    
    def _get_system_prompt(self):
        # Full Sovereign Prompt
        base = AGENT_SYSTEM_PROMPT
        mem_path = WORKSPACE / "memory.txt"
        if mem_path.exists():
            mem = mem_path.read_text(encoding="utf-8").strip()
            if mem:
                base += f"\n\n--- MEMORY ---\n{mem}"
        return base

    def _ensure_remote_key(self):
        """Lazy-load API key from origin via SSH if missing."""
        remote = self.config.data.get("remote", {})
        url = remote.get("url", "")
        key = remote.get("key", "")
        
        # Colors (since config doesn't have them)
        BLUE = "\033[96m"
        PINK = "\033[95m"
        RESET = "\033[0m"

        # If we have a URL but no key (or placeholder), try to fetch it
        if url and (not key or len(key) < 10):
            # Extract host from URL (http://1.2.3.4:8000 -> 1.2.3.4)
            try:
                ip = url.split("//")[1].split(":")[0]
                # Default to root@ip if not stored
                origin_ssh = remote.get("ssh_host", f"root@{ip}")
                
                print(f"{BLUE}[Auto-Auth] Fetching key from {origin_ssh}...{RESET}")
                cmd = f"ssh -o StrictHostKeyChecking=no {origin_ssh} \"cat api_key.txt\""
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if res.returncode == 0:
                    new_key = res.stdout.strip()
                    if len(new_key) > 10:
                        self.config.data.setdefault("remote", {})["key"] = new_key
                        self.config.save()
                        print(f"{BLUE}[Success] Key secured.{RESET}")
                        return new_key
                else:
                    print(f"{PINK}[Auth Fail] Could not fetch key: {res.stderr.strip()}{RESET}")
            except Exception as e:
                print(f"{PINK}[Auth Error] Could not auto-fetch key: {e}{RESET}")
        return key

    def chat_remote(self, messages: list, url: str = None) -> str:
        """Chat via remote API with full message history."""
        # Auto-auth before chatting
        self._ensure_remote_key()
        
        url = url or self.config.get("remote.url", "http://187.77.208.28:8125")
        key = self.config.get("remote.key")
        
        data = json.dumps({
            "model": "freeli",
            "messages": messages,
            "max_tokens": self.config.get("inference.max_tokens", 4096),
            "temperature": self.config.get("inference.temperature", 0.7)
        }).encode('utf-8')
        
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        
        req = urllib.request.Request(
            f"{url}/v1/chat/completions",
            data=data,
            headers=headers
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                msg = result.get("choices", [{}])[0].get("message", {})
                content = msg.get("content", "")
                reasoning = msg.get("reasoning_content", "")
                if reasoning and not content:
                    return reasoning
                return content or str(result)
        except Exception as e:
            return f"[ERROR] {e}"
    
    def chat_local(self, messages: list) -> str:
        """Chat via local llama-cli with full history."""
        model = self.get_model()
        if not model:
            return "[ERROR] No model found"
        
        # Construct prompt from messages
        prompt = ""
        for m in messages:
            role = m["role"]
            content = m["content"]
            if role == "system":
                prompt += f"{content}\n\n"
            elif role == "user":
                prompt += f"User: {content}\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n"
        prompt += "Assistant:"
        
        cmd = [
            str(LLAMA_CLI), "-m", model,
            "-c", str(self.config.get("model.context_length", 4096)),
            "-t", str(self.config.get("model.threads", 4)),
            "-n", str(self.config.get("inference.max_tokens", 2048)),
            "-p", prompt, "--no-display-prompt"
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.stdout.strip() or result.stderr
        except Exception as e:
            return f"[ERROR] {e}"

    
    def agent_chat(self, user_input: str, use_remote: bool = True) -> str:
        """Chat with autonomous tool execution loop (Max 5 turns)."""
        system = self._get_system_prompt()
        messages = [{"role": "system", "content": system}]
        
        # Handle simple history (TODO: full session history)
        messages.append({"role": "user", "content": user_input})
        
        final_response = ""
        PINK = "\033[95m"
        BLUE = "\033[96m"
        YELLOW = "\033[93m"
        RESET = "\033[0m"

        for turn in range(5): # Max 5 turns to prevent infinite loops
            # 1. Get Model Response
            if use_remote:
                response = self.chat_remote(messages)
            else:
                response = self.chat_local(messages)
            
            # 2. Parse Tools
            tool_calls = self.parse_tool_calls(response)
            
            if not tool_calls:
                final_response = response
                return final_response # Done
            
            # 3. Execute Tools
            messages.append({"role": "assistant", "content": response})
            print(f"{BLUE}{response}{RESET}") # Stream thoughts/calls
            
            tool_outputs = []
            for name, content in tool_calls:
                print(f"{YELLOW}  [EXEC] {name}...{RESET}")
                try:
                    result = self.execute_tool(name, content)
                    tool_outputs.append(f"<tool_result name=\"{name}\">\n{result}\n</tool_result>")
                except Exception as e:
                     tool_outputs.append(f"<tool_result name=\"{name}\">Error: {e}</tool_result>")
            
            # 4. Feed back to model
            tool_feedback = "\n".join(tool_outputs)
            messages.append({"role": "user", "content": f"Tool Outputs:\n{tool_feedback}\n\nContinue."})
        
        return f"{PINK}[STOPPED]{RESET} Max turns reached.\nLast Output: {response}"
    
    def serve(self):
        """Start local llama-server."""
        model = self.get_model()
        if not model:
            print("[freeli] ERROR: No model found")
            return
        
        port = self.config.get("api.port", 8125)
        host = self.config.get("api.host", "0.0.0.0")
        
        if is_port_open("localhost", port):
            print(f"[freeli] Port {port} already in use")
            return
        
        print(f"FREELI API SERVER\nModel: {model}\nAPI: http://{host}:{port}/v1/chat/completions")
        cmd = [str(LLAMA_SERVER), "-m", model, "-c", str(self.config.get("model.context_length", 4096)),
               "-t", str(self.config.get("model.threads", 4)), "--host", host, "--port", str(port)]
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print("\n[freeli] Stopped")

    
    def repl(self, use_remote: bool = True):
        """Interactive agent REPL."""
        model = self.get_model()
        remote_url = self.config.get("remote.url", "http://187.77.208.28:8000")
        
        # ANSI Colors
        PINK = "\033[95m"
        BLUE = "\033[96m"
        YELLOW = "\033[93m"
        RESET = "\033[0m"
        
        # ASCII Art (Fixed escapes)
        BANNER = f"""{BLUE}
      ,           {PINK}   _  _   {BLUE}   / \\__
    __)\\_         {PINK}  ( )( )  {BLUE}  (    @\\___
  (\\_.-'   {YELLOW}~~~~~{PINK}   |/|    {BLUE}  /         O
           {YELLOW}~~~~~{PINK}  ( )( )  {BLUE} /   (_____/
   {YELLOW}FREELI{RESET}       {PINK}   -  -   {BLUE}/_____/
   {YELLOW}Sovereign AI{RESET}
"""
        print(BANNER)
        
        mode_str = f"{BLUE}Remote: {remote_url}{RESET}" if use_remote else f"{YELLOW}Local: {Path(model).name if model else 'none'}{RESET}"
        print(f"{PINK}Tools:{RESET} code, files, edit, grep, web, sql, ask, artifact, screenshot")
        print(f"{PINK}Cmds:{RESET}  /spawn /addcmd /addtool /config /addorigin /addmem /ide /quit\n")
        print(f"{mode_str}\n")
        
        # Auto-Auth Check on Launch
        if use_remote:
             print(f"{BLUE}[Auto-Auth] Verifying connection to Sovereign Stack...{RESET}")
             try:
                 key = self._ensure_remote_key()
                 if key:
                     print(f"{BLUE}[OK] Secure Link Established.{RESET}")
                 else:
                     print(f"{PINK}[WARN] Could not fetch key automatically. Check SSH.{RESET}")
             except Exception as e:
                 print(f"{PINK}[ERROR] Connection check failed: {e}{RESET}")

        # Try importing prompt_toolkit for better TUI
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.history import FileHistory
            from prompt_toolkit.styles import Style as PtStyle
            from prompt_toolkit.formatted_text import HTML
            
            history_file = WORKSPACE / ".history"
            
            # Custom Style
            style = PtStyle.from_dict({
                'prompt': '#ff69b4 bold',       # Hot Pink
                'user': '#00bfff',              # Deep Sky Blue
                'toolbar': 'bg:#333333 #ffffff',
            })
            
            session = PromptSession(history=FileHistory(str(history_file)))
            
            while True:
                try:
                    # Bottom toolbar status
                    def get_toolbar():
                        return f" Mode: {'REMOTE' if use_remote else 'LOCAL'} | Url: {remote_url} "
                    
                    user = session.prompt(HTML('<prompt>[you]</prompt> <user>></user> '), style=style, bottom_toolbar=get_toolbar).strip()
                    
                    if not user: continue
                    if user in ["/quit", "exit"]: break
                    
                    # Handle Commands
                    if user.startswith("/"):
                        self.handle_command(user)
                        continue
                        
                    # Chat
                    print(f"{BLUE}[freeli] thinking...{RESET}")
                    print(self.agent_chat(user, use_remote))
                    
                except KeyboardInterrupt:
                    continue
                except EOFError:
                    break
        except ImportError:
            # Fallback to simple input
            print(f"{YELLOW}[WARN] prompt_toolkit not found. Using simple input.{RESET}")
            while True:
                try:
                    user = input(f"\n{PINK}[you]{BLUE} > {YELLOW}").strip()
                    print(RESET, end="")
                    
                    if not user: continue
                    if user == "/quit": break
                    
                    if user.startswith("/"):
                        self.handle_command(user)
                        continue

                    print(f"{BLUE}[freeli] thinking...{RESET}")
                    print(self.agent_chat(user, use_remote))
                    
                except KeyboardInterrupt:
                    print()
                    continue

    def handle_command(self, user: str):
        """Handle slash commands."""
        cmd = user.split()[0]
        PINK = "\033[95m"
        BLUE = "\033[96m"
        YELLOW = "\033[93m"
        RESET = "\033[0m"
        
        if cmd.startswith("/hostinger"):
            parts = user.split()
            token = parts[1] if len(parts) > 1 else ""
            
            # Auto-load from config if missing
            if not token:
                token = self.config.data.get("hostinger_token", "")
                
            if not token:
                token = input("Hostinger API Token > ").strip()
            
            if not token: return
            
            # Save for future
            if token != self.config.data.get("hostinger_token"):
                self.config.data["hostinger_token"] = token
                self.config.save()

            print(f"{BLUE}[Hostinger] Connecting to API...{RESET}")
            
            def h_req(endpoint, method="GET", data=None):
                url = f"https://developers.hostinger.com/api/vps/v1{endpoint}"
                req = urllib.request.Request(url, headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }, method=method)
                if data:
                    req.data = json.dumps(data).encode('utf-8')
                try:
                    with urllib.request.urlopen(req) as r:
                        return json.loads(r.read().decode())
                except urllib.error.HTTPError as e:
                    print(f"{PINK}[API Error] {e.code}: {e.read().decode()[:200]}{RESET}")
                    return None
                except Exception as e:
                    print(f"{PINK}[Error] {e}{RESET}")
                    return None

            # 1. List VPS
            print(f"{YELLOW}Fetching VPS instances...{RESET}")
            vps_list = h_req("/virtual-machines")
            
            # If standard endpoint fails, try /instances as fallback?
            # But we confirmed /virtual-machines worked with curl.
            if not vps_list or 'data' not in vps_list:
                # Try simple list if direct array?
                # The previous curl output started with `[{"id":...`
                # So it's a list, not a dict with 'data'.
                if isinstance(vps_list, list):
                    instances = vps_list
                else:
                    print(f"{PINK}No VPS instances found or API error.{RESET}")
                    return
            else:
                instances = vps_list['data']

            if not instances:
                print(f"{PINK}You have no VPS instances.{RESET}")
                return

            print(f"\n{BLUE}Available VPS:{RESET}")
            for i, vps in enumerate(instances):
                ip_list = vps.get('ipv4', [])
                ip = ip_list[0]['address'] if ip_list else 'Unknown'
                name = vps.get('hostname', 'Unnamed')
                status = vps.get('state', 'unknown')
                print(f"  [{i}] {name} ({ip}) - {status}")
            
            try:
                sel_input = input(f"\n{YELLOW}Select VPS [0-{len(instances)-1}] > {RESET}").strip()
                if not sel_input: return
                sel = int(sel_input)
                target = instances[sel]
                ip_list = target.get('ipv4', [])
                ip = ip_list[0]['address'] if ip_list else None
                vps_id = target.get('id')
            except:
                print("Invalid selection")
                return

            if not ip:
                print("Error: No IP found for VPS")
                return

            # 2. Try to Connect via SSH first (Fast Path)
            print(f"{YELLOW}Attempting direct SSH connection...{RESET}")
            try:
                # Try fetching key immediately
                ssh_cmd = f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@{ip} \"cat api_key.txt\""
                k_res = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
                
                if k_res.returncode == 0:
                    api_key = k_res.stdout.strip()
                    if len(api_key) > 10:
                        self.config.data.setdefault("remote", {})["url"] = f"http://{ip}:8000"
                        self.config.data.setdefault("remote", {})["ssh_host"] = f"root@{ip}"
                        self.config.data["remote"]["key"] = api_key
                        self.config.save()
                        print(f"{BLUE}[SUCCESS] Connected to {name}!{RESET}")
                        print(f"Origin: http://{ip}:8000")
                        return
            except Exception:
                pass

            print(f"{PINK}[Info] Direct SSH failed. Proceeding with key injection...{RESET}")

            # 3. Ensure Local SSH Key
            ssh_dir = Path.home() / ".ssh"
            pub_path = ssh_dir / "id_rsa.pub"
            if not pub_path.exists():
                print(f"{YELLOW}Generating local SSH key...{RESET}")
                ssh_dir.mkdir(mode=0o700, exist_ok=True)
                subprocess.run(["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", str(ssh_dir / "id_rsa"), "-N", ""], capture_output=True)
            
            pub_key = pub_path.read_text(encoding="utf-8").strip()

            # 4. Add Key to Hostinger (Global)
            print(f"{BLUE}Registering SSH key with Hostinger...{RESET}")
            key_name = f"freeli-auto-{int(time.time())}"
            # Try to register
            resp = h_req("/public-keys", "POST", {"name": key_name, "key": pub_key})
            
            key_id = None
            if resp and 'id' in resp: 
                 key_id = resp['id']
            elif resp and 'data' in resp and 'id' in resp['data']:
                 key_id = resp['data']['id']
            else:
                 # Check existing
                 print(f"{YELLOW}Checking existing keys...{RESET}")
                 keys = h_req("/public-keys")
                 # Check if list or dict
                 k_list = keys if isinstance(keys, list) else keys.get('data', [])
                 
                 # Clean local key (remove comment)
                 local_body = pub_key.split()[1]
                 
                 for k in k_list:
                     remote_body = k.get('key', '').split()
                     if len(remote_body) > 1 and remote_body[1] == local_body:
                         key_id = k['id']
                         print(f"{BLUE}Found existing matching key ({key_id}).{RESET}")
                         break
            
            if not key_id:
                print(f"{PINK}[Error] Could not register or find SSH key on Hostinger.{RESET}")
                # Don't return, try to proceed anyway just in case
            else:
                # 5. Attach Key to VPS
                print(f"{BLUE}Injecting key into VPS...{RESET}")
                # Try plain attach
                res = h_req(f"/virtual-machines/{vps_id}/public-keys", "POST", {"key_ids": [key_id]})
                if not res:
                     print(f"{YELLOW}[Warn] Key injection failed (API might be read-only). Continuing...{RESET}")

            # 6. Configure Freeli & Fetch Key
            print(f"{BLUE}Configuring Freeli...{RESET}")
            url = f"http://{ip}:8000"
            self.config.data.setdefault("remote", {})["url"] = url
            self.config.data.setdefault("remote", {})["ssh_host"] = f"root@{ip}"
            
            # Fetch API Key
            print(f"{YELLOW}Fetching Sovereign API Key via SSH...{RESET}")
            try:
                # We need to wait a moment for key propagation if it was just added?
                # Usually fast.
                ssh_cmd = f"ssh -o StrictHostKeyChecking=no root@{ip} \"cat api_key.txt\""
                k_res = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
                
                if k_res.returncode == 0:
                    api_key = k_res.stdout.strip()
                    if len(api_key) > 10:
                        self.config.data["remote"]["key"] = api_key
                        print(f"{BLUE}[SUCCESS] API Key retrieved!{RESET}")
                    else:
                        print(f"{PINK}[WARN] Key file found but empty/invalid.{RESET}")
                else:
                    print(f"{PINK}[WARN] Could not fetch api_key.txt via SSH.{RESET}")
                    print(f"Error: {k_res.stderr}")
            except Exception as e:
                print(f"{PINK}[Error] SSH fetch failed: {e}{RESET}")

            self.config.save()
            print(f"\n{BLUE}[DONE] Connected to {name}!{RESET}")
            print(f"Origin: {url}")

        elif cmd == "/config":
            print(json.dumps(self.config.data, indent=2))
            
        elif cmd.startswith("/addorigin"):
            parts = user.split()
            origin_input = parts[1] if len(parts) > 1 else ""
            if not origin_input:
                origin_input = input(f"Sovereign Origin (e.g. root@1.2.3.4) > ").strip()
            
            if origin_input:
                # 1. Save host to SSH helper
                self.config.data.setdefault("remote", {})["ssh_host"] = origin_input
                
                # 2. Derive URL
                try:
                    ip = origin_input.split("@")[-1] if "@" in origin_input else origin_input
                    url = f"http://{ip}:8000"
                    self.config.data.setdefault("remote", {})["url"] = url
                    self.config.save()
                    print(f"{BLUE}[OK] Origin saved: {url}{RESET}")
                    print(f"{YELLOW}(Will auto-auth on first message){RESET}")
                except Exception as e:
                    print(f"[ERROR] Invalid origin format: {e}")

        elif cmd == "/rotatekey":
            remote = self.config.data.get("remote", {}).get("url", "")
            if not remote:
                 print(f"{PINK}[ERROR]{RESET} No remote origin configured.")
                 return
                 
            host_ip = remote.split("//")[1].split(":")[0]
            origin = f"root@{host_ip}" # Assumption: running as root
            
            print(f"{YELLOW}Rotating Sovereign Key on {origin}...{RESET}")
            
            try:
                # 1. SSH command to kill wrapper, delete key, restart wrapper
                remote_cmd = (
                    "pkill -f gguf_wrapper.py; "
                    "rm -f api_key.txt; "
                    "screen -dmS freeli_wrapper bash -c 'while true; do python3 gguf_wrapper.py >> wrapper.log 2>&1; sleep 5; done'"
                )
                subprocess.run(f"ssh {origin} \"{remote_cmd}\"", shell=True)
                
                # 2. Wait for regeneration
                print(f"{BLUE}Waiting for key regeneration...{RESET}")
                time.sleep(5)
                
                # 3. Fetch new key
                res = subprocess.run(f"ssh {origin} \"cat api_key.txt\"", shell=True, capture_output=True, text=True)
                new_key = res.stdout.strip()
                
                if len(new_key) > 10:
                    self.config.data["remote"]["key"] = new_key
                    self.config.save()
                    print(f"{BLUE}[SUCCESS]{RESET} Key rotated!")
                    print(f"{PINK}New Key:{RESET} {new_key[:8]}...{new_key[-8:]}")
                else:
                    print(f"{PINK}[ERROR]{RESET} Failed to fetch new key.")
                    
            except Exception as e:
                 print(f"{PINK}[ERROR]{RESET} Rotation failed: {e}")
            
        elif cmd == "/addmem":
            mem = input("Memory > ").strip()
            if mem:
                (WORKSPACE / "memory.txt").write_text(mem + "\n", encoding="utf-8")
                print("[OK] Memory saved")
                
        elif cmd == "/addkey":
             print("[WARN] Deprecated. Use /addorigin or edit config directly.")

        elif cmd == "/spawn":
            print("\n[FREELI SPAWN] Provision Remote Inference Server")
            host = input("SSH Host (e.g. root@1.2.3.4) > ").strip()
            if host:
                print(f"[freeli] Provisioning {host}...")
                script_content = """#!/bin/bash
set -e
echo "--- Updating System ---"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -y -qq build-essential git cmake wget screen python3-pip curl

echo "--- Installing Python Libs ---"
pip3 install httpx uvicorn fastapi --break-system-packages

echo "--- Setting up Llama.cpp (CMake) ---"
if [ ! -d "llama.cpp" ]; then
    git clone https://github.com/ggerganov/llama.cpp
    cd llama.cpp
    cmake -B build -DGGML_NATIVE=OFF
    cmake --build build --config Release -j$(nproc)
    cd ..
fi

echo "--- Downloading Model (Phi-2) ---"
mkdir -p models
if [ ! -f "models/phi-2.Q4_K_M.gguf" ]; then
    wget -q --show-progress -O models/phi-2.Q4_K_M.gguf https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf
fi

echo "--- Starting Server ---"
pkill -f llama-server || true
screen -dmS freeli ./llama.cpp/build/bin/llama-server -m models/phi-2.Q4_K_M.gguf -c 2048 --host 0.0.0.0 --port 8125

echo "SUCCESS: Server running on port 8125"
"""
                try:
                    prov_path = WORKSPACE / "provision.sh"
                    prov_path.write_text(script_content, encoding='utf-8')
                    tgt = f"{host}:/tmp/provision_freeli.sh"
                    print(f"• Uploading script to {tgt}...")
                    subprocess.run(["scp", str(prov_path), tgt], check=True)
                    print(f"• Executing on {host}...")
                    subprocess.run(["ssh", host, "chmod +x /tmp/provision_freeli.sh && /tmp/provision_freeli.sh"], check=True)
                    ip = host.split("@")[1] if "@" in host else host
                    new_url = f"http://{ip}:8125"
                    print(f"\n[OK] Remote server provisioned at {new_url}")
                    if input("Set as current origin? (y/n) > ").lower().startswith("y"):
                        self.config.data.setdefault("remote", {})["url"] = new_url
                        self.config.save()
                        print("[OK] Origin updated")
                except Exception as e:
                    print(f"[ERROR] Spawn failed: {e}")

        elif cmd == "/addcmd":
            print("\n[FREELI MAKER] Create a new CLI command")
            name = input("Name > ").strip()
            if name:
                desc = input("Describe what it does > ").strip()
                if desc:
                    print(f"[freeli] Generating command '{name}'...")
                    prompt = f"Write a Python script to: {desc}\nRequirements:\n- Self-contained\n- Prints to stdout\nOutput ONLY the code inside ```python blocks."
                    resp = self.agent_chat(prompt, True)
                    code = ""
                    if "```python" in resp: code = resp.split("```python")[1].split("```")[0].strip()
                    elif "```" in resp: code = resp.split("```")[1].split("```")[0].strip()
                    else: code = resp.strip()
                    
                    if code:
                        script_path = BIN_DIR / f"{name}.py"
                        cmd_path = BIN_DIR / f"{name}.cmd"
                        script_path.write_text(code, encoding='utf-8')
                        cmd_path.write_text(f'@python "{script_path}" %*', encoding='utf-8')
                        print(f"[OK] Command created: {name}")
                    else:
                        print("[ERROR] Failed to generate code")

        elif cmd == "/addtool":
             print("\n[FREELI MAKER] Create a new Agent Tool")
             name = input("Tool Name > ").strip()
             if name:
                 desc = input("Describe functionality > ").strip()
                 if desc:
                     print(f"[freeli] Implementing tool '{name}'...")
                     prompt = f"Write a Python method for the 'Tools' class to: {desc}\nSignature: @staticmethod def {name}(args: str) -> str:\nOutput ONLY python code inside ```python blocks."
                     resp = self.agent_chat(prompt, True)
                     code = ""
                     if "```python" in resp: code = resp.split("```python")[1].split("```")[0].strip()
                     elif "```" in resp: code = resp.split("```")[1].split("```")[0].strip()
                     else: code = resp
                     
                     if code:
                         my_path = Path(__file__)
                         c = my_path.read_text(encoding='utf-8')
                         if "class Config:" in c:
                             parts = c.split("class Config:")
                             indented = "\n    " + code.replace("\n", "\n    ") + "\n\n"
                             new_c = parts[0] + indented + "class Config:" + parts[1]
                             if 'AGENT_SYSTEM_PROMPT = """' in new_c:
                                 tool_def = f'\n<tool name="{name}">{desc}</tool>\n'
                                 new_c = new_c.replace('AGENT_SYSTEM_PROMPT = """', 'AGENT_SYSTEM_PROMPT = """' + tool_def)
                             my_path.write_text(new_c, encoding='utf-8')
                             print(f"[OK] Tool '{name}' added! Restart Freeli.")
                             sys.exit(0)
                         else: print("[ERROR] Could not insert tool")
                     else: print("[ERROR] Failed to generate tool code")

        elif cmd == "/load":
            parts = user.split()
            if len(parts) < 2:
                print("Usage: /load <path/to/model.gguf> or /load <index>")
                models = find_models()
                for i, m in enumerate(models):
                    print(f"  [{i}] {m.name}")
                return

            arg = parts[1]
            try:
                idx = int(arg)
                models = find_models()
                if 0 <= idx < len(models):
                    new_model = str(models[idx])
                    if not isinstance(self.config.data.get("model"), dict):
                        self.config.data["model"] = {}
                    self.config.data["model"]["path"] = new_model
                    self.config.save()
                    print(f"[OK] Loaded model: {Path(new_model).name}")
                else:
                    print(f"[ERROR] Invalid index. Max is {len(models)-1}")
            except ValueError:
                p = Path(arg)
                if p.exists():
                    if not isinstance(self.config.data.get("model"), dict):
                        self.config.data["model"] = {}
                    self.config.data["model"]["path"] = str(p)
                    self.config.save()
                    print(f"[OK] Loaded model: {p.name}")
                else:
                    print(f"[ERROR] File not found: {arg}")

        elif cmd == "/models":
            models = find_models()
            for i, m in enumerate(models): 
                print(f"  [{i}] {m}")

        elif cmd == "/ide":
            print("\n[FREELI IDE] Starting FreeAide Server...")
            print("Open http://127.0.0.1:9999")
            try:
                subprocess.run([sys.executable, str(FREELI_HOME / "ide" / "main.py")], cwd=str(FREELI_HOME / "ide"))
            except KeyboardInterrupt: print("\nStopped")

        elif cmd == "/serve":
            self.serve()

        elif cmd == "/remote":
             print("[INFO] Switched to remote mode (effective next turn)")
        
        elif cmd == "/local":
             print("[INFO] Switched to local mode (effective next turn)")
             
        else:
            print(f"Unknown command: {cmd}")



def main():
    p = argparse.ArgumentParser(description="Freeli - Sovereign AI Agent")
    p.add_argument("cmd", nargs="?", default="repl", choices=["repl", "serve", "chat", "config", "models", "ide", "hostinger"])
    p.add_argument("-m", "--message")
    p.add_argument("-r", "--remote", action="store_true", default=True)
    p.add_argument("-l", "--local", action="store_true")
    p.add_argument("--ide", action="store_true", help="Launch FreeAide immediately")
    p.add_argument("--port", type=int)
    p.add_argument("hostinger_token", nargs="?", help="API token for /hostinger command") # Add optional token arg
    args = p.parse_args()
    
    f = Freeli()
    
    if args.port:
        f.config.data.setdefault("api", {})["port"] = args.port
    
    use_remote = not args.local
    
    # Handle --ide flag
    if args.ide or args.cmd == "ide":
        print("\n[FREELI IDE] Starting FreeAide Server...")
        print("Open http://127.0.0.1:9999 in your browser")
        try:
            subprocess.run(
                [sys.executable, str(FREELI_HOME / "ide" / "main.py")],
                cwd=str(FREELI_HOME / "ide")
            )
        except KeyboardInterrupt:
            print("\n[FREELI IDE] Stopped")
        return

    if args.cmd == "hostinger":
        token = args.hostinger_token or f.config.data.get("hostinger_token", "")
        if token:
            f.handle_command(f"/hostinger {token}")
        else:
            print("Token required. Pass it as arg or set in config.")
            return
            
    elif args.cmd == "serve":
        f.serve()
    elif args.cmd == "config":
        print(json.dumps(f.config.data, indent=2))
    elif args.cmd == "models":
        for m in find_models(): print(f"  • {m}")
    elif args.cmd == "chat":
        if args.message:
            print(f.agent_chat(args.message, use_remote))
        else:
            print("Need -m MESSAGE")
    else:
        f.repl(use_remote)


if __name__ == "__main__":
    main()
