import os
import sys
import subprocess
import time
import logging
import secrets
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel
import httpx
import uvicorn

# Configuration
WRAPPER_PORT = 8000
LLAMA_PORT = 8080
LLAMA_HOST = "127.0.0.1"
API_KEY_FILE = "api_key.txt"
LLAMA_BIN = os.path.abspath("llama.cpp/build/bin/llama-server")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gguf-wrapper")

# Auth
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

def get_api_key():
    if os.path.exists(API_KEY_FILE):
        return open(API_KEY_FILE).read().strip()
    
    # Hardened Alphanumeric Key (64 chars)
    import string
    alphabet = string.ascii_letters + string.digits
    key = ''.join(secrets.choice(alphabet) for i in range(64))
    
    with open(API_KEY_FILE, "w") as f:
        f.write(key)
    return key

SERVER_API_KEY = get_api_key()
print(f"\n🔑 SERVER API KEY: {SERVER_API_KEY}\n")

async def verify_api_key(key: str = Security(api_key_header)):
    if not key:
         # Try query param for ease of use in browser/curl
         pass 
    
    # Simple check
    # In production, check Authorization: Bearer <key>
    # Here we just check if the string matches
    if key == SERVER_API_KEY:
        return key
    
    # If using Bearer scheme
    # if key and key.startswith("Bearer "): ...
    
    raise HTTPException(status_code=403, detail="Invalid API Key")

app = FastAPI(title="Freeli GGUF Cloud Loader")

# State
class ServerState:
    process = None
    current_model = None

state = ServerState()

@app.on_event("startup")
async def startup_event():
    """Auto-load default model on startup."""
    logger.info(f"CWD: {os.getcwd()}")
    logger.info(f"Files: {os.listdir()}")
    if os.path.exists("models"):
         logger.info(f"Models dir: {os.listdir('models')}")
    
    default_model = "models/tinyllama.gguf"
    if os.path.exists(default_model):
        logger.info(f"Auto-loading default model: {default_model}")
        
        if not os.path.exists(LLAMA_BIN):
            logger.error(f"llama-server binary not found at {LLAMA_BIN}")
            return

        cmd = [
            LLAMA_BIN,
            "-m", default_model,
            "-c", "4096",
            "-ngl", "99",
            "-b", "512",
            "--port", str(LLAMA_PORT),
            "--host", LLAMA_HOST
        ]
        
        logger.info(f"Starting: {str(cmd)}")
        log_file = open("llama_server.log", "w")
        state.process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
        state.current_model = default_model

class LoadModelRequest(BaseModel):
    path: str
    ctx: int = 4096
    n_gpu: int = 99
    batch: int = 512

@app.post("/v1/models/load")
async def load_model(req: LoadModelRequest, key: str = Security(verify_api_key)):
    """Load a specific model into llama-server."""
    if not os.path.exists(req.path):
        # Try finding in current dir models/
        alt_path = os.path.join("models", req.path)
        if os.path.exists(alt_path):
            req.path = alt_path
        else:
             raise HTTPException(status_code=404, detail=f"Model not found: {req.path}")
    
    # Check binary
    req_bin = LLAMA_BIN
    if not os.path.exists(req_bin):
         # Try fallback locations
         alt_bin = os.path.abspath("llama.cpp/build/bin/llama-server")
         if os.path.exists(alt_bin):
             req_bin = alt_bin
         else:
             raise HTTPException(status_code=500, detail="llama-server binary not found. Build llama.cpp first.")

    # Stop existing
    if state.process:
        logger.info("Stopping existing server...")
        state.process.terminate()
        try:
            state.process.wait(timeout=5)
        except:
            state.process.kill()
        state.process = None

    # Start new
    cmd = [
        req_bin,
        "-m", req.path,
        "-c", str(req.ctx),
        "-ngl", str(req.n_gpu),
        "-b", str(req.batch),
        "--port", str(LLAMA_PORT),
        "--host", LLAMA_HOST
    ]
    
    logger.info(f"Starting: {str(cmd)}")
    log_file = open("llama_server.log", "w")
    state.process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    state.current_model = req.path
    
    # Wait for health
    for i in range(20):
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"http://{LLAMA_HOST}:{LLAMA_PORT}/health")
                if r.status_code == 200:
                    return {"status": "loaded", "model": req.path}
        except: pass
        time.sleep(0.5)
        if state.process.poll() is not None:
             raise HTTPException(status_code=500, detail="Server died on startup. Check logs.")

    return {"status": "started_loading", "model": req.path}

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request):
    # Public endpoints or protected?
    # For now, let verify_api_key handle it globally or per route
    # But since this is a proxy to llama-server, we might want to protect it too
    
    # Extract key manually if needed, or rely on Depends
    # For simplicity in this script, we assume trusted network OR add global dependency
    # But user wants "each server gets own API key... anytime a user downloads our they get their own API key"
    
    # Let's enforce key on proxy too
    key = request.headers.get("Authorization")
    if key != SERVER_API_KEY and key != f"Bearer {SERVER_API_KEY}":
        raise HTTPException(status_code=403, detail="Missing or Invalid API Key")

    if not state.process:
         raise HTTPException(status_code=503, detail="No model loaded. Call /v1/models/load first.")

    url = f"http://{LLAMA_HOST}:{LLAMA_PORT}/{path}"
    
    client = httpx.AsyncClient(timeout=300.0)
    try:
        # Exclude host header
        headers = dict(request.headers)
        headers.pop("host", None)
        headers.pop("content-length", None) 
        
        content = await request.body()
        
        rp_req = client.build_request(
            request.method, url,
            headers=headers,
            content=content
        )
        r = await client.send(rp_req, stream=True)
        return StreamingResponse(
            r.aiter_raw(),
            status_code=r.status_code,
            headers=r.headers,
            background=BackgroundTask(r.aclose),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=WRAPPER_PORT)

