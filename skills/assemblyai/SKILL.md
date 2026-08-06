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
| REST API (async) | `https://api.assemblyai.com` | `https://api.eu.assemblyai.com` |
| Sync STT API (≤120s) | `https://sync.assemblyai.com` (global default, routes to nearest; `https://sync.us.assemblyai.com` for US residency) | `https://sync.eu.assemblyai.com` |
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

**`universal-3-5-pro` is the model to use across the board.** It is GA for **both** realtime/streaming and pre-recorded/async transcription and is the default on each. Use it everywhere by default; drop to `universal-2` only for cost or for languages outside Universal-3.5 Pro's 18. `universal-3-pro` (async) and `u3-rt-pro` (streaming) have both been **superseded by `universal-3-5-pro`** and removed from their model lists/enums.

### Pre-Recorded

| Model | Languages | Best For |
|-------|-----------|----------|
| **Universal-3.5 Pro** (recommended default) | 18 (auto-falls back to Universal-2 for the other 99) | Flagship: best accuracy, fastest, native code-switching across its 18 languages, contextual `prompt`, keyterms up to 1,000 words |
| **Universal-2** | 99 | Cost-effective; broadest language coverage; keyterms up to 200 words; fallback for languages outside Universal-3.5 Pro's 18 |

On `POST /v2/transcript`, `speech_models` is a priority list with fallback and **defaults to `["universal-3-5-pro", "universal-2"]`** when omitted — Universal-3.5 Pro handles its 18 languages and automatically falls back to Universal-2 for the rest. The async `speech_models` enum now accepts only `universal-3-5-pro` and `universal-2` (`universal-3-pro` has been removed, superseded by `universal-3-5-pro`). Universal-3.5 Pro supports contextual `prompt` (a plain-language *description* of the audio) and `keyterms_prompt` (up to 1,000 terms). Check the `speech_model_used` response field to see which model actually ran.

### Streaming

| Model | Languages | Best For |
|-------|-----------|----------|
| **universal-3-5-pro** | 18 | **Recommended default for new realtime/streaming code** — next-gen flagship: more languages, native code-switching, improved prompting + conversational context |
| **universal-streaming-english** | 1 (English) | Voice agents, ~300ms latency |
| **universal-streaming-multilingual** | 6 | Per-utterance language detection |
| **u3-rt-pro** | 6 | **Legacy** — Universal-3 Pro Streaming, **removed July 2026** from the model picker and streaming spec `speech_model` enum. Superseded by `universal-3-5-pro`. Still seen in older code |
| **whisper-rt** | 99+ | **Legacy** — removed from the public model picker (June 2026) and the streaming spec enums, but still functional via `speech_model: whisper-rt` for broadest streaming language coverage, auto-detect only |

For realtime/streaming STT, use `speech_model: "universal-3-5-pro"` by default. The raw API parameter is optional and defaults to `universal-3-5-pro`; set it explicitly when pinning behavior or using an SDK that requires the field. The streaming spec `speech_model` enum now lists only `universal-3-5-pro`, `universal-streaming-english`, and `universal-streaming-multilingual`. The `mode` connection param (universal-3-5-pro only) trades off accuracy vs latency: `min_latency`, `balanced` (default), `max_accuracy`.

### Medical Mode (Add-On)

`domain: "medical-v1"` enables Medical Mode — an add-on that improves accuracy for medical terminology (medications, procedures, conditions, dosages). Works with both pre-recorded and streaming models.

- **Pre-recorded:** Universal-3.5 Pro (`domain: "medical-v1"` in request body), Universal-2
- **Streaming:** universal-3-5-pro, universal-streaming-english, universal-streaming-multilingual
- **Supported languages:** English, Spanish, German, French (4 languages only)
- Billed as a separate add-on. If used with an unsupported language, the API ignores `domain` and returns a warning — transcript still completes and you are NOT charged for Medical Mode.

### Prompting (Universal-3.5 Pro)

`prompt` and `keyterms_prompt` are **complementary** — use either, or both together. Neither changes the output format, and both work the same way for **streaming and async** (`POST /v2/transcript`). Transcription behavior (verbatim, punctuation, formatting) is built in and managed by AssemblyAI.

- **`prompt`** (string; length cap varies by API — streaming ≤1750 chars, async up to ~1,500 words, Sync STT ≤4096 chars): a plain-language **description of the audio** — its domain, scenario, or full details. It carries *context*, **not instructions** — formatting/behavioral commands (punctuation rules, "transcribe verbatim", "don't…") are not supported and are ignored. The model stays grounded in the audio: irrelevant or only-partially-applicable context won't make it insert words that weren't spoken, so you can safely send the same description on every session/segment.
- **`keyterms_prompt`** (string[]): an explicit list of names/brands/domain terms to boost. Streaming: up to **100** terms, ≤50 chars each. Async: up to **1,000** terms.

**Contextual prompt — three levels of specificity** (use the least specific that covers your case):

| Level | Length | Contains | Example |
|-------|--------|----------|---------|
| Domain | 2–5 words | The field only | `Medical consultation call.` |
| Scenario | 5–15 words | What the call is about | `Cardiology consultation about chest pain symptoms.` |
| Detailed | 20–50 words | Names, products, identifiers | `Cardiology consultation between Dr. Smith and a patient about recurring chest pain, ECG results, and hypertension medication.` |

**Best practices:**
- **Start with no `prompt` and no `keyterms_prompt`** — the model is optimized out of the box. Add context only for domain vocabulary it gets wrong, starting at the broadest level.
- Write plain, complete sentences that *describe* the recording; keep it to one short block, not a keyword list (that's what `keyterms_prompt` is for).
- Keyterms: use exact spelling/capitalization; avoid common words (over-inclusion causes overcorrection/hallucination).
- Specify language via `language_code` (preferred) or by naming it in the prompt (e.g. "Spanish customer support call…").
- Streaming: update both mid-session via `UpdateConfiguration`; a new keyterms array replaces the prior set, `[]` clears it.

## Sync STT API (short-form audio, ≤120s)

A separate synchronous endpoint for short clips — send audio in one HTTP request, get the transcript back in the response. **No polling, no transcript ID, no `upload` step.** Ideal for voice-message transcription, short call recordings, or voice-agent pipelines that do their own turn detection and submit completed utterances.

- **Endpoint:** `POST https://sync.assemblyai.com/transcribe` (global default — routes to nearest region; use `sync.us.assemblyai.com` / `sync.eu.assemblyai.com` for data residency)
- **Required header:** `X-AAI-Model` — the current quickstart uses `universal-3-5-pro`; `u3-sync-pro` (Universal-3 Pro) is also accepted (the value in the formal spec enum)
- **Auth:** `Authorization: YOUR_API_KEY` (Bearer prefix optional here, unlike the async REST API; or pass `?token=YOUR_API_KEY`)
- **Body:** `multipart/form-data` with an `audio` part (`Content-Type: audio/wav` or `audio/pcm`) and an optional `config` JSON part
- **`config` fields:** `prompt` (≤4096 chars), `word_boost` (string[], ≤2048 chars total — this is the documented keyterms param for Sync, *not* `keyterms_prompt`), `conversation_context` (string or string[] — prior conversation turns oldest-first, for continuity across a multi-turn conversation; oldest dropped when over the context budget), `language_code` (ISO 639-1 string or list, default `en` — steers the default prompt toward the named language(s); **ignored when a custom `prompt` is set**), and for `audio/pcm` also `sample_rate` + `channels` (required for raw PCM; WAV reads them from its header)
- **Audio limits:** 80ms–120s, ≤40MB, 16-bit only, mono/stereo (stereo down-mixed), sample rates 8000/16000/22050/24000/32000/44100/48000 Hz
- **Response:** `{ text, words[{text, start, end, confidence}], confidence, audio_duration_ms, session_id }` — word timestamps use `start`/`end` (integer milliseconds), same field names as the async API; only the clip-level `audio_duration_ms` carries the `_ms` suffix
- **30s per-request deadline** (504 `inference_timeout`). For audio >120s use the async REST API; for live mic audio use Streaming.

```bash
curl -X POST https://sync.assemblyai.com/transcribe \
  -H 'Authorization: YOUR_API_KEY' \
  -H 'X-AAI-Model: universal-3-5-pro' \
  -F 'audio=@sample.wav;type=audio/wav'
```

## LeMUR is Deprecated

**LeMUR is deprecated (sunset March 31, 2026 — already sunset).** Use the LLM Gateway instead. The LLM Gateway is an OpenAI-compatible API. Key difference: you pass transcript text directly in messages (no `transcript_ids`). Transcribe first, then include `transcript.text` in your prompt.

See `references/llm-gateway.md` for models, tool calling, structured outputs, and examples.

## Key Gotchas

| Gotcha | Details |
|--------|---------|
| `prompt` + `keyterms_prompt` | **Complementary** for Universal-3.5 Pro — use either or both together. `prompt` is a contextual *description* of the audio; `keyterms_prompt` is an explicit term list. Neither changes output formatting |
| `summarization` / `auto_chapters` (top-level params) | **Deprecated.** Use **Speech Understanding** `summarization` (chaptered summary w/ timestamps + headlines) or `action_items` — `speech_understanding.request.<feature>` on `POST /v2/transcript` — or the LLM Gateway for fully custom prompts |
| PII redaction scope | Only redacts words in `text` — other feature outputs (entities, summaries) may still expose sensitive data |
| Upload key scoping | Files uploaded with one API key project cannot be transcribed with a different project's key |
| Structured outputs | Supported by OpenAI, Gemini, Claude 4.5+, Qwen, and Kimi — Claude 3.x does NOT support `json_schema` structured outputs |
| universal-3-5-pro turn detection | `universal-3-5-pro` uses punctuation (`.` `?` `!`), NOT confidence thresholds — `end_of_turn_confidence_threshold` has no effect (it applies only to Universal Streaming English/Multilingual) |
| `prompt` is context, not instructions | Universal-3.5 Pro's `prompt` *describes* the audio (domain/scenario/details). Formatting or behavioral commands (punctuation rules, "transcribe verbatim", negative directives like "don't…") are **not supported** and are ignored — transcription behavior is managed internally |
| PII audio redaction method | `override_audio_redaction_method: "silence"` replaces PII with silence instead of default beep |
| Language detection | Requires minimum 15 seconds of spoken audio for reliable results |
| LLM Gateway EU region | Only Anthropic Claude and Google Gemini models available — OpenAI models are NOT supported in EU |
| Disfluencies | Enable with `disfluencies: true` to keep "um"/"uh" in the transcript |
| Medical Mode unsupported language | API silently skips Medical Mode and does not charge for it — check for warning in response |
| Voice Agent API URL | The Voice Agent endpoint is `wss://agents.assemblyai.com/v1/ws` — NOT `/v1/voice` (renamed April 2026), `/v1/realtime` (older), or `speech-to-speech.us.assemblyai.com` (very old) |
| Voice Agent `tool.call` field | The argument dict is named `arguments`, not `args` (renamed April 2026) |
| Voice Agent stored agents (`agent_id`) | The first `session.update` either binds a reusable stored agent via `{"agent_id":"<id>"}` (the **only** field in `session`) OR sends inline config (`system_prompt`/`greeting`/`tools`/`input`/`output`) — the two modes are **mutually exclusive**; sending both raises a validation error. Create stored agents with `POST https://agents.assemblyai.com/v1/agents` |
| Voice Agent turn detection fields | Use `min_silence` (default 1000ms) and `max_silence` (default 3000ms) under `session.input.turn_detection` — `min_turn_silence`/`max_turn_silence` are the streaming/LiveKit/Pipecat field names, not Voice Agent API. Both must be in `[50, 10000]` ms with `min_silence < max_silence`. Setting either explicitly disables adaptive endpointing for the rest of the session |
| Voice Agent immutable fields | After `session.ready`, **immutable**: `greeting`, `output.voice`, `output.format` — changing them returns `immutable_field`. **Mutable**: `system_prompt`, `input.turn_detection`, `input.keyterms` (up to 100 strings), `output.volume` (0–100), `tools`, `input.format` |
| Voice Agent greeting | The `greeting` is sent **straight to the TTS engine** — it is NOT passed through the LLM. Whatever string you set is exactly what the user hears, word for word. Don't write meta-greetings like "Greet the user warmly" — TTS will literally speak that |
| Voice Agent hold-mode transcripts | While an `execution_mode: "hold"` tool is in flight, `transcript.user.delta` / `transcript.user` are NOT emitted in real time — they flush when the hold ends (on `tool.result` or `reply.create`) |
| Voice Agent audio pacing | Don't stream audio faster than realtime — excess frames are dropped server-side |
| Voice Agent session teardown billing | Just closing the WebSocket holds the session for 30s (resumable via `session.resume`) and **that grace window is billable**. Send `session.end` (`{"type":"session.end"}`) when the call is over to close immediately and stop billing — the server replies with a final `session.ended` (carrying `session_duration_seconds`, `audio_duration_seconds`) before closing the socket |
| Streaming `format_turns` digit rendering | `format_turns=true` enables punctuation, casing, and inverse text normalization (dates, times, phone numbers) — it does **NOT** control digit rendering. Numerals like "22" are a model behavior, and lexical number output ("twenty-two") is not supported in streaming |
| Streaming EU region | Moved from Ireland (eu-west-1) to Stockholm (eu-north-1) in March 2026. Endpoint host (`streaming.eu.assemblyai.com`) is unchanged |
| LLM Gateway `tool_calls` location | `tool_calls` lives at `choices[i].message.tool_calls` (under `message`), NOT at `choices[i].tool_calls` (under `choice`). `content` is `null` when only tool_calls are present |
| LLM Gateway `finish_reason` is provider-native | Don't branch tool-calling loops on `finish_reason == "tool_calls"` — the Gateway passes the provider's value through, so **Claude returns `tool_use`/`end_turn`** (OpenAI returns `tool_calls`/`stop`). Detect a tool call by the **presence of `message.tool_calls`**, not by `finish_reason` |
| Transcript `metadata.warnings` | The `Transcript` response now includes an optional `metadata` object. When present, `metadata.warnings` is an array of `{message}` objects describing issues processed during transcription (e.g. Medical Mode skipped due to unsupported language). `metadata` is omitted entirely when there is nothing to report |
| universal-3-5-pro streaming context carryover | On by default — the model carries prior finalized turns forward as context (per-session, up to `previous_context_n_turns` entries, server default `5`, range 0–100). Pass your agent's spoken reply via `agent_context` (connection-time query param to seed an opening greeting, or mid-stream via `UpdateConfiguration`; ≤1750 chars per value) so the model knows the question the user is answering. `universal-3-5-pro` only |
| Streaming diarization revised labels | With `speaker_labels` enabled, a single `SpeakerRevision` message is emitted right before `Termination` (after you send `Terminate`), containing a `revisions` array of only the turns whose speaker labels changed (matched by `turn_order`). Text and word timestamps never change — only speaker assignments. Adds ~400ms latency at session close. Use it for the final, highest-quality attribution |
| LLM Gateway `model_region: "global"` | Optional request field (only accepted value `"global"`) routes to the provider's global, non-region endpoints for lower cost. Live for Anthropic Claude now; Google Gemini 3 series coming soon. Omit for default in-region processing. **Effective July 1, 2026, in-region LLM Gateway requests cost 10% more** (provider pass-through, no AssemblyAI upcharge) — global routing keeps current pricing |
| Streaming language selection | The connection param is **`language_codes`** (plural, a **list** e.g. `["en","es"]`) — there is no singular `language_code` *input* param. It steers output toward those languages while still allowing native code-switching. `universal-3-5-pro` only. (`language_code` appears only as an *output* field when `language_detection: true`.) |
| Streaming Opus input | `encoding` accepts `opus` (raw packets — one per binary WS message) and `ogg_opus` (Ogg stream — arbitrary chunks; ffmpeg/gstreamer/MediaRecorder output), in addition to `pcm_s16le`/`pcm_mulaw`. For Opus, `sample_rate` is ignored (stream is self-describing) |
| Voice Agent HTTP tool `headers` | Server-side HTTP tools take `headers` as a **list of `{name, value}` entries** (since June 2026), NOT a `{name: value}` dict. Reads return `{name, last_set_at}` only — values are write-only and never returned (not masked as `"***"`) |
| Voice Agent BYO LLM (`llm`) | Set `llm` on a **stored agent** (REST create/update, not `session.update`) to run on your own OpenAI-compatible endpoint: `[{base_url, model, api_key}]` — one entry only, must stream, `api_key` write-only. `"llm": []` reverts to the managed model. Point `base_url` at the LLM Gateway to use a frontier model on your AssemblyAI account |
| Voice Agent webhooks | Subscribe to Voice Agent events via `POST https://agents.assemblyai.com/v1/webhook-subscriptions` (events: `session.started`/`session.completed`/`call.connected`/`call.ended`/`call.failed`; scope with `agent_id` or omit for account-wide). See `references/api-reference.md` |

## Common Mistakes

| Mistake | Correction |
|---------|------------|
| `Authorization: Bearer KEY` | `Authorization: KEY` (no Bearer prefix) — BUT the Voice Agent API (`agents.assemblyai.com`) uses `Authorization: Bearer KEY` |
| Using LeMUR API | **Deprecated.** Use LLM Gateway instead |
| Using top-level `summarization` or `auto_chapters` | **Deprecated.** Use Speech Understanding `summarization`/`action_items` (`speech_understanding.request.<feature>`) or the LLM Gateway |
| LeMUR `transcript_ids` with LLM Gateway | Pass transcript text in messages, not IDs |
| `anthropic/claude-...` model IDs | No provider prefix: `claude-sonnet-4-5-20250929` not `anthropic/claude-sonnet-4-5-20250929` |
| `claude-opus-4-20250514` / `claude-sonnet-4-20250514` on LLM Gateway | **Removed June 2026.** Use Claude Opus 4.5/4.6/4.7 or Claude Sonnet 4.5/4.6 |
| Uploading to `/v2/upload` with `-d`/`--data` or a JSON body | Use `--data-binary @file` (raw bytes). `-d`/JSON returns a valid `upload_url` but transcription later fails with `Transcoding failed. File type application/json` |
| Using Java/Go/C# SDKs | **Discontinued.** Use Python, JS/TS, Ruby, or raw API |
| `word_boost` on the async REST API | Use `keyterms_prompt` instead. **Exception:** the Sync STT API *does* use `word_boost` (in its `config` part) — that's its documented keyterms param |
| Hardcoding v2 streaming URL | v3 (`/v3/ws`) is current; v2 still works but is legacy |
| Using `speech_model=u3-rt-pro` for streaming | **Removed July 2026** from the model picker and streaming spec enum — superseded by `universal-3-5-pro` (the streaming default). Set a different model only for cost tradeoffs (`universal-streaming-english`/`-multilingual`) |
| Python SDK rejects `universal-3-5-pro` | Upgrade to `assemblyai>=0.64.21` for Streaming v3 SDK support. Older SDKs such as `0.64.4` validate `speech_model` against an enum that omits `universal-3-5-pro` |
| `aai.SpeechModel.universal_3_5_pro` in Python SDK | Use raw strings: `"universal-3-5-pro"`, `"universal-2"` — these enum aliases don't exist in the SDK |
| S2S `session.update` without `"session"` key | Must wrap config: `{"type":"session.update","session":{...}}` |
| S2S tool schema using `{"function":{...}}` nesting | S2S tools are flat: `{"type":"function","name":"...","description":"...","parameters":{...}}` |
| Voice Agent S2S URL | Correct URL: `wss://agents.assemblyai.com/v1/ws` — not `/v1/voice` (renamed April 2026), `/v1/realtime` (older), or `speech-to-speech.us.assemblyai.com` (very old) |
| Voice Agent `tool.call` `args` field | Renamed to `arguments` — `event["arguments"]` is the parameter dict |
| Medical Mode `domain: "medical"` | Correct value is `domain: "medical-v1"` |
| LLM Gateway tool result `role: "function_call_output"` | Correct role is `"tool"` — use `{"role": "tool", "tool_call_id": "...", "content": "..."}` |
| LLM Gateway response `choices[i].tool_calls` | Tool calls live under `message`: `choices[i].message.tool_calls`, not at the choice level |
| Sending `tool.result` immediately on `tool.call` | Wait until `reply.done` is the latest event received — sending earlier (mid transition phrase) or later (after a new turn started) breaks turn-taking |
| Speech Understanding without the `request` wrapper | Features nest under `speech_understanding.request.<feature>` — `speech_understanding.translation` (no `.request`) is invalid. Results come back under `speech_understanding.response.<feature>` |
| Custom Formatting params as booleans | `date`/`phone_number`/`email` are **format-pattern strings** (e.g. `"mm/dd/yyyy"`), not `true`/`false`. Only `format_utterances` is a boolean |

## Reference Files

Read the relevant reference file based on what the user needs:

| File | When to read |
|------|-------------|
| `references/python-sdk.md` | Python SDK patterns and examples |
| `references/js-sdk.md` | JavaScript/TypeScript SDK patterns |
| `references/streaming.md` | Real-time/streaming STT, v3 protocol, temp tokens, error codes |
| `references/voice-agents.md` | Voice agent integrations: LiveKit, Pipecat, turn detection, latency optimization |
| `references/llm-gateway.md` | Applying LLMs to transcripts, tool calling, available models |
| `references/speech-understanding.md` | Translation, speaker identification, custom formatting, summarization, action items |
| `references/audio-intelligence.md` | PII redaction, diarization, summarization, sentiment, chapters |
| `references/api-reference.md` | Full parameter list, export endpoints, webhooks, upload, PII policies, Sync STT API, Voice Agents REST API (stored agents, HTTP-tool headers, BYO LLM, webhook subscriptions) |

## API Spec Source of Truth

https://github.com/AssemblyAI/assemblyai-api-spec
