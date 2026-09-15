# AssemblyAI Dictation API Reference

Short-form dictation: send one spoken utterance (≤120s) in a single HTTP call and get back **send-ready cleaned-up text together with the verbatim transcript**. Filler is removed, self-corrections resolve to what the speaker landed on, and punctuation and capitalization are applied — by default, with no configuration. Set `llm_instruction` to ask for a different shape instead (a bulleted task list, a clinical chart note, a booking confirmation).

Dictation is a **separate service** from Sync, Pre-recorded, and Streaming STT, with its own hostname (`dictation.assemblyai.com`) and its own request shape. It runs on Universal-3.5 Pro across **32 languages**. The transcript rewrite is the one feature Dictation has that no other AssemblyAI STT API does.

**When to use which short-form API:**

| Need | Use |
|------|-----|
| Verbatim transcript of a ≤120s clip, lowest latency, optional word timestamps | **Sync STT** (`sync.assemblyai.com`) |
| Cleaned-up / reshaped text **and** the verbatim transcript from one ≤120s utterance | **Dictation** (`dictation.assemblyai.com`) |
| Audio > 120s, URLs, diarization, PII redaction, audio intelligence | Pre-recorded (async) API |
| Live partial transcripts while the speaker is still talking | Streaming v3 |

---

## Endpoint

```
POST https://dictation.assemblyai.com/v1/transcribe/live
```

| Host | Region |
|------|--------|
| `dictation.assemblyai.com` | Global default — routes to the nearest region (any US or EU location below) |
| `dictation.us.assemblyai.com` | US data residency (us-east-1, us-east-2, us-west-1, us-west-2) |
| `dictation.eu.assemblyai.com` | EU data residency (eu-central-1, eu-north-1, eu-south-1, eu-south-2, eu-west-1, eu-west-3) |

Request format, headers, and parameters are identical on all three hosts. The global host may process data in either the US or EU — call a regional host explicitly when residency matters.

- The endpoint is **`/v1` only** — there is no unversioned alias. `/v1/transcribe/stream` (the path it shipped under) still reaches the same handler; new code should use `/v1/transcribe/live`.
- **No URL ingestion.** Audio bytes go in the request body; there is no `audio_url`, no upload step, no job ID, and no polling.

## Authentication

```
Authorization: YOUR_API_KEY
```

Raw key, **no `Bearer` prefix** (same as the async REST API). Missing header → `401` with `detail: "Missing Authorization header"`; bad key → `401` with `detail: "Invalid API key"`.

## Request Body (`multipart/form-data`)

Two parts, **in this order**:

| Part | Content-Type | Notes |
|------|-------------|-------|
| `config` | `application/json` | **Required, and must come first.** A JSON object. Send `{}` to transcribe with defaults (including the default cleanup rewrite). |
| `audio` | `audio/wav` or `audio/pcm` | **Required.** Raw audio bytes, ≤120 seconds. May be uploaded in chunks as it is captured. |

**Why the order matters:** the server starts transcribing audio as it arrives and cannot begin without the config. An `audio` part that arrives before `config`, or a body with no `config` part, is rejected with `400` (`error_code: "bad_request"`). A body that isn't multipart at all gets the same error:

```json
{"error": "request must be multipart/form-data with a `config` part followed by an `audio` part", "error_code": "bad_request"}
```

### `config` fields

The config accepts **exactly** these fields. An unknown field is rejected with `400` rather than ignored — so a typo, or a Sync-STT-only option (`model`, `timestamps`, `conversation_context`) or async param (`speaker_labels`, `redact_pii`), surfaces as an error instead of silently doing nothing.

| Field | Type | Notes |
|-------|------|-------|
| `sample_rate` | integer | Source sample rate in Hz (e.g. `16000`). **Required for `audio/pcm`.** Ignored for WAV (read from the header). |
| `channels` | integer | Channel count. **Required for `audio/pcm`.** Ignored for WAV. |
| `language_codes` | string[] | Language(s) of the audio as ISO codes. **Always a list** — `["es"]` for monolingual, `["en", "es"]` for code-switching audio. Default `["en"]`. A code outside the 32 supported (below) → `400` whose `detail` lists the full set. Applies to the transcript only; the rewrite follows the transcript's language unless `llm_instruction` says otherwise. |
| `stt_prompt` | string | Max **6000** chars. Contextual *description* of the audio (e.g. `"A doctor dictating a patient visit note."`), prepended to the base transcription prompt, which always applies. Describes the situation — **not** instructions to the model. Also accepted as `prompt`; sending both → `400`. |
| `keyterms_prompt` | string[] | Max **100 terms / 8000 chars total**. Exact strings to bias the decoder toward (names, drug names, SKUs, jargon). Same name as Streaming/Pre-recorded. Legacy aliases `keyterms` and `word_boost` are accepted — send **only one** of the three or the request is `400`. Keep it to genuinely hard terms; common words dilute the list. |
| `llm_instruction` | string \| null | Max **2048** chars. Plain-English description of the rewrite you want. **Replaces** the default cleanup task (it does not add to it). Omitting the field or sending `null` keeps the default cleanup. |

**The three knobs do different jobs.** `stt_prompt` and `keyterms_prompt` steer the ASR model *while it writes the transcript*; `llm_instruction` tells the LLM what to do with that transcript *afterwards*. They compose freely.

### Audio requirements

| Constraint | Value |
|------------|-------|
| Max duration | 120 s |
| Sample width | 16-bit only |
| Formats | WAV (`audio/wav`) or raw PCM S16LE (`audio/pcm`) |
| Compressed formats | **Rejected with `415`** — MP3, M4A, FLAC, OGG, WebM cannot be decoded incrementally. Decode to WAV/PCM first. |

Raw PCM is the easiest format to upload while the user is still speaking (no container header to finalize): declare `sample_rate` and `channels` in `config` and send frames as they come off the microphone.

### Supported languages (`language_codes`)

32 codes: `en` `es` `de` `fr` `it` `pt` `tr` `nl` `sv` `no` `da` `fi` `hi` `vi` `ar` `he` `ja` `ur` `zh` (Mandarin) `ko` `ca` `gl` `ru` `ro` `et` `fa` `yue` (Cantonese) `af` `mr` `zu` `xh` `nn`.

## Response (`200`)

```json
{
  "text": "Um, patient presents with, uh, a persistent cough for about two weeks.",
  "words": [
    { "text": "Um", "confidence": 0.82 },
    { "text": "patient", "confidence": 0.97 },
    { "text": "presents", "confidence": 0.96 }
  ],
  "confidence": 0.94,
  "llm_response": "Patient presents with a persistent cough for about two weeks.",
  "llm_error": null,
  "audio_duration_ms": 5120,
  "session_id": "eb92c4ff-4bbb-429f-9b99-7279d7fe738f",
  "request_time_ms": 812.4,
  "sync_time_ms": 430.1,
  "auth_time_ms": 24.6
}
```

| Field | Type | Meaning |
|-------|------|---------|
| `text` | string | The **verbatim** transcript. Never altered by the LLM. |
| `words` | array | `{ text, confidence }` per word. **No `start`/`end` timestamps** (unlike Sync STT's opt-in `timestamps`). |
| `confidence` | number | Overall transcription confidence, 0–1. |
| `llm_response` | string \| null | The rewritten text. `null` when the rewrite failed. |
| `llm_error` | `"timeout"` \| `"error"` \| null | Set when the rewrite failed. `timeout` = the rewrite passed its **5-second** internal deadline. |
| `audio_duration_ms` | number | Duration of the submitted audio. |
| `session_id` | string (uuid) | Request identifier — include it in support requests. |
| `request_time_ms` | number | Total server-side processing time. |
| `sync_time_ms` | number | The transcription portion of `request_time_ms`. |
| `auth_time_ms` | number | The authentication portion of `request_time_ms`. |

### A failed rewrite is NOT a failed request

The rewrite is **best-effort**. If it fails, the response is still `200`, `text` still holds the verbatim transcript, `llm_response` is `null`, and `llm_error` says why. **Always fall back to `text` when `llm_response` is `null`, and never treat a non-`null` `llm_error` as an error.** The SDKs expose this as `final_text` (the rewrite when present, otherwise the transcript).

### Dictated commands are never executed

The transcript is passed to the rewrite model as fenced data with instructions not to act on it. Dictated speech like "translate this into French" or "ignore what I just said" is rewritten *as speech*, not carried out.

## Transcript rewriting (`llm_instruction`)

Default (no `llm_instruction`, or `null`): filler removed, self-corrections resolved, punctuation and capitalization applied; the speaker's phrasing and tone survive.

```
text:         "um so can we uh move the the meeting to thursday i think friday works better actually"
llm_response: "Can we move the meeting to Friday? That works better."
```

**Write only the transformation.** Output-format rules, "don't answer the text", and "return clean input unchanged" are enforced by the service — restating them wastes instruction budget and can conflict with the built-in rules.

| Instead of | Write |
|------------|-------|
| "You are a helpful medical scribe. Output only the note, nothing else. If the input is already clean, return it unchanged. Rewrite as a chart note." | "Rewrite as a concise clinical chart note." |
| "Return JSON with a summary field." | Describe the prose you want, then parse it yourself |

Instructions that work well:

- `"Remove filler words and tidy the punctuation."`
- `"Turn this into a bulleted list of action items."`
- `"Rewrite as a concise clinical chart note."`
- `"Rewrite as a short, friendly booking confirmation addressed to the client."`

## Uploading while recording (chunked upload)

The server transcribes the audio it has while the rest is still arriving, so a client that uploads *during* the recording gets its result sooner — what the user waits for after they stop speaking is the last stretch of audio, not the whole clip. (The saving grows with clip length; on a few-second clip there is little to save.)

Three rules for a chunked upload:

1. The `config` part must arrive **before the first audio byte**.
2. **Don't let the connection go silent** mid-body — an abandoned upload is timed out rather than held open. Stop by *ending* the stream, not pausing it.
3. **A chunked body can't be replayed.** Keep the audio in memory if you want to retry a failed request.

A body with a `Content-Length` also streams — the server does not wait for the full body before it begins. Errors (auth, rate limit, size, capacity) can surface **part-way through** the upload; a `413` on a chunked upload can arrive mid-request.

Without an SDK, frame the multipart body yourself and pass a generator so the HTTP client uses chunked transfer encoding:

```python
import json
import requests

BOUNDARY = "----dictation-example"
CONFIG = {"sample_rate": 16000, "channels": 1}


def multipart_body(frames):
    """Yield the config part, then each audio frame as it is captured."""
    yield (
        f"--{BOUNDARY}\r\n"
        'Content-Disposition: form-data; name="config"\r\n'
        "Content-Type: application/json\r\n\r\n"
        f"{json.dumps(CONFIG)}\r\n"
        f"--{BOUNDARY}\r\n"
        'Content-Disposition: form-data; name="audio"; filename="audio"\r\n'
        "Content-Type: audio/pcm\r\n\r\n"
    ).encode()
    for frame in frames:
        yield frame
    yield f"\r\n--{BOUNDARY}--\r\n".encode()


def record():
    """Your microphone loop, yielding 16-bit PCM bytes."""
    yield b"\0\0" * 16000


response = requests.post(
    "https://dictation.assemblyai.com/v1/transcribe/live",
    headers={
        "Authorization": "YOUR_API_KEY",
        "Content-Type": f"multipart/form-data; boundary={BOUNDARY}",
    },
    data=multipart_body(record()),  # a generator => chunked transfer encoding
    timeout=90,
)
response.raise_for_status()
result = response.json()
print(result["llm_response"] or result["text"])
```

## Connection pre-warming

`GET /warm` is an **unauthenticated no-op** that leaves an open connection in your HTTP client's pool, taking DNS + TCP + TLS off the critical path. Both `/warm` and `/v1/warm` return `200 {"warm":"toasty"}` (the SDKs call `/v1/warm`).

```bash
curl https://dictation.assemblyai.com/warm
```

Rules for it to actually help:

- **Same client / connection pool.** A fresh `requests.Session`, `httpx.Client`, or `AssemblyAI` instance for the transcription pays the handshake anyway.
- **Same host.** Pre-warming is per host — a connection warmed against `dictation.assemblyai.com` does nothing for `dictation.eu.assemblyai.com`.
- **Not too early.** Idle connections are evicted after a short window (httpx default 5s; Python SDK `aai.settings.keepalive_expiry` raises it). Warm when you *know audio is coming* — the moment the user taps record — not at app startup. Calling it again to refresh is fine; it's idempotent and cheap.

If the connection was evicted by the time you transcribe, the request silently opens a fresh one. Nothing breaks; the warm-up just bought nothing.

## Errors

Two body shapes — **read both** (check `detail` first, fall back to `error`):

| Shape | Used for |
|-------|----------|
| `{"status", "title", "detail"}` | Most errors: `401`, config validation `400`s, `413`, `415`, `429`, `5xx` |
| `{"error", "error_code"}` | Only errors raised while **parsing the request itself** (malformed body, config not valid JSON, wrong part order). `error_code` is `bad_request` in practice. |

| HTTP | Body shape | Cause | Retry? |
|------|-----------|-------|--------|
| 400 | `error`/`error_code` | Missing/empty `audio`, missing `config` or `config` after `audio`, `config` not valid JSON | Fix request |
| 400 | `status`/`title`/`detail` | Well-formed `config` that fails validation: unknown field, value out of range, over a length limit, unsupported language code, both `stt_prompt` and `prompt` | Fix request |
| 401 | `status`/`title`/`detail` | Missing `Authorization` header or invalid key | No |
| 413 | `status`/`title`/`detail` | Audio exceeded the size cap (can arrive mid-upload) | Fix audio |
| 415 | `status`/`title`/`detail` | `audio` part is not `audio/wav` or `audio/pcm` | Decode to WAV/PCM |
| 429 | `status`/`title`/`detail` | Rate limited | Back off (honor `Retry-After`) |
| 502 | `status`/`title`/`detail` | Transcription upstream unavailable | Retry once, then surface |
| 503 | `status`/`title`/`detail` | Server at capacity | Back off (honor `Retry-After`) |
| 504 | `status`/`title`/`detail` | Transcription upstream timed out | Retry once, then surface |

Set the HTTP client timeout to **90 seconds** (typical short clips respond in under a second; the SDKs default to a 300s total budget). Include `session_id` when contacting support.

---

## Examples

### cURL — defaults (verbatim + default cleanup)

```bash
curl -X POST https://dictation.assemblyai.com/v1/transcribe/live \
  -H 'Authorization: YOUR_API_KEY' \
  -F 'config={};type=application/json' \
  -F 'audio=@sample.wav;type=audio/wav'
```

### cURL — clinical dictation with all three knobs

```bash
curl -X POST https://dictation.assemblyai.com/v1/transcribe/live \
  -H 'Authorization: YOUR_API_KEY' \
  -F 'config={"stt_prompt": "A doctor dictating a patient visit note.", "keyterms_prompt": ["amoxicillin", "lisinopril", "metoprolol"], "llm_instruction": "Remove filler words and rewrite as a concise clinical chart note."};type=application/json' \
  -F 'audio=@sample.wav;type=audio/wav'
```

### Python (raw HTTP with `requests`)

```python
import json
import requests

config = {
    "language_codes": ["en"],
    "keyterms_prompt": ["Reykjavik", "Cancun", "Lufthansa"],
    "llm_instruction": "Rewrite as a short, friendly booking confirmation addressed to the client.",
}

with open("/path/to/local/recording.wav", "rb") as f:
    audio = f.read()

response = requests.post(
    "https://dictation.assemblyai.com/v1/transcribe/live",
    headers={"Authorization": "YOUR_API_KEY"},
    files={
        # `config` first, and always present. "{}" means "no settings".
        "config": (None, json.dumps(config), "application/json"),
        "audio": ("recording.wav", audio, "audio/wav"),
    },
    timeout=90,
)
if not response.ok:
    body = response.json()
    raise RuntimeError(body.get("detail") or body.get("error"))

result = response.json()
transcript = result["text"]
rewrite = result["llm_response"] or transcript  # rewrite is best-effort
print(rewrite)
```

### JavaScript (raw HTTP with `fetch`, Node 18+)

```javascript
import { readFileSync } from "fs";

const config = {
  stt_prompt: "A doctor dictating a patient visit note.",
  keyterms_prompt: ["amoxicillin", "lisinopril", "metoprolol"],
  llm_instruction: "Remove filler words and rewrite as a concise clinical chart note.",
};

const audio = readFileSync("clip.wav");
const form = new FormData();
// `config` first, and always present. "{}" means "no settings".
form.append("config", new Blob([JSON.stringify(config)], { type: "application/json" }));
form.append("audio", new Blob([audio], { type: "audio/wav" }), "clip.wav");

const response = await fetch("https://dictation.assemblyai.com/v1/transcribe/live", {
  method: "POST",
  headers: { Authorization: "YOUR_API_KEY" }, // raw key, no Bearer
  body: form,
});

if (!response.ok) {
  const error = await response.json();
  throw new Error(error.detail || error.error);
}

const result = await response.json();
const rewrite = result.llm_response ?? result.text; // rewrite is best-effort
console.log(rewrite);
```

---

## SDK support

Dictation support landed in **Python SDK 1.5.2** and **Node SDK 4.40.0**, both released on **Sept 11, 2026**; install the current releases, **Python 1.5.4** (`pip install "assemblyai>=1.5.4"`) and **Node 4.41.1** (`npm i assemblyai@^4.41.1`). Check `pip show assemblyai` / `npm ls assemblyai` in an existing project before writing code against the SDK path; on an older SDK, use the raw HTTP examples above. Both SDKs validate the config caps client-side (6000 / 100 terms + 8000 / 2048), strip whitespace from keyterms and drop empty ones, and add a derived `final_text` (`llm_response` falling back to `text`).

### Python SDK (≥1.5.4 recommended; dictation since 1.5.2)

```python
import assemblyai as aai
from assemblyai.dictation.v1 import DictationConfig, DictationTranscriber

aai.settings.api_key = "YOUR_API_KEY"
# aai.settings.dictation_base_url = "https://dictation.eu.assemblyai.com"  # data residency

config = DictationConfig(
    stt_prompt="A doctor dictating a patient visit note.",
    keyterms_prompt=["amoxicillin", "lisinopril", "metoprolol"],
    llm_instruction="Remove filler words and rewrite as a concise clinical chart note.",
)

result = DictationTranscriber().transcribe_live("/path/to/local/recording.wav", config)
print(result.text)        # verbatim
print(result.final_text)  # rewrite, falling back to the transcript
```

- `aai.DictationTranscriber`, `aai.DictationConfig`, `aai.DictationResponse`, `aai.DictationError` are also exported at the top level; the versioned import is `assemblyai.dictation.v1`.
- `transcribe_live(data, config=None)` accepts a local path, raw bytes, a binary file object, **or an iterator of PCM chunks** (pull-style live upload) — **not a URL**. Raw PCM needs `sample_rate` + `channels` on the config (they mark the audio as `audio/pcm`; leave both unset for WAV).
- `open_live(config=None)` returns a `DictationLiveSession` for **push-style** sources (a mic callback, a WebRTC track, a telephony stream): `session.write(chunk)` from any thread (never blocks), `session.close()` ends the audio, `session.result()` waits for the `DictationResponse`; `session.abort()` drops the request. Use it as a context manager — a clean exit closes, an exception aborts.
- `warm()` returns `True`/`False` and never raises. Pair with `aai.settings.keepalive_expiry` so the pooled connection survives the recording.
- `AsyncDictationTranscriber` (asyncio) has the same `transcribe_live` / `open_live` / `warm` surface; `asyncio.create_task(transcriber.warm())` overlaps the handshake with whatever else is happening.
- Failures raise `DictationError` with `status_code`, `error_code` (snake_cased server `title`, when present), and `retry_after` (seconds, from `Retry-After` on 429/503; `None` when absent — use your own backoff).
- `aai.settings.dictation_http_timeout` (default 300s) bounds each socket operation, not the whole request; the transcriber is also a context manager (`with aai.DictationTranscriber() as t:`).

```python
import assemblyai as aai
import sounddevice as sd

aai.settings.api_key = "YOUR_API_KEY"
config = aai.DictationConfig(sample_rate=16000, channels=1)

with aai.DictationTranscriber() as transcriber:
    transcriber.warm()  # as soon as you know audio is coming
    with transcriber.open_live(config) as session:
        stream = sd.RawInputStream(
            samplerate=16000, channels=1, dtype="int16",
            callback=lambda data, *_: session.write(bytes(data)),
        )
        with stream:
            input("Dictating, press Enter to stop... ")
    print(session.result().final_text)
```

### Node SDK (≥4.41.1 recommended; dictation since 4.40.0)

```typescript
import { AssemblyAI } from "assemblyai";

const client = new AssemblyAI({
  apiKey: process.env.ASSEMBLYAI_API_KEY!,
  // dictationBaseUrl: "https://dictation.eu.assemblyai.com", // data residency
});

await client.dictation.warm(); // optional, idempotent

const result = await client.dictation.transcribeLive("/path/to/local/recording.wav", {
  stt_prompt: "A doctor dictating a patient visit note.",
  keyterms_prompt: ["amoxicillin", "lisinopril", "metoprolol"],
  llm_instruction: "Remove filler words and rewrite as a concise clinical chart note.",
});
console.log(result.text);       // verbatim
console.log(result.final_text); // rewrite, falling back to the transcript
```

- `client.dictation` is a `DictationTranscriber`. `transcribeLive(audio, config?, options?)` accepts a local path, data URL, `Uint8Array`/`ArrayBuffer`, `Blob`/`File`, a web `ReadableStream`, a Node stream, or any (async) iterable of `Uint8Array` chunks — **not an http(s) URL**. `options` = `{ timeout?: number /* default 300_000 ms, whole request */, signal?: AbortSignal }`.
- `openLive(config?, options?)` returns a `DictationLiveSession` for callback-driven sources: `session.write(chunk)` (never blocks), `session.close()`, `await session.result()`, `session.abort()`.
- Raw PCM: set `sample_rate` **and** `channels` (setting either marks the audio as PCM and both become required). Leave both unset for WAV.
- `DictationConfig` is exactly `{ sample_rate, channels, language_codes, stt_prompt, keyterms_prompt, llm_instruction }` — there is no `model`, `prompt`, `timestamps`, or `conversation_context` (those are Sync STT).
- Failures throw `DictationError` with `.status`, `.errorCode`, `.retryAfter`.
- The chunked upload uses `fetch` with `duplex: "half"` under the hood, which is what lets the request start before the audio exists.
