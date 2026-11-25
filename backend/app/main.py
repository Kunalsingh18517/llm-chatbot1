import json
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import ALLOWED_ORIGINS, DEFAULT_SYSTEM_PROMPT, ENABLE_FAILURE_SIMULATION, LLM_API_KEYS
from .database import database_is_ready, get_connection, initialize_database
from .llm_service import AllProvidersUnavailable, generate_reply
from .schemas import ChatRequest, ChatResponse

app = FastAPI(title="Lyftr AI Chatbot", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Simulate-Failure"],
)


@app.on_event("startup")
def startup() -> None:
    initialize_database()


@app.get("/health")
def health():
    if not database_is_ready() or len(LLM_API_KEYS) < 2:
        raise HTTPException(status_code=503, detail="service not ready")
    return {"status": "ok", "keys_configured": len(LLM_API_KEYS), "cache_enabled": True}


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, x_simulate_failure: str | None = Header(default=None)):
    if x_simulate_failure and not ENABLE_FAILURE_SIMULATION:
        # Ignore the test hook unless explicitly enabled in the deployment environment.
        x_simulate_failure = None

    with get_connection() as connection:
        previous = connection.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
            (payload.session_id,),
        ).fetchall()

    system_prompt = payload.system_prompt.strip() if payload.system_prompt and payload.system_prompt.strip() else DEFAULT_SYSTEM_PROMPT
    llm_messages = [{"role": "system", "content": system_prompt}]
    llm_messages.extend({"role": row["role"], "content": row["content"]} for row in previous)
    llm_messages.append({"role": "user", "content": payload.message})

    try:
        result = await generate_reply(llm_messages, x_simulate_failure)
    except AllProvidersUnavailable:
        raise HTTPException(status_code=503, detail="all providers unavailable")
    except Exception:
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable")

    created_at = datetime.now(timezone.utc).isoformat()
    metadata_json = json.dumps(result["metadata"])
    # Save only after a successful model response: failed requests never enter history.
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO messages(session_id, role, content, metadata, created_at) VALUES (?, 'user', ?, NULL, ?)",
            (payload.session_id, payload.message, created_at),
        )
        connection.execute(
            "INSERT INTO messages(session_id, role, content, metadata, created_at) VALUES (?, 'assistant', ?, ?, ?)",
            (payload.session_id, result["reply"], metadata_json, created_at),
        )

    return {"session_id": payload.session_id, "reply": result["reply"], "metadata": result["metadata"]}


@app.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str):
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT role, content, metadata FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="session not found")

    messages = []
    for row in rows:
        item = {"role": row["role"], "content": row["content"]}
        if row["role"] == "assistant" and row["metadata"]:
            item["metadata"] = json.loads(row["metadata"])
        messages.append(item)
    return {"session_id": session_id, "messages": messages}
