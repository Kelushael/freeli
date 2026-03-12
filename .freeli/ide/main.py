import os
import sys
import json
import subprocess
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import urllib.request
import urllib.error

# Configuration
IDE_PORT = 9999
ROOT_DIR = Path.cwd()

app = FastAPI(title="FreeAide Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class FileWrite(BaseModel):
    path: str
    content: str

class CommandRequest(BaseModel):
    cmd: str

class ChatMessage(BaseModel):
    message: str
    model_url: str = "http://187.77.208.28:8000"
    api_key: str = "ocHphHIRM2BHNivGt0F34qtc2RcFq18Z7tkF1bWmQ75wQyY1abUlfxCKzXAveUJv"

@app.get("/api/files")
def list_files(path: str = "."):
    try:
        p = (ROOT_DIR / path).resolve()
        items = []
        if p.exists() and p.is_dir():
            for entry in os.scandir(p):
                items.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "path": str(Path(path) / entry.name).replace("\\", "/")
                })
        return sorted(items, key=lambda x: (not x["is_dir"], x["name"]))
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/file")
def read_file(path: str):
    try:
        p = (ROOT_DIR / path).resolve()
        if not p.exists(): return {"content": ""}
        return {"content": p.read_text(encoding="utf-8", errors="ignore")}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/file")
def write_file_content(data: FileWrite):
    try:
        p = (ROOT_DIR / data.path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data.content, encoding="utf-8")
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/exec")
def execute_command(data: CommandRequest):
    try:
        result = subprocess.run(
            data.cmd, shell=True, capture_output=True, text=True, cwd=str(ROOT_DIR)
        )
        return {"stdout": result.stdout, "stderr": result.stderr}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/chat")
def chat_agent(data: ChatMessage):
    try:
        payload = {
            "model": "freeli-ide",
            "messages": [
                {"role": "system", "content": "You are FreeAide, the AI assistant for coding. Help the user write code."},
                {"role": "user", "content": data.message}
            ],
            "max_tokens": 4096,
            "temperature": 0.7
        }
        
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{data.model_url}/v1/chat/completions",
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {data.api_key}"
            }
        )
        
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            content = res["choices"][0]["message"]["content"]
            return {"response": content}
            
    except Exception as e:
        return {"response": f"Error contacting remote server: {e}"}

# Serve Static Files
static_dir = Path(__file__).parent / "static"
if not static_dir.exists(): static_dir.mkdir()

app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=IDE_PORT)

