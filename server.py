#!/usr/bin/env python3
"""
Apple FM — Ollama-compatible API server
Port: 11436
Model name: apple-fm:latest

Endpoints:
  GET  /api/tags
  POST /api/generate
  POST /api/chat
  GET  /api/version
  GET  /v1/models
  POST /v1/chat/completions
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

import apple_fm_sdk as fm
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

# ──────────────────────────────────────────
# Model setup
# ──────────────────────────────────────────

MODEL_NAME = "apple-fm:latest"
MODEL_ID = "apple-fm"

_model = fm.SystemLanguageModel(
    guardrails=fm.SystemLanguageModelGuardrails.PERMISSIVE_CONTENT_TRANSFORMATIONS
)

app = FastAPI(title="Apple FM Server", version="1.0.0")


# ──────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def now_ts() -> int:
    return int(time.time())


def make_session(system: Optional[str] = None) -> fm.LanguageModelSession:
    return fm.LanguageModelSession(
        model=_model,
        instructions=system or "You are a helpful assistant.",
    )


def build_prompt_from_messages(messages: list[dict]) -> tuple[str, str]:
    """Extract system prompt and build conversation string from messages."""
    system = "You are a helpful assistant."
    turns = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            system = content
        elif role == "user":
            turns.append(f"User: {content}")
        elif role == "assistant":
            turns.append(f"Assistant: {content}")

    # Last user message becomes the actual prompt
    if turns and turns[-1].startswith("User: "):
        prompt = turns[-1][len("User: "):]
        history = "\n".join(turns[:-1])
    else:
        prompt = ""
        history = "\n".join(turns)

    # Prepend history as context if exists
    if history:
        full_prompt = f"Previous conversation:\n{history}\n\nUser: {prompt}"
    else:
        full_prompt = prompt

    return system, full_prompt


async def stream_generate(session: fm.LanguageModelSession, prompt: str) -> AsyncIterator[str]:
    """Yield Ollama-format streaming chunks."""
    full = ""
    async for chunk in session.stream_response(prompt):
        text = str(chunk)
        full += text
        yield json.dumps({
            "model": MODEL_NAME,
            "created_at": now_iso(),
            "response": text,
            "done": False,
        }) + "\n"

    yield json.dumps({
        "model": MODEL_NAME,
        "created_at": now_iso(),
        "response": "",
        "done": True,
        "total_duration": 0,
        "prompt_eval_count": len(prompt.split()),
        "eval_count": len(full.split()),
    }) + "\n"


async def stream_chat(session: fm.LanguageModelSession, prompt: str) -> AsyncIterator[str]:
    """Yield Ollama chat-format streaming chunks."""
    full = ""
    async for chunk in session.stream_response(prompt):
        text = str(chunk)
        full += text
        yield json.dumps({
            "model": MODEL_NAME,
            "created_at": now_iso(),
            "message": {"role": "assistant", "content": text},
            "done": False,
        }) + "\n"

    yield json.dumps({
        "model": MODEL_NAME,
        "created_at": now_iso(),
        "message": {"role": "assistant", "content": ""},
        "done": True,
        "prompt_eval_count": len(prompt.split()),
        "eval_count": len(full.split()),
    }) + "\n"


async def stream_openai(session: fm.LanguageModelSession, prompt: str, req_id: str) -> AsyncIterator[str]:
    """Yield OpenAI SSE-format streaming chunks."""
    async for chunk in session.stream_response(prompt):
        text = str(chunk)
        data = {
            "id": req_id,
            "object": "chat.completion.chunk",
            "created": now_ts(),
            "model": MODEL_NAME,
            "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(data)}\n\n"

    final = {
        "id": req_id,
        "object": "chat.completion.chunk",
        "created": now_ts(),
        "model": MODEL_NAME,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(final)}\n\ndata: [DONE]\n\n"


# ──────────────────────────────────────────
# Ollama endpoints
# ──────────────────────────────────────────

@app.get("/api/tags")
async def list_models():
    return {
        "models": [{
            "name": MODEL_NAME,
            "model": MODEL_NAME,
            "modified_at": "2026-06-07T00:00:00Z",
            "size": 3_000_000_000,
            "digest": "apple-fm-on-device",
            "details": {
                "parent_model": "",
                "format": "apple-npu",
                "family": "apple-fm",
                "families": ["apple-fm"],
                "parameter_size": "3B",
                "quantization_level": "mixed-2-4bit",
            },
        }]
    }


@app.get("/api/version")
async def version():
    return {"version": "apple-fm-1.0.0"}


@app.post("/api/generate")
async def generate(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "")
    system = body.get("system")
    stream = body.get("stream", True)

    session = make_session(system)

    if stream:
        return StreamingResponse(
            stream_generate(session, prompt),
            media_type="application/x-ndjson",
        )
    else:
        r = await session.respond(prompt)
        return {
            "model": MODEL_NAME,
            "created_at": now_iso(),
            "response": str(r),
            "done": True,
        }


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    stream = body.get("stream", True)

    system, prompt = build_prompt_from_messages(messages)
    session = make_session(system)

    if stream:
        return StreamingResponse(
            stream_chat(session, prompt),
            media_type="application/x-ndjson",
        )
    else:
        r = await session.respond(prompt)
        return {
            "model": MODEL_NAME,
            "created_at": now_iso(),
            "message": {"role": "assistant", "content": str(r)},
            "done": True,
        }


# ──────────────────────────────────────────
# OpenAI-compatible endpoints
# ──────────────────────────────────────────

@app.get("/v1/models")
async def openai_models():
    return {
        "object": "list",
        "data": [{
            "id": MODEL_NAME,
            "object": "model",
            "created": now_ts(),
            "owned_by": "apple",
        }],
    }


@app.post("/v1/chat/completions")
async def openai_chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    req_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

    system, prompt = build_prompt_from_messages(messages)
    session = make_session(system)

    if stream:
        return StreamingResponse(
            stream_openai(session, prompt, req_id),
            media_type="text/event-stream",
        )
    else:
        t0 = time.time()
        r = await session.respond(prompt)
        elapsed_ms = int((time.time() - t0) * 1000)
        content = str(r)
        return {
            "id": req_id,
            "object": "chat.completion",
            "created": now_ts(),
            "model": MODEL_NAME,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(content.split()),
                "total_tokens": len(prompt.split()) + len(content.split()),
            },
        }


# ──────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print(f"Apple FM Server starting on http://localhost:11436")
    print(f"Model: {MODEL_NAME}")
    uvicorn.run(app, host="0.0.0.0", port=11436, log_level="warning")
