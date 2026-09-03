# AssemblyAI Python SDK Reference

## Installation

```bash
pip install "assemblyai>=1.1.0"
```

**1.1.0 is the latest release (Sept 1, 2026).** Install it, or `pip install -U assemblyai` for whatever is newest if you are reading this later. The matched JS/TS version is `assemblyai@^4.37.1`, which shipped the same day.

Most 0.x code runs on 1.x unchanged, but four things were removed or renamed in 1.0.0 (Aug 14, 2026) — see §13 for the full migration. 1.0.0 is the oldest release with the current API surface; anything on 0.x is a different SDK generation.

## Authentication

The SDK uses the `Authorization: KEY` header (no Bearer prefix). Three ways to supply the key, in precedence order:

```python
from assemblyai.prerecorded.v2 import Transcriber

# 1. Per client — preferred in 1.x. Accepted by every transcriber and by Client().
transcriber = Transcriber(api_key="YOUR_API_KEY")
```

```python
import assemblyai as aai

# 2. Process-wide global. Still supported, still the default for any client not given a key.
aai.settings.api_key = "YOUR_API_KEY"
transcriber = aai.Transcriber()
```

3. The `ASSEMBLYAI_API_KEY` environment variable, which `settings` reads automatically — no code needed.

`api_key=` wins over an explicitly passed `client=`: the transcriber derives its own client from a copy of that client's settings with the key replaced, leaving your client untouched. That makes per-tenant keys over a shared client configuration straightforward:

```python
from assemblyai import Client, Settings
from assemblyai.prerecorded.v2 import Transcriber

shared = Client(settings=Settings(api_key="TEAM_KEY", http_timeout=60.0))
per_tenant = Transcriber(client=shared, api_key="TENANT_KEY")  # keeps http_timeout=60.0
```

## Import Style

Each product lives in a versioned subpackage. New code should import from it — the path states which product and which API version you are pinned to:

| Product | Import |
|---------|--------|
| Pre-recorded / async | `from assemblyai.prerecorded.v2 import Transcriber, AsyncTranscriber, Transcript, TranscriptionConfig` |
| Sync STT (≤120s) | `from assemblyai.sync.v1 import SyncTranscriber, AsyncSyncTranscriber, SyncTranscriptionConfig` |
| Streaming / realtime | `from assemblyai.streaming.v3 import RealTimeTranscriber, RealTimeTranscriberOptions, RealTimeParameters` |

Cross-cutting names are **not** re-exported by the subpackages — import `TranscriptStatus`, `TranscriptError`, `Settings`, `Client`, `AsyncClient`, and the global `settings` from the top-level package. Mixing both styles in one file is normal and expected.

The top-level `aai.Transcriber` / `aai.SyncTranscriber` and the flat module paths (`assemblyai.transcriber`, `assemblyai.sync`, `assemblyai.sync_api`) still work and are not deprecated — the examples below use `import assemblyai as aai` where it reads better.

---

## 1. Basic Transcription

### From a URL

```python
from assemblyai import TranscriptStatus
from assemblyai.prerecorded.v2 import Transcriber

transcriber = Transcriber(api_key="YOUR_API_KEY")
transcript = transcriber.transcribe("https://example.com/audio.mp3")

if transcript.status == TranscriptStatus.error:
    raise RuntimeError(f"Transcription failed: {transcript.error}")

print(transcript.text)
```

### From a local file

```python
import pathlib

transcript = transcriber.transcribe(pathlib.Path("/path/to/local/audio.mp3"))
```

The SDK automatically uploads the local file to AssemblyAI's servers before transcription. No separate upload step is needed. `transcribe()` accepts a `pathlib.Path`, a `str` path, a URL, raw `bytes`/`bytearray`, or an open binary file — no `str()` wrapping needed for a `Path`.

### Bounding the poll with `poll_timeout`

`transcribe()` polls until the transcript reaches a terminal status, which by default means forever. Give it a deadline so a stuck job cannot hang a request handler:

```python
from assemblyai import TranscriptError
from assemblyai.prerecorded.v2 import Transcriber

transcriber = Transcriber(api_key="YOUR_API_KEY")

try:
    transcript = transcriber.transcribe(
        "https://example.com/audio.mp3",
        poll_timeout=300,
    )
except TranscriptError as error:
    # The job keeps processing server-side; the message carries the transcript id.
    print(f"still running: {error}")
```

Available on `Transcriber.transcribe`, `Transcriber.transcribe_async`, and `AsyncTranscriber.transcribe`; omit it to keep the unbounded behavior. Pick the transcript up later with `Transcript.get_by_id(transcript_id)`.

### With TranscriptionConfig and speech_models fallback

Use `speech_models` to specify a preferred model with automatic fallback:

```python
config = aai.TranscriptionConfig(
    speech_models=["universal-3-5-pro", "universal-2"]
)

transcriber = aai.Transcriber(config=config)
transcript = transcriber.transcribe("https://example.com/audio.mp3")
print(transcript.text)
```

If the first model in the list cannot process the audio, the next model is used as a fallback.

---

## 2. Error Handling

Always check `transcript.status` after transcription:

```python
transcript = transcriber.transcribe("https://example.com/audio.mp3")

if transcript.status == aai.TranscriptStatus.error:
    print(f"Transcription failed: {transcript.error}")
else:
    print(transcript.text)
```

---

## 3. Speaker Diarization

Enable speaker labels and iterate over utterances:

```python
config = aai.TranscriptionConfig(speaker_labels=True)

transcriber = aai.Transcriber(config=config)
transcript = transcriber.transcribe("https://example.com/audio.mp3")

for utterance in transcript.utterances:
    print(f"Speaker {utterance.speaker}: {utterance.text}")
```

---

## 4. PII Redaction

### Basic redaction

```python
config = aai.TranscriptionConfig(
    redact_pii=True,
    redact_pii_policies=[
        aai.PIIRedactionPolicy.person_name,
        aai.PIIRedactionPolicy.phone_number,
        aai.PIIRedactionPolicy.email_address,
        aai.PIIRedactionPolicy.credit_card_number,
        aai.PIIRedactionPolicy.us_social_security_number,
    ],
)

transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)
print(transcript.text)  # PII is replaced with ###
```

### Substitution policy

Control how redacted text appears:

```python
config = aai.TranscriptionConfig(
    redact_pii=True,
    redact_pii_policies=[
        aai.PIIRedactionPolicy.person_name,
    ],
    redact_pii_sub=aai.PIISubstitutionPolicy.hash,  # or .entity_name
)
```

### Redacted audio

Get a version of the audio with PII bleeped out:

```python
config = aai.TranscriptionConfig(
    redact_pii=True,
    redact_pii_audio=True,
    redact_pii_policies=[
        aai.PIIRedactionPolicy.person_name,
    ],
)

transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)
redacted_audio_url = transcript.get_redacted_audio_url()
```

---

## 5. Audio Intelligence

### Sentiment Analysis

```python
config = aai.TranscriptionConfig(sentiment_analysis=True)
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)

for result in transcript.sentiment_analysis:
    print(f"{result.text} — {result.sentiment}")  # POSITIVE, NEGATIVE, NEUTRAL
```

### Entity Detection

```python
config = aai.TranscriptionConfig(entity_detection=True)
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)

for entity in transcript.entities:
    print(f"{entity.text} ({entity.entity_type})")
```

### Auto Chapters

Generates chapters with headlines, summaries, and gist for sections of audio.

```python
config = aai.TranscriptionConfig(auto_chapters=True)
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)

for chapter in transcript.chapters:
    print(f"{chapter.headline}")
    print(f"  {chapter.summary}")
    print(f"  Gist: {chapter.gist}")
```

> **Note:** `auto_chapters` and `summarization` are mutually exclusive. Do not enable both in the same config.

### IAB Categories (Topic Detection)

```python
config = aai.TranscriptionConfig(iab_categories=True)
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)

for result in transcript.iab_categories.results:
    print(result.text)
    for label in result.labels:
        print(f"  {label.label} ({label.relevance:.2f})")
```

### Content Safety Detection

```python
config = aai.TranscriptionConfig(content_safety=True)
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)

for result in transcript.content_safety.results:
    print(result.text)
    for label in result.labels:
        print(f"  {label.label} ({label.confidence:.2f})")
```

### Summarization

The top-level `summarization=True` param is **deprecated**. Use Speech Understanding summarization instead — `TranscriptionConfig` accepts the `speech_understanding` object directly, so you do NOT need to drop to raw REST for this:

```python
config = aai.TranscriptionConfig(
    speaker_labels=True,
    speech_understanding={
        "request": {
            "summarization": {"summary_type": "bullets", "effort": "low"},
        }
    },
)
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)

su = transcript.json_response.get("speech_understanding", {})
print(su.get("response", {}).get("summarization", {}).get("summary"))
```

Typed request models exist too (`aai.types.SpeechUnderstandingRequest`). For fully custom summaries, use the LLM Gateway (section 9).

> **Note:** `summarization` and `auto_chapters` are mutually exclusive. Do not enable both in the same config.

### Auto Highlights (Key Phrases)

```python
config = aai.TranscriptionConfig(auto_highlights=True)
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)

for result in transcript.auto_highlights.results:
    print(f"{result.text} (count: {result.count}, rank: {result.rank:.4f})")
```

---

## 6. Language Detection

### Automatic language detection

```python
config = aai.TranscriptionConfig(language_detection=True)
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)

print(transcript.json_response["language_code"])
print(transcript.text)
```

### Specifying a language code directly

```python
config = aai.TranscriptionConfig(language_code="es")  # Spanish
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)
print(transcript.text)
```

---

## 7. Prompting with Universal-3.5 Pro

`prompt` and `keyterms_prompt` are **complementary** — use either, or both together. `prompt` is a contextual *description* of the audio (domain → scenario → full detail), **not** formatting/behavioral instructions (those are ignored). `keyterms_prompt` is an explicit list of terms to boost (up to 1,000 for async). Start with neither and add only for vocabulary the model gets wrong.

```python
config = aai.TranscriptionConfig(
    speech_models=["universal-3-5-pro"],
    prompt="Cardiology consultation about chest pain symptoms.",
    keyterms_prompt=["Dr. Smith", "ECG", "hypertension"],
)

transcript = aai.Transcriber().transcribe("https://example.com/audio.mp3", config)
print(transcript.text)
```

> **Note on disfluencies:** Enable `disfluencies=True` to keep "ums" and "uhs" in the transcript.

---

## 8. Streaming v3 (Realtime)

Use `assemblyai.streaming.v3` for new realtime STT code. In 1.x the classes are named `RealTime*` — `RealTimeTranscriber`, `RealTimeTranscriberOptions`, `RealTimeParameters`, `RealTimeEvents`, `RealTimeError`. The former `Streaming*` names are still bound to the same objects (so `isinstance` checks and old imports keep working), but write the `RealTime*` names.

Set `speech_model="universal-3-5-pro"` explicitly; the raw API defaults to it, but the SDK parameter is required. `sample_rate` is required for PCM encodings and optional for the self-describing compressed ones (`opus`, `ogg_opus`, `aac`).

```python
from assemblyai.streaming.v3 import RealTimeParameters, RealTimeTranscriber

transcriber = RealTimeTranscriber(api_key="YOUR_API_KEY")

transcriber.connect(
    RealTimeParameters(
        speech_model="universal-3-5-pro",
        sample_rate=16_000,
    )
)

# `chunks` is any iterable of 16-bit PCM frames from your capture library.
chunks = [b"\x00\x00" * 160]
transcriber.stream(chunks)

transcriber.disconnect(terminate=True)
```

`api_key=` on the constructor covers the common case; pass `RealTimeTranscriberOptions` when you need more — `api_host`, `token` (a temporary token instead of a key), `connect_timeout`, `max_connection_retries`, `connection_retry_delay`, `terminate_timeout`.

**The SDK does not capture microphone audio.** `assemblyai.extras` and its `MicrophoneStream` were removed in 1.0.0, along with the `[extras]` install option. Bring your own capture — `pyaudio`, `sounddevice`, a loopback device, a file — and pass 16-bit PCM chunks to `stream()`.

For the async client, use `AsyncRealTimeTranscriber` (formerly `AsyncStreamingClient`) from the same module.

---

## 9. LLM Gateway Usage from Python

The LLM Gateway provides access to LLMs via AssemblyAI's infrastructure. Use `requests` to call the gateway endpoint directly. **Do not use LeMUR — it is deprecated.**

```python
import requests

API_KEY = "YOUR_API_KEY"

response = requests.post(
    "https://llm-gateway.assemblyai.com/v1/chat/completions",
    headers={
        "Authorization": API_KEY,
        "Content-Type": "application/json",
    },
    json={
        "model": "claude-sonnet-4-6",
        "messages": [
            {
                "role": "user",
                "content": "Summarize the key themes from this transcript: ...",
            }
        ],
        "temperature": 0.5,
    },
)

result = response.json()
print(result["choices"][0]["message"]["content"])
```

The gateway follows the OpenAI-compatible chat completions format. The `Authorization` header uses the API key directly — no Bearer prefix.

---

## 10. File Upload

The SDK handles file uploads automatically when you pass a local file path to `transcribe()`:

```python
transcript = transcriber.transcribe("/path/to/local/recording.wav")
```

Under the hood, the SDK uploads the file to AssemblyAI's servers and then submits the returned URL for transcription. No manual upload step is required.

If you need to upload manually (e.g., to reuse the URL across multiple transcriptions):

```python
upload_url = transcriber.upload_file("/path/to/local/recording.wav")
transcript = transcriber.transcribe(upload_url)
```

---

## 11. Sync STT (Short-Form Audio, ≤120s)

`SyncTranscriber` (`assemblyai.sync.v1`) wraps the Sync STT API — one HTTP round trip, no polling. Call `warm()` shortly before transcribing to pre-establish the connection (it's idempotent and cheap), and set `keepalive_expiry` to hold the pooled connection between requests (useful in voice-agent pipelines):

```python
import assemblyai as aai

aai.settings.api_key = "YOUR_API_KEY"
aai.settings.keepalive_expiry = 30  # seconds to keep the connection alive between requests

transcriber = aai.SyncTranscriber()
transcriber.warm()  # optional: pre-warm so transcribe() reuses the open connection

result = transcriber.transcribe(
    "/path/to/local/recording.wav",
    config=aai.SyncTranscriptionConfig(
        prompt="Customer voice message about an online order.",
        keyterms_prompt=["AssemblyAI"],
        timestamps=True,  # opt-in word-level start/end (ms)
    ),
)
print(result.text)
```

Accepts a local file path, raw bytes, or a stream — **not a URL**. There is also `transcribe_async()` and `close()`, and `AsyncSyncTranscriber` (added in 1.0.0) for asyncio callers, with an awaitable `warm()`. The model defaults to `universal-3-5-pro` (the only sync model in the SDK). `SyncTranscriptionConfig` fields mirror the REST `config` part: `model`, `prompt`, `keyterms_prompt`, `conversation_context`, `language_codes`, `timestamps`, and `sample_rate`/`channels` for raw PCM. See `references/api-reference.md` §16 for limits and error codes.

---

## 12. Asyncio Support

Every product has an asyncio transcriber: `AsyncTranscriber` (`prerecorded.v2`), `AsyncSyncTranscriber` (`sync.v1`), and `AsyncRealTimeTranscriber` (`streaming.v3`).

The async HTTP transcribers hold a connection pool, so use them as async context managers and the pool is always released:

```python
import asyncio

from assemblyai.prerecorded.v2 import AsyncTranscriber


async def main():
    async with AsyncTranscriber(api_key="YOUR_API_KEY") as transcriber:
        transcript = await transcriber.transcribe(
            "https://example.com/audio.mp3",
            poll_timeout=300,
        )
        print(transcript.text)


asyncio.run(main())
```

`aclose()` is the explicit equivalent. A client you pass in with `client=` stays yours to close; anything the transcriber builds itself — including a client derived because you also passed `api_key=` — it closes itself.

---

## 13. Migrating from 0.x to 1.x

Most 0.x code runs on 1.x unchanged. No method signature was narrowed, every argument that worked in 0.x still works, and the new ones are optional keywords. Four things actually break:

| 0.x | 1.x |
|-----|-----|
| `aai.Lemur(...)` and every `aai.Lemur*` name | **Removed.** No drop-in replacement in the package — transcribe, then send `transcript.text` to the LLM Gateway (§9) |
| `pip install "assemblyai[extras]"` | **Removed** — the install fails. Use `pip install -U assemblyai` |
| `from assemblyai.extras import MicrophoneStream` | **Removed.** Capture PCM yourself and pass chunks to `RealTimeTranscriber.stream(...)` (§8) |
| `StreamingClient`, `AsyncStreamingClient`, `StreamingClientOptions`, `StreamingParameters`, `StreamingSessionParameters`, `StreamingEvents`, `StreamingError`, `StreamingErrorCodes` | Renamed `RealTimeTranscriber`, `AsyncRealTimeTranscriber`, `RealTimeTranscriberOptions`, `RealTimeParameters`, `RealTimeSessionParameters`, `RealTimeEvents`, `RealTimeError`, `RealTimeErrorCodes`. **The old names still work** — each is bound to the same object — so this one is a style migration, not a breakage |

What did *not* change:

- `aai.settings.api_key = "..."` still works and is still the default for any client not given a key.
- `aai.Transcriber()` / `aai.SyncTranscriber()` and the flat import paths (`assemblyai.transcriber`, `assemblyai.sync`, `assemblyai.sync_api`) still work and are not deprecated.

Worth adopting once you are on 1.x:

| Pattern | Why |
|---------|-----|
| `Transcriber(api_key="...")` | Keeps the key out of process-wide state; works per-tenant over a shared client |
| `transcribe(url, poll_timeout=300)` | An unbounded poll can hang a request handler indefinitely |
| `if transcript.status == TranscriptStatus.error:` | A failed transcription is **returned, not raised** — `text` and `words` are `None` |
| `async with AsyncTranscriber(...)` | Releases the HTTP connection pool |
| `SyncTranscriber.warm()` + `settings.keepalive_expiry` | Keeps the DNS + TCP + TLS handshake off the critical path (§11) |
| `transcribe(pathlib.Path(...))` | `Path` is accepted directly; no `str()` wrapping |
| `from assemblyai.prerecorded.v2 import Transcriber` | States the product and API version you are pinned to |

Upstream guide: https://github.com/AssemblyAI/assemblyai-python-sdk/blob/master/MIGRATION.md
