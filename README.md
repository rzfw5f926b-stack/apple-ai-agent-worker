# apple-ai-agent-worker

Run Apple's on-device Foundation Models as an Ollama-compatible HTTP server.

Any tool that supports the Ollama or OpenAI API (OpenWebUI, LangChain, Cursor, etc.) can use your Mac's on-device AI model with zero cloud dependency.

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
python server.py
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

## Key Findings

Tested on M5 MacBook Air with apple-fm-sdk 0.2.0 (AFM Core Advanced 20B MoE):

| Task | Latency |
|------|---------|
| Simple Q&A | ~0.26s |
| Summarization | ~1.2s |
| Structured output | ~0.6s |
| Image description | ~1.4s |

**Works well:** classification, structured extraction, short text generation, image analysis (`ImageAttachment`), tool calling

**Limitation:** long-form generation is capped at ~400 characters by a system-level constraint — not a model capability issue

See [RESEARCH.md](RESEARCH.md) for full benchmark results across all four Apple AI paths (on-device 3B, HTTP server, PCC Cloud via Shortcuts, 20B MoE).

## How It Differs from Apple's `fm` CLI

Apple ships a built-in `fm` CLI in macOS 27 for terminal use. This project exposes the same model as an **HTTP API server** — so any tool with Ollama/OpenAI support can connect without code changes.

## License

MIT
