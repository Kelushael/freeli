import http.server
import socketserver
import urllib.request
import urllib.error
import json
import os
import sys
from pathlib import Path

# Config
PORT = 8888
REMOTE_URL = "http://187.77.208.28:8000/v1/chat/completions"
# Try to find API key
CONFIG_PATH = Path.home() / ".freeli" / "config" / "config.json"
API_KEY = ""
try:
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text())
        API_KEY = data.get("remote", {}).get("key", "")
except: pass

ARTIFACTS_DIR = Path.home() / ".freeli" / "artifacts"
HTML_FILE = ARTIFACTS_DIR / "matrix_chat.html"

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_FILE.read_bytes())
        else:
            # Serve other artifacts if needed
            super().do_GET()

    def do_POST(self):
        if self.path == "/chat":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                # Forward to Remote
                req = urllib.request.Request(
                    REMOTE_URL,
                    data=post_data,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {API_KEY}"
                    }
                )
                
                with urllib.request.urlopen(req, timeout=300) as resp:
                    response_data = resp.read()
                    
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(response_data)
                    
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

os.chdir(ARTIFACTS_DIR)
print(f"Sovereign Dashboard running at http://localhost:{PORT}")
print(f"Proxying to {REMOTE_URL}")

with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
