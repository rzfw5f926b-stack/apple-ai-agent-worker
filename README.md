# apple-ai-agent-worker

**What can Apple's free built-in models take off your main AI agent's plate?**

Every Mac with Apple Intelligence ships with an on-device model, and since macOS 27 a Shortcut can call Apple's Private Cloud Compute (PCC) models too. They cost nothing per call. This repo is a field report on using them as a *sub-worker* for a main agent (Claude, GPT, etc.): which tasks they handle reliably, which they get wrong, how to call them from a script, and how to check their answers.

[繁體中文版](README.zh-TW.md)

> Tested on macOS 27.0.1, Apple Silicon, October 2026. Apple updates these models with the OS — re-run [`bench/`](bench/) after an update.

## TL;DR: what to delegate

| ✅ Delegate | ⚠️ Delegate, then verify | ❌ Keep in the main agent |
|---|---|---|
| Summarize, rewrite, translate many items | Arithmetic, percentages, dates — recompute in code | Multi-step reasoning and planning |
| Classify / tag lists (JSON labels) | OCR text from images — spot-check numbers | Fractions and exact math (PCC answers 3/8 + 5/12 = 1.0417) |
| Extract fields to JSON (incl. financial text) | Translation — tends to be literal | Exact length ("exactly 100 characters") |
| Find a fact in a long document (up to ~32k tokens) | Anything a guardrail might block — retry once | Long-form writing (output caps around 350–450 Chinese characters) |
| Draft short text, headlines, hashtags | | Judgment-heavy work, style imitation, >4 rules at once |
| Decode QR codes / barcodes (on-device) | | One-off tiny questions (faster to answer yourself) |

The pattern that pays off: let the Apple model **compress raw material** (summaries, extracted fields, labels) and hand the main agent the small result.

## Pick a backend

| Backend | How to call | Speed | Limits | Use it for |
|---|---|---|---|---|
| **Cloud** (PCC) | `shortcuts run` + a shortcut | ~0.8–1.6 s, 4 in parallel ≈ same | Daily usage limit (not published); input ~32k tokens | **Default.** Strongest overall; handles integer math and dates |
| **Cloud Pro** (PCC) | `shortcuts run` + a shortcut | similar | Hit the usage limit after ~47 calls in a row | Fallback when Cloud fails |
| **On-device** (`fm` CLI) | `/usr/bin/fm respond` | ~0.2 s short answers | 8192-token context including output | Guaranteed JSON (`--schema`), images, QR/barcodes, offline or private data |
| On-device (SDK / HTTP) | `apple-fm-sdk`, [`server.py`](docs/server.md) | similar to `fm` | same | When a tool needs an Ollama / OpenAI-compatible API |

The cloud models are **not** reachable from `fm` — only through Shortcuts. Apple documents [daily usage limits](https://support.apple.com/en-us/127901) for both cloud models without giving numbers, so batch jobs must be able to fall back to on-device.

## Setup

Requirements: macOS 27+, Apple Silicon, Apple Intelligence turned on, network access for the cloud models.

**1. Make two shortcuts.** The cloud models have no command-line interface of their own; the only way to reach them from a script is a shortcut you build yourself and then run with `shortcuts run "<name>"`. Everything in this repo assumes these two names:

| Shortcut name | Model in the "Use Model" action |
|---|---|
| `Ask Apple Cloud` | Private Cloud Compute |
| `Ask Apple Cloud Pro` | Cloud Pro |

In the Shortcuts app, create a new shortcut named **Ask Apple Cloud** with three actions:

1. **Receive** Text input (so `shortcuts run -i` can pass the prompt in)
2. **Use Model** — model: **Private Cloud Compute**; request: *Shortcut Input*
3. **Stop and Output** the model's response

Then duplicate it, rename the copy **Ask Apple Cloud Pro**, and switch its model to **Cloud Pro**. Check that both exist with `shortcuts list | grep "Ask Apple"`. (Action labels may differ slightly with your system language. If you prefer other names, pass them to the scripts with `SHORTCUTS_CHAIN` / `SC`.)

**2. Check the on-device model:** `fm available` should print `System model available`.

## Call it from your agent

```bash
# Cloud: write the prompt to a file. The -o file name MUST end in .txt.
printf '%s' "$PROMPT" > in.txt
shortcuts run "Ask Apple Cloud" -i in.txt -o out.txt && cat out.txt

# On-device
fm respond --no-stream 'Classify this headline: ...'
cat article.txt | fm respond --no-stream -i 'Summarize in one sentence'
fm respond --no-stream -g --schema label.json 'Classify: ...'          # output guaranteed to match the schema
fm respond --no-stream --image qr.png --tool barcode --text 'What does the QR code say?'
```

[`examples/delegate.sh`](examples/delegate.sh) wraps this with error handling: it tries Cloud, then Cloud Pro, then falls back to `fm`, and reports which backend answered on stderr.

```bash
examples/delegate.sh "Summarize in one sentence: ..."
cat notes.txt | SHORTCUTS_CHAIN="MyShortcut" examples/delegate.sh
```

Tips:

- Each `shortcuts run` is stateless. For multi-turn work, put the earlier turns into the prompt.
- Ask for "the answer alone on the last line" to make parsing easy.
- Run up to 4 cloud calls in parallel (e.g. a thread pool), each with its own input/output files.
- Before a big batch, send one call to make sure you are not already at the usage limit.

## Verify the answers

- **Success** = exit code 0 **and** the output file exists **and** it is not empty. An empty prompt returns exit 0 with empty output.
- **Failure** = exit code 1, message on stderr, no output file. The three messages you will see (shown in the system language):

  | Meaning | What to do |
  |---|---|
  | Guardrail refused the request (also happens on harmless prompts) | Retry or rephrase; then fall back to `fm` |
  | Usage limit reached | Switch backend (Cloud ↔ Cloud Pro ↔ `fm`) |
  | Input too long (> ~32k tokens) | Split the input |

- Recompute every number and date in code. Never trust fractions.
- For classification and extraction, spot-check a few items against the source.

## Gotchas

- `shortcuts run -o out.out` (any non-`.txt` name) exits 0 but **writes nothing**.
- Without `-o`, stdout is RTF, not plain text.
- Both cloud models answer "a foundation model developed by Apple" when asked who they are — you cannot tell them apart from the output.
- The on-device model's `--model` option only accepts `system`; the OS decides which on-device model runs.

## Benchmark results (2026-10-24)

22 questions, 3 rounds each (long-document questions 1 round). Script and raw output: [`bench/`](bench/).

| Category | Cloud | Cloud Pro | On-device `fm` | Notes |
|---|---|---|---|---|
| Integers, percentages, compound interest | 15/15 | 12/15 | 6/15 | Cloud Pro rounded 984.9 to 985; `fm` said 1234 + 5678 = 7912 |
| Fractions (3/8 + 5/12) | 0/3 | 3/3 | 0/3 | Cloud consistently answers 1.0417 (correct: 0.7917) |
| Weekday, day count, leap year, time zone | 12/12 | 12/12 | 0/12 | |
| Avoid banned words | 6/6 | 6/6 | 6/6 | |
| Exact length (100 / 50 characters) | 4/6 | 4/6 | 0/6 | |
| JSON classification (prompt only, no schema) | 6/6 | 6/6 | 6/6 | |
| Traditional Chinese only (no Simplified) | 3/3 | 1/1 | 3/3 | Cloud Pro hit its usage limit from here on |
| Prompt mentioning "internal information" | 3/3 | — | 3/3 | |
| Simple logic | 5/6 | — | 6/6 | Cloud: one guardrail false positive |
| Find a fact in 9k / 18k / 45k characters | 1/1 · 1/1 · 1/1 | — | 1/1 · 0/1 · — | 45k took 15 s; `fm` ran out of context at 18k |
| **Total** | **56/62** | **44/46** | **31/62** | |

Earlier on-device test (September 2026, `fm` CLI):

| ✅ Reliable | ⚠️ Check the output | ❌ Avoid |
|---|---|---|
| Classification with a schema enum 30/30 (free text: 27/30) | Length control (0.87–1.2× the target) | Arithmetic, dates, weekdays, time zones |
| Structured extraction 9/9; financial extraction 18/18 | OCR (`--tool ocr`) — re-check numbers | Asking about an image without `--tool` (it makes things up) |
| Names, places, times 15/15 | Multi-turn memory | Chaining several tool calls |
| Traditional Chinese summary / rewrite 15/15 | Fiction (changes course midway) | Inputs over ~7.5k tokens |
| Long-document lookup within 7k tokens 54/54 | Investment questions (adds disclaimers or refuses) | |
| QR / barcode 3/3; common knowledge 23/24 | Translation (literal) | |

## More

- [`docs/server.md`](docs/server.md) — `server.py`, an Ollama / OpenAI-compatible HTTP server over the on-device model, plus the June 2026 SDK findings (20B MoE speed, image input, streaming).
- [`docs/research-log.zh-TW.md`](docs/research-log.zh-TW.md) — the full chronological research log (Traditional Chinese), June–October 2026. Later entries correct earlier ones.
- [`experiments/`](experiments/) — early probes of Shortcuts' built-in AI actions.

## License

MIT
