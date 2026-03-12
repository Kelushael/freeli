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
    for path in [MODELS_DIR, FREELI_HOME / "models", Path.home() / "Downloads"]:
        if path.exists():
            models.extend(path.glob("*.gguf"))
    return sorted(models, key=lambda x: x.stat().st_size, reverse=True)

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
        base = self.config.get("system_prompt", AGENT_SYSTEM_PROMPT)
        mem_path = WORKSPACE / "memory.txt"
        if mem_path.exists():
            mem = mem_path.read_text(encoding="utf-8").strip()
            if mem:
                base += f"\n\n--- MEMORY ---\n{mem}"
        return base

    def chat_remote(self, message: str, url: str = None) -> str:
        """Chat via remote API."""
        url = url or self.config.get("remote.url", "http://187.77.208.28:8125")
        key = self.config.get("remote.key")
        
        system = self._get_system_prompt()
        
        data = json.dumps({
            "model": "freeli",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": message}
            ],
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
                # Handle different response formats
                msg = result.get("choices", [{}])[0].get("message", {})
                content = msg.get("content", "")
                reasoning = msg.get("reasoning_content", "")
                if reasoning and not content:
                    return reasoning
                return content or str(result)
        except Exception as e:
            return f"[ERROR] {e}"
    
    def chat_local(self, message: str) -> str:
        """Chat via local llama-cli."""
        model = self.get_model()
        if not model:
            return "[ERROR] No model found"
        
        system = self._get_system_prompt()
        prompt = f"{system}\n\nUser: {message}\nAssistant:"
        
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

    
    def agent_chat(self, message: str, use_remote: bool = True) -> str:
        """Chat with tool execution loop."""
        # Get response
        if use_remote:
            response = self.chat_remote(message)
        else:
            response = self.chat_local(message)
        
        # Parse and execute any tool calls
        tool_calls = self.parse_tool_calls(response)
        if tool_calls:
            tool_outputs = []
            for name, content in tool_calls:
                print(f"  [TOOL] {name}...")
                result = self.execute_tool(name, content)
                tool_outputs.append(f"[{name}]: {result}")
            
            # Append tool results to response
            response += "\n\n--- Tool Results ---\n" + "\n".join(tool_outputs)
        
        return response
    
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
        remote = self.config.get("remote.url", "http://187.77.208.28:8125")
        
        # THEME: Pink, Baby Blue, Yellow, Black
        PINK = "\033[95m"
        BLUE = "\033[96m"
        YELLOW = "\033[93m"
        RESET = "\033[0m"
        BOLD = "\033[1m"
        
        BANNER = f"""{{BLUE}}
      ,           {{PINK}}   _  _   {{BLUE}}   / \\__
    __)\\_         {{PINK}}  ( )( )  {{BLUE}}  (    @\\___
  (\\_.-'   {{YELLOW}}~~~~~{{PINK}}   |/|    {{BLUE}}  /         O
           {{YELLOW}}~~~~~{{PINK}}  ( )( )  {{BLUE}} /   (_____/
   {{YELLOW}}FREELI{{RESET}}       {{PINK}}   -  -   {{BLUE}}/_____/
   {{YELLOW}}Sovereign AI{{RESET}}
"""
        print(BANNER)
        
        mode = f"{BLUE}Remote: {remote}{RESET}" if use_remote else f"{YELLOW}Local: {Path(model).name if model else 'none'}{RESET}"
        print(f"{PINK}Tools:{RESET} code, files, edit, grep, web, sql, ask, artifact, screenshot")
        print(f"{PINK}Cmds:{RESET}  /spawn /addcmd /addtool /config /addorigin /addmem /ide /quit\n")
        print(f"{mode}\n")
        
        while True:
            try:
                # Custom colorful prompt
                user = input(f"\n{PINK}[you]{BLUE} > {YELLOW}").strip()
                print(RESET, end="") # Reset after input
                
                if not user: continue
                if user == "/quit": break
                
                if user == "/config":
                    print(json.dumps(self.config.data, indent=2))
                    continue
                
                if user.startswith("/addorigin"):
                    parts = user.split()
                    origin_input = parts[1] if len(parts) > 1 else ""
                    
                    if not origin_input:
                        print(f"\n{PINK}[FREELI CONFIG]{RESET} Setup Sovereign Origin")
                        origin_input = input(f"{BLUE}SSH Host (e.g. root@1.2.3.4) > {YELLOW}").strip()
                    
                    if origin_input:
                        print(f"\n{YELLOW}Bootstrapping sovereign connection to {origin_input}...{RESET}")
                        
                        # 1. SSH to get the key
                        try:
                            # Use ssh to cat the key file
                            cmd = f"ssh -o StrictHostKeyChecking=no {origin_input} \"cat api_key.txt\""
                            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                            
                            if result.returncode != 0:
                                print(f"{PINK}[ERROR]{RESET} SSH handshake failed.")
                                print(f"{PINK}Details:{RESET} {result.stderr.strip()}")
                                continue
                                
                            remote_key = result.stdout.strip()
                            # Check for valid key length (approx 64 chars)
                            if len(remote_key) < 10: 
                                print(f"{PINK}[ERROR]{RESET} Invalid key retrieved: '{remote_key}'")
                                continue
                                
                            # 2. Extract IP for HTTP URL
                            if "@" in origin_input:
                                host_ip = origin_input.split("@")[1]
                            else:
                                host_ip = origin_input
                                
                            remote_url = f"http://{host_ip}:8000/v1"
                            
                            # 3. Update config
                            self.config.data.setdefault("remote", {})["url"] = remote_url
                            self.config.data.setdefault("remote", {})["key"] = remote_key
                            self.config.save()
                            
                            print(f"{BLUE}[SUCCESS]{RESET} Sovereign link established!")
                            print(f"{PINK}Remote:{RESET} {remote_url}")
                            print(f"{PINK}Key:{RESET}    {remote_key[:8]}...{remote_key[-8:]} (securely saved)")
                            
                        except Exception as e:
                            print(f"{PINK}[ERROR]{RESET} Bootstrap failed: {e}")
                    continue

                if user == "/addkey":
                    print("\n[FREELI CONFIG] Add Remote Server Key")
                    alias = input("Server Alias (e.g. origin, gpu1) > ").strip()
                    if alias:
                        url = input("Server URL (e.g. http://1.2.3.4:8000) > ").strip()
                        key = input("API Key > ").strip()
                        
                        if 'servers' not in self.config.data:
                            self.config.data['servers'] = {}
                        
                        self.config.data['servers'][alias] = {"url": url, "key": key}
                        
                        # If origin, update main remote
                        if alias == "origin":
                            self.config.data.setdefault("remote", {})["url"] = url
                            self.config.data.setdefault("remote", {})["key"] = key
                            
                        self.config.save()
                        print(f"[OK] Saved server '{alias}'")
                    continue
                
                if user == "/rotatekey":
                    remote = self.config.data.get("remote", {}).get("url", "")
                    if not remote:
                         print(f"{PINK}[ERROR]{RESET} No remote origin configured.")
                         continue
                         
                    host_ip = remote.split("//")[1].split(":")[0]
                    origin = f"root@{host_ip}" # Assumption: running as root
                    
                    print(f"{YELLOW}Rotating Sovereign Key on {origin}...{RESET}")
                    
                    try:
                        # 1. SSH command to kill wrapper, delete key, restart wrapper
                        remote_cmd = (
                            "pkill -f gguf_wrapper.py; "
                            "rm -f api_key.txt; "
                            "screen -dmS freeli_wrapper bash -c 'python3 gguf_wrapper.py > wrapper.log 2>&1'"
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
                    continue

                if user == "/addmem":
                    print("\n[FREELI MEMORY] Add Persistent Context")
                    mem = input("Memory to save > ").strip()
                    if mem:
                        mem_path = WORKSPACE / "memory.txt"
                        mode = "a" if mem_path.exists() else "w"
                        with open(mem_path, mode, encoding="utf-8") as f:
                            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {mem}\n")
                        print(f"[OK] Memory saved to {mem_path}")
                    continue

                if user == "/spawn":
                    print("\n[FREELI SPAWN] Provision Remote Inference Server")
                    host = input("SSH Host (e.g. root@1.2.3.4) > ").strip()
                    if not host: continue
                    
                    print(f"[freeli] Provisioning {host}...")
                    
                    # Create provision script
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

                    echo "--- Setting up Wrapper ---"
                    # Download wrapper or create it (simplified version for spawn)
                    # For now, we assume user will SCP their enhanced wrapper or we can embed a simple one.
                    # Let's just launch llama-server directly for basic spawn, 
                    # OR we can try to replicate the wrapper. 
                    # Given the complexity, let's stick to the raw server for the basic /spawn command 
                    # unless we want to embed the whole wrapper script in this f-string.
                    
                    echo "--- Starting Server ---"
                    # Kill existing
                    pkill -f llama-server || true
                    
                    # Run in screen
                    screen -dmS freeli ./llama.cpp/build/bin/llama-server -m models/phi-2.Q4_K_M.gguf -c 2048 --host 0.0.0.0 --port 8125
                    
                    echo "SUCCESS: Server running on port 8125"
                    """
                    
                    try:
                        # Write local temp script
                        prov_path = WORKSPACE / "provision.sh"
                        prov_path.write_text(script_content, encoding='utf-8')
                        
                        # SCP script
                        tgt = f"{host}:/tmp/provision_freeli.sh"
                        print(f"• Uploading script to {tgt}...")
                        subprocess.run(["scp", str(prov_path), tgt], check=True)
                        
                        # Execute SSH
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
                        print("Ensure you have SSH keys set up and 'scp' available.")
                    continue

                if user == "/adjustconfig":
                    print("\n[FREELI CONFIG] Adjust Configuration")
                    print(f"Current Config: {json.dumps(self.config.data, indent=2)}")
                    key = input("Key (e.g. inference.temperature) > ").strip()
                    if key:
                        val = input(f"Value for '{key}' > ").strip()
                        # Try to parse as json/number/bool
                        try: val = json.loads(val)
                        except: pass
                        
                        # Set nested key
                        keys = key.split('.')
                        curr = self.config.data
                        for k in keys[:-1]:
                            curr = curr.setdefault(k, {})
                        curr[keys[-1]] = val
                        
                        self.config.save()
                        print(f"[OK] Set {key} = {val}")
                    continue

                if user == "/addcmd":
                    print("\n[FREELI MAKER] Create a new CLI command")
                    name = input("Name > ").strip()
                    if not name: continue
                    desc = input("Describe what it does > ").strip()
                    if not desc: continue
                    
                    print(f"[freeli] Generating command '{name}'...")
                    prompt = f"""Write a Python script to: {desc}
                    Requirements:
                    - Self-contained
                    - Uses standard libraries or requests/BeautifulSoup
                    - Prints output to stdout
                    
                    Output ONLY the code inside ```python blocks."""
                    
                    # Generate code
                    resp = self.agent_chat(prompt, use_remote)
                    
                    # Extract code
                    code = ""
                    if "```python" in resp:
                        code = resp.split("```python")[1].split("```")[0].strip()
                    elif "```" in resp:
                        code = resp.split("```")[1].split("```")[0].strip()
                    else:
                        code = resp.strip()
                        
                    if code:
                        # Save to bin
                        script_path = BIN_DIR / f"{name}.py"
                        cmd_path = BIN_DIR / f"{name}.cmd"
                        
                        script_path.write_text(code, encoding='utf-8')
                        cmd_path.write_text(f'@python "{script_path}" %*', encoding='utf-8')
                        
                        print(f"[OK] Command created: {name}")
                        print(f"Run it with: {name}")
                    else:
                        print("[ERROR] Failed to generate code")
                    continue

                if user == "/addtool":
                    print("\n[FREELI MAKER] Create a new Agent Tool")
                    name = input("Tool Name > ").strip()
                    if not name: continue
                    desc = input("Describe functionality > ").strip()
                    if not desc: continue
                    
                    print(f"[freeli] Implementing tool '{name}'...")
                    prompt = f"""Write a Python method for the 'Tools' class to: {desc}
                    Method signature: @staticmethod def {name}(args: str) -> str:
                    
                    Requirements:
                    - Error handling (try/except) returning string error
                    - Return string output
                    - Use type hinting
                    
                    Output ONLY the python code for the method inside ```python blocks."""
                    
                    resp = self.agent_chat(prompt, use_remote)
                    
                    code = ""
                    if "```python" in resp:
                        code = resp.split("```python")[1].split("```")[0].strip()
                    elif "```" in resp:
                        code = resp.split("```")[1].split("```")[0].strip()
                    else:
                        code = resp
                    
                    if code:
                        # Append to this file!
                        my_path = Path(__file__)
                        content = my_path.read_text(encoding='utf-8')
                        
                        # Find end of Tools class
                        # We'll look for "class Config:" as the marker after Tools
                        if "class Config:" in content:
                            parts = content.split("class Config:")
                            
                            # Indent the code
                            indented_code = "\n    " + code.replace("\n", "\n    ") + "\n\n"
                            
                            new_content = parts[0] + indented_code + "class Config:" + parts[1]
                            
                            # Also need to update System Prompt to include this tool
                            if 'AGENT_SYSTEM_PROMPT = """' in new_content:
                                tool_def = f'\n<tool name="{name}">{desc}</tool>\n'
                                new_content = new_content.replace('AGENT_SYSTEM_PROMPT = """', 'AGENT_SYSTEM_PROMPT = """' + tool_def)
                            
                            my_path.write_text(new_content, encoding='utf-8')
                            print(f"[OK] Tool '{name}' added! Please restart Freeli to use it.")
                            break # Exit to restart
                        else:
                            print("[ERROR] Could not find insertion point in source code")
                    else:
                        print("[ERROR] Failed to generate tool code")
                    continue

                if user == "/models":
                    for m in find_models(): print(f"  • {m}")
                    continue
                if user == "/ide":
                    print("\n[FREELI IDE] Starting FreeAide Server...")
                    print("Open http://127.0.0.1:9999 in your browser")
                    try:
                        subprocess.run(
                            [sys.executable, str(FREELI_HOME / "ide" / "main.py")],
                            cwd=str(FREELI_HOME / "ide")
                        )
                    except KeyboardInterrupt:
                        print("\n[FREELI IDE] Stopped")
                    continue
                if user == "/serve":
                    self.serve()
                    continue
                if user == "/remote":
                    use_remote = True
                    print(f"[freeli] Remote mode: {remote}")
                    continue
                if user == "/local":
                    use_remote = False
                    print("[freeli] Local mode")
                    continue
                
                print("\n[freeli] thinking...")
                resp = self.agent_chat(user, use_remote)
                print(f"\n[freeli] {resp}")
            except KeyboardInterrupt:
                print("\n/quit to exit")
            except EOFError:
                break



def main():
    p = argparse.ArgumentParser(description="Freeli - Sovereign AI Agent")
    p.add_argument("cmd", nargs="?", default="repl", choices=["repl", "serve", "chat", "config", "models", "ide"])
    p.add_argument("-m", "--message")
    p.add_argument("-r", "--remote", action="store_true", default=True)
    p.add_argument("-l", "--local", action="store_true")
    p.add_argument("--ide", action="store_true", help="Launch FreeAide immediately")
    p.add_argument("--port", type=int)
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

    if args.cmd == "serve":
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
