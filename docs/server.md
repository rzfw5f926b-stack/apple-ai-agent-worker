# Ollama / OpenAI-compatible server for the on-device model

`server.py` wraps the on-device Apple Foundation Model (via `apple-fm-sdk`) in an HTTP server, so any tool that speaks the Ollama or OpenAI API (OpenWebUI, LangChain, Cursor, etc.) can use it with zero cloud dependency.

> Since macOS 27 the built-in `fm serve` command also exposes an OpenAI-compatible endpoint. Use `server.py` when you need the Ollama endpoints or per-session multi-turn state.

## Requirements

- macOS 27 (Golden Gate) or later
- Apple Silicon (M1+)
- Apple Intelligence enabled
- Python 3.10+
- Xcode 26+ installed

## Install

```bash
pip install apple-fm-sdk
pip install fastapi uvicorn
```

## Quick Start

```bash
python server.py   # or ./run.sh
# Server running at http://localhost:11436
```

Ollama-compatible endpoints:

```
GET  /api/tags
POST /api/generate
POST /api/chat
GET  /api/version
```

OpenAI-compatible endpoints:

```
GET  /v1/models
POST /v1/chat/completions
```

## Usage

```bash
# Ollama style
curl http://localhost:11436/api/generate -d '{
  "model": "apple-fm:latest",
  "prompt": "Summarize this article in 3 bullet points."
}'

# OpenAI style
curl http://localhost:11436/v1/chat/completions -d '{
  "model": "apple-fm:latest",
  "messages": [{"role": "user", "content": "Hello"}]
}'
```

Multi-turn conversation works via session reuse — the server maintains session state per `session_id`.

## Findings (June 2026)

Tested on an Apple Silicon Mac with apple-fm-sdk 0.2.0 (AFM Core Advanced 20B MoE):

| Task | Latency |
|------|---------|
| Simple Q&A | ~0.26s |
| Summarization | ~1.2s |
| Structured output | ~0.6s |
| Image description | ~1.4s |

**Works well:** classification, structured extraction, short text generation, image analysis (`ImageAttachment`), tool calling

**Limitation:** long-form generation is capped at ~400 characters by a system-level constraint — not a model capability issue

See the [research log](research-log.zh-TW.md) for full benchmark results across all Apple AI paths (on-device 3B, HTTP server, PCC Cloud via Shortcuts, 20B MoE, and the October 2026 Cloud / Cloud Pro / `fm` CLI comparison).
