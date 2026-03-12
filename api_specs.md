# PEEPEESEE Engine API Specifications

**Base URL**: `http://localhost:8000` (or your VPS IP `http://76.13.24.113:8000`)
**Authentication**: None required for local access. If accessing via VPS proxy, use Bearer Token: `ol1JW3OJwgOhQLGmyjYHtSidN8flHI4QhaFNwJCBa82f7732`.
**CORS**: Enabled for all origins (`*`).

## 1. System Status & Dashboard
**Endpoint**: `GET /status`
**Description**: Polling endpoint for real-time dashboard updates (Poll every 2-5s).

**Response Example**:
```json
{
  "name": "PEEPEESEE Engine",
  "status": "ENGAGED",
  "bartowski_mode": "ON",
  "active_model": "DeepSeek-V3-70B.gguf",
  "available_models": ["DeepSeek-V3-70B.gguf", "Dolphin-2.9.gguf"],
  "dashboard": {
    "hybridizer_status": "IDLE",  // or "HYBRIDIZING"
    "hybridization_percent": "0%",
    "last_loaded": "5m ago",
    "cycle_interval": "5.0 min",
    "self_cycler": "ENABLED"
  }
}
```

## 2. Model Management
**List Models**: `GET /v1/models`
Returns OpenAI-compatible model list.
```json
{
  "object": "list",
  "data": [
    {"id": "DeepSeek-V3-70B", "object": "model", "owned_by": "peepeesee"}
  ]
}
```

**Load Model**: `POST /v1/models/load`
**Body**:
```json
{
  "model": "DeepSeek-V3-70B" // Partial matching works
}
```

## 3. Hybridizer Control
**Configure Hybrid Profile**: `POST /v1/hybridize/configure`
Sets the active rotation pool.
**Body**:
```json
{
  "models": ["DeepSeek", "Dolphin"]
}
```

**Trigger Cycle**: `POST /v1/hybridize/trigger`
Forces an immediate hybrid cycle.
**Body**: `{}` (Empty JSON)

## 4. Agent Chat (Neural Interface)
**Endpoint**: `POST /v1/agents/chat`
**Description**: Conversational endpoint for agents. Auto-loads required model if needed.

**Body**:
```json
{
  "agent_id": "user_session_1",
  "message": "Hello, hybridizer."
}
```

**Response**:
```json
{
  "response": "Greetings, user. I am online.",
  "agent_id": "user_session_1",
  "used_model": "DeepSeek-V3-70B.gguf"
}
```

## 5. Tools Management
**List Tools**: `GET /v1/tools`
**Add Tool**: `POST /v1/tools/add`
**Body**:
```json
{
  "name": "read_file",
  "description": "Reads a file from disk",
  "command": "python read_file.py {path}" // Optional
}
```
