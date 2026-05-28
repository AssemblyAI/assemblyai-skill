---
name: assemblyai
description: Use when implementing speech-to-text, audio transcription, real-time streaming STT, audio intelligence features, or voice AI using AssemblyAI APIs or SDKs. Use when user mentions AssemblyAI, voice agents, transcription, speaker diarization, PII redaction of audio, LLM Gateway for audio understanding, or applying LLMs to transcripts. Also use when building voice agents with LiveKit or Pipecat that need speech-to-text, or when the user is working with any audio/video processing pipeline that could benefit from transcription, even if they don't mention AssemblyAI by name.
---

# AssemblyAI Speech-to-Text and Voice AI

AssemblyAI provides speech-to-text APIs, audio intelligence models, and an LLM Gateway for applying language models to transcripts. This skill corrects common mistakes that training data gets wrong — deprecated APIs, discontinued SDKs, and non-obvious auth patterns.

## Authentication

**All endpoints use the same header:**
```
Authorization: YOUR_API_KEY
```
**NOT** `Authorization: Bearer ...` — just the raw API key, no Bearer prefix. This is the #1 mistake.

## Base URLs

| Service | US | EU |
|---------|----|----|
| REST API | `https://api.assemblyai.com` | `https://api.eu.assemblyai.com` |
| LLM Gateway | `https://llm-gateway.assemblyai.com/v1` | `https://llm-gateway.eu.assemblyai.com/v1` |
| Streaming v3 | `wss://streaming.assemblyai.com/v3/ws` | `wss://streaming.eu.assemblyai.com/v3/ws` |
| Streaming v2 (legacy) | `wss://api.assemblyai.com/v2/realtime/ws` | — |
| Voice Agent API | `wss://agents.assemblyai.com/v1/ws` | `wss://agents.eu.assemblyai.com/v1/ws` |

**Streaming EU region**: As of March 2026, the EU region moved from AWS eu-west-1 (Ireland) to AWS eu-north-1 (Stockholm). The customer-facing endpoint host (`streaming.eu.assemblyai.com`) is unchanged.

## SDKs

| Language | Package | Status |
|----------|---------|--------|
| Python | `pip install assemblyai` | Active |
| JavaScript/TypeScript | `npm i assemblyai` | Active |
| Ruby | `assemblyai` gem | Active |
| Java | `assemblyai-java-sdk` | **Discontinued April 2025** |
| Go | `assemblyai-go-sdk` | **Discontinued April 2025** |
| C# .NET | `AssemblyAI` NuGet | **Discontinued April 2025** |

**Only Python, JS/TS, and Ruby SDKs are maintained.** For Java, Go, or C#, use the REST API directly.

## Speech-to-Text Models

### Pre-Recorded

| Model | Languages | Best For |
|-------|-----------|----------|
| **Universal-3 Pro** | 6 (en, es, de, fr, pt, it) | Highest accuracy, promptable transcription, keyterms up to 1,000 words |
| **Universal-2** | 99 | Broadest language coverage, keyterms up to 200 words |

Use `speech_models` as a priority list with fallback: `["universal-3-pro", "universal-2"]`.

### Streaming

| Model | Languages | Best For |
|-------|-----------|----------|
| **universal-streaming-english** | 1 (English) | Voice agents, ~300ms latency |
| **universal-streaming-multilingual** | 6 | Per-utterance language detection |
| **whisper-rt** | 99+ | Broadest streaming language support, auto-detect only |
| **u3-rt-pro** | 6 | Voice agents — punctuation-based turn detection, promptable |

### Medical Mode (Add-On)

`domain: "medical-v1"` enables Medical Mode — an add-on that improves accuracy for medical terminology (medications, procedures, conditions, dosages). Works with both pre-recorded and streaming models.

- **Pre-recorded:** Universal-3 Pro (`domain: "medical-v1"` in request body), Universal-2
- **Streaming:** u3-rt-pro, universal-streaming-english, universal-streaming-multilingual
- **Supported languages:** English, Spanish, German, French (4 languages only)
- Billed as a separate add-on. If used with an unsupported language, the API ignores `domain` and returns a warning — transcript still completes and you are NOT charged for Medical Mode.

### Prompting (Universal-3 Pro only)

Two mutually exclusive customization parameters:
- **`prompt`** (string, up to 1500 words): Natural language instructions for transcription style
- **`keyterms_prompt`** (string[], up to 1000 terms): Domain vocabulary for proper nouns, brands, technical terms

**Prompting best practices:**
- Use positive, authoritative instructions — NEVER use negative phrasing ("Don't", "Avoid", "Never") as the model gets confused
- Limit to 3-6 instructions for best results
- Prefix critical instructions with "Non-negotiable:" or "Required:"

## LeMUR is Deprecated

**LeMUR is deprecated (sunset March 31, 2026 — already sunset).** Use the LLM Gateway instead. The LLM Gateway is an OpenAI-compatible API. Key difference: you pass transcript text directly in messages (no `transcript_ids`). Transcribe first, then include `transcript.text` in your prompt.

See `references/llm-gateway.md` for models, tool calling, structured outputs, and examples.

## Key Gotchas

| Gotcha | Details |
|--------|---------|
| `prompt` + `keyterms_prompt` | **Mutually exclusive** — use one or the other |
| `summarization` / `auto_chapters` | **Deprecated.** Use LLM Gateway instead (transcribe → send text to LLM) |
| PII redaction scope | Only redacts words in `text` — other feature outputs (entities, summaries) may still expose sensitive data |
| Upload key scoping | Files uploaded with one API key project cannot be transcribed with a different project's key |
| Structured outputs | Supported by OpenAI, Gemini, Claude 4.5+, Qwen, and Kimi — Claude 3.x does NOT support `json_schema` structured outputs |
| U3 Pro turn detection | Uses punctuation (`.` `?` `!`), NOT confidence thresholds — `end_of_turn_confidence_threshold` has no effect |
| Negative prompts | Never use "Don't" or "Avoid" in prompts — rephrase as positive instructions |
| PII audio redaction method | `override_audio_redaction_method: "silence"` replaces PII with silence instead of default beep |
| Language detection | Requires minimum 15 seconds of spoken audio for reliable results |
| LLM Gateway EU region | Only Anthropic Claude and Google Gemini models available — OpenAI models are NOT supported in EU |
| Disfluencies | `disfluencies: true` works on Universal-3 Pro and Universal-2. U3 Pro can also preserve disfluencies via prompting for finer-grained control |
| Medical Mode unsupported language | API silently skips Medical Mode and does not charge for it — check for warning in response |
| Voice Agent API URL | The Voice Agent endpoint is `wss://agents.assemblyai.com/v1/ws` — NOT `/v1/voice` (renamed April 2026), `/v1/realtime` (older), or `speech-to-speech.us.assemblyai.com` (very old) |
| Voice Agent `tool.call` field | The argument dict is named `arguments`, not `args` (renamed April 2026) |
| Voice Agent turn detection fields | Use `min_silence` (default 1000ms) and `max_silence` (default 3000ms) under `session.input.turn_detection` — `min_turn_silence`/`max_turn_silence` are the streaming/LiveKit/Pipecat field names, not Voice Agent API. Both must be in `[50, 10000]` ms with `min_silence < max_silence`. Setting either explicitly disables adaptive endpointing for the rest of the session |
| Voice Agent immutable fields | After `session.ready`, **immutable**: `greeting`, `output.voice`, `output.format` — changing them returns `immutable_field`. **Mutable**: `system_prompt`, `input.turn_detection`, `input.keyterms` (up to 100 strings), `output.volume` (0–100), `tools`, `input.format` |
| Voice Agent greeting | The `greeting` is sent **straight to the TTS engine** — it is NOT passed through the LLM. Whatever string you set is exactly what the user hears, word for word. Don't write meta-greetings like "Greet the user warmly" — TTS will literally speak that |
| Voice Agent hold-mode transcripts | While an `execution_mode: "hold"` tool is in flight, `transcript.user.delta` / `transcript.user` are NOT emitted in real time — they flush when the hold ends (on `tool.result` or `reply.create`) |
| Voice Agent audio pacing | Don't stream audio faster than realtime — excess frames are dropped server-side |
| Streaming `format_turns` digit rendering | `format_turns=true` enables punctuation, casing, and inverse text normalization (dates, times, phone numbers) — it does **NOT** control digit rendering. Numerals like "22" are a model behavior, and lexical number output ("twenty-two") is not supported in streaming |
| Streaming EU region | Moved from Ireland (eu-west-1) to Stockholm (eu-north-1) in March 2026. Endpoint host (`streaming.eu.assemblyai.com`) is unchanged |
| LLM Gateway `tool_calls` location | `tool_calls` lives at `choices[i].message.tool_calls` (under `message`), NOT at `choices[i].tool_calls` (under `choice`). `content` is `null` when only tool_calls are present |
| Transcript `metadata.warnings` | The `Transcript` response now includes an optional `metadata` object. When present, `metadata.warnings` is an array of `{message}` objects describing issues processed during transcription (e.g. Medical Mode skipped due to unsupported language). `metadata` is omitted entirely when there is nothing to report |

## Common Mistakes

| Mistake | Correction |
|---------|------------|
| `Authorization: Bearer KEY` | `Authorization: KEY` (no Bearer prefix) — BUT the Voice Agent API (`agents.assemblyai.com`) uses `Authorization: Bearer KEY` |
| Using LeMUR API | **Deprecated.** Use LLM Gateway instead |
| Using `summarization` or `auto_chapters` | **Deprecated.** Use LLM Gateway instead (transcribe then summarize via LLM) |
| LeMUR `transcript_ids` with LLM Gateway | Pass transcript text in messages, not IDs |
| `anthropic/claude-...` model IDs | No provider prefix: `claude-sonnet-4-5-20250929` not `anthropic/claude-sonnet-4-5-20250929` |
| Using Java/Go/C# SDKs | **Discontinued.** Use Python, JS/TS, Ruby, or raw API |
| `word_boost` parameter | Use `keyterms_prompt` instead |
| Hardcoding v2 streaming URL | v3 (`/v3/ws`) is current; v2 still works but is legacy |
| Omitting `speech_models` / `speech_model` | **Required** — no default exists. Omitting causes the request to fail. Use `["universal-3-pro", "universal-2"]` for pre-recorded, `"u3-rt-pro"` for streaming |
| `aai.SpeechModel.universal_3_pro` in Python SDK | Use raw strings: `"universal-3-pro"`, `"universal-2"` — these enum aliases don't exist in the SDK |
| S2S `session.update` without `"session"` key | Must wrap config: `{"type":"session.update","session":{...}}` |
| S2S tool schema using `{"function":{...}}` nesting | S2S tools are flat: `{"type":"function","name":"...","description":"...","parameters":{...}}` |
| Voice Agent S2S URL | Correct URL: `wss://agents.assemblyai.com/v1/ws` — not `/v1/voice` (renamed April 2026), `/v1/realtime` (older), or `speech-to-speech.us.assemblyai.com` (very old) |
| Voice Agent `tool.call` `args` field | Renamed to `arguments` — `event["arguments"]` is the parameter dict |
| Medical Mode `domain: "medical"` | Correct value is `domain: "medical-v1"` |
| LLM Gateway tool result `role: "function_call_output"` | Correct role is `"tool"` — use `{"role": "tool", "tool_call_id": "...", "content": "..."}` |
| LLM Gateway response `choices[i].tool_calls` | Tool calls live under `message`: `choices[i].message.tool_calls`, not at the choice level |
| Sending `tool.result` immediately on `tool.call` | Wait until `reply.done` is the latest event received — sending earlier (mid transition phrase) or later (after a new turn started) breaks turn-taking |

## Reference Files

Read the relevant reference file based on what the user needs:

| File | When to read |
|------|-------------|
| `references/python-sdk.md` | Python SDK patterns and examples |
| `references/js-sdk.md` | JavaScript/TypeScript SDK patterns |
| `references/streaming.md` | Real-time/streaming STT, v3 protocol, temp tokens, error codes |
| `references/voice-agents.md` | Voice agent integrations: LiveKit, Pipecat, turn detection, latency optimization |
| `references/llm-gateway.md` | Applying LLMs to transcripts, tool calling, available models |
| `references/speech-understanding.md` | Translation, speaker identification, custom formatting |
| `references/audio-intelligence.md` | PII redaction, diarization, summarization, sentiment, chapters |
| `references/api-reference.md` | Full parameter list, export endpoints, webhooks, upload, PII policies |

## API Spec Source of Truth

https://github.com/AssemblyAI/assemblyai-api-spec
