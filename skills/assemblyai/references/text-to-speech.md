# AssemblyAI Text-to-Speech API Reference

AssemblyAI's Text-to-Speech (TTS) API converts text into ultra-realistic speech with low latency. It supports both **buffered and streamed HTTP synthesis** for single texts, and a **full-duplex WebSocket session** for streaming conversational audio in real-time voice applications.

TTS is a **separate service** from Speech-to-Text (STT) and Voice Agents, with its own dedicated endpoints and hostnames (`tts.us.assemblyai.com` and `tts.eu.assemblyai.com`).

---

## Endpoints

### HTTP API (One-shot and Chunked Streaming)

```
POST https://tts.us.assemblyai.com/v1/speech
```

| Host | Region / Data Residency |
|------|------------------------|
| `tts.us.assemblyai.com` | US data residency (default) |
| `tts.eu.assemblyai.com` | EU data residency |

- **Buffered synthesis** (`"stream": false`): Returns complete audio bytes in the response body along with metadata in `X-TTS-*` response headers.
- **Streamed synthesis** (`"stream": true`, default on the HTTP streaming route): Returns chunked audio as the model generates it, allowing playback to begin within tens of milliseconds.

### WebSocket API (Real-Time Bidirectional Session)

```
wss://tts.us.assemblyai.com/v1/ws
```

| Host | Region / Data Residency |
|------|------------------------|
| `wss://tts.us.assemblyai.com/v1/ws` | US data residency (default) |
| `wss://tts.eu.assemblyai.com/v1/ws` | EU data residency |

The WebSocket session allows conversational applications to pipeline text generation (`generate`), trigger audio flushes (`flush`), interrupt speech on barge-in (`cancel`), receive word boundaries (`wordBoundaries`), and stream synthesized audio chunks continuously over a persistent connection.

---

## Authentication

### Server-Side Applications

All HTTP and WebSocket requests authenticate using the same raw API key header:

```
Authorization: YOUR_API_KEY
```

**Never** add a `Bearer ` prefix. Just pass the raw API key.

### Client-Side / Browser Sessions

For client-side web or mobile applications where your private API key must not be exposed, generate a short-lived temporary token from your backend server:

```bash
curl -X POST https://token.assemblyai.com/v1/token \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"expires_in_seconds": 300}'
```

Pass the returned token in the `Authorization: Token <TEMPORARY_TOKEN>` header or as a `?token=<TEMPORARY_TOKEN>` query parameter when connecting to the WebSocket endpoint.

---

## Voices

AssemblyAI provides 16 studio-quality in-house voices.

### 11 Built-in Voices (English + Multilingual)

All 11 built-in voices can speak all 6 supported core languages:

| Voice ID | Gender | Accent / Style | Notes |
|----------|--------|----------------|-------|
| `aai-jane` | Female | US English | **Default voice** |
| `aai-alba` | Female | US English | Warm, friendly |
| `aai-anna` | Female | US English | Clear, professional |
| `aai-charles` | Male | US English | Deep, conversational |
| `aai-eve` | Female | US English | Expressive, energetic |
| `aai-george` | Male | US English | Confident, narrative |
| `aai-jean` | Female | US English | Natural, calm |
| `aai-mary` | Female | US English | Authoritative, formal |
| `aai-michael` | Male | US English | Articulate, approachable |
| `aai-paul` | Male | UK English | British accent |
| `aai-vera` | Female | UK English | British accent |

### Native-Accent Multilingual Voices

These voices are tuned for native language pronunciation:

| Voice ID | Gender | Native Language |
|----------|--------|-----------------|
| `aai-giovanni` | Male | Italian |
| `aai-lola` | Female | Spanish |
| `aai-juergen` | Male | German |
| `aai-rafael` | Male | Portuguese |
| `aai-estelle` | Female | French |

> **Crucial Rule:** Always specify the voice with `voice_id` (e.g. `voice_id="aai-jane"`). Using `voice` is rejected with an explicit validation error pointing to `voice_id`.

---

## HTTP Request Parameters (`POST /v1/speech`)

Send a JSON object with the following fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `text` | string | **Required** | The text to speak. |
| `voice_id` | string | `"aai-jane"` | Voice identifier (e.g. `"aai-alba"`, `"aai-charles"`). |
| `stream` | boolean | `true` | `false` buffers until complete; `true` yields chunked audio. |
| `language` | string | Voice default | Language name: `english`, `spanish`, `german`, `french`, `italian`, `portuguese` (case-insensitive). |
| `sample_rate` | integer | `24000` | Output rate in Hz: `8000`, `16000`, `22050`, `24000`, `44100`, `48000`. |
| `encoding` | string | `"pcm_s16le"` | Codec: `"pcm_s16le"` (16-bit linear PCM), `"pcm_mulaw"` (8-bit G.711 μ-law), `"pcm_alaw"` (8-bit G.711 A-law), or `"mp3"`. |
| `container` | string | `"raw"` | Container format: `"raw"` (headerless audio bytes) or `"wav"`. Only valid for PCM/mulaw/alaw codecs (not MP3). |
| `bit_rate` | integer | `64000` | MP3 bit rate in bps: `32000`, `48000`, `64000`, `96000`, `128000` (max `64000` at 8 kHz). Only with `encoding="mp3"`. |
| `extend_biometric_consent` | boolean | `false` | When using a custom cloned voice, set `true` to renew the 60-day biometric consent window. |

### Response Headers (`X-TTS-*`)

On a `200 OK` response, metadata is returned in response headers:

| Header | Description |
|--------|-------------|
| `X-Request-Id` | Unique ID for support and diagnostics. |
| `X-TTS-Region` | AWS region that synthesized the audio (e.g. `us-west-2`). |
| `X-TTS-Model` | Model used (e.g. `assemblyai-tts-1`). |
| `X-TTS-Voice-Id` | Active voice ID. |
| `X-TTS-Language` | Language code used. |
| `X-TTS-Encoding` | Codec (e.g. `pcm_s16le`, `pcm_mulaw`). |
| `X-TTS-Sample-Rate` | Sample rate in Hz. |
| `X-TTS-Container` | Container format (`raw` or `wav`). |
| `X-TTS-Bit-Rate` | MP3 bit rate if applicable. |
| `X-TTS-Billed-Characters`| Total billed character count. |
| `X-TTS-Audio-Duration-Ms`| Audio length in milliseconds. |

---

## Python SDK Reference (`assemblyai>=1.8.2`)

### 1. Buffered Synthesis (`synthesize`)

Returns the complete audio bytes in `response.audio` as a `bytes` object:

```python
import assemblyai as aai

aai.settings.api_key = "YOUR_API_KEY"

tts = aai.TextToSpeech()

# Generate a WAV file with Jane
config = aai.TTSConfig(
    voice_id="aai-jane",
    container=aai.TTSContainer.wav,
    sample_rate=24000,
)
response = tts.synthesize("Hello from AssemblyAI Text-to-Speech!", config=config)

with open("output.wav", "wb") as f:
    f.write(response.audio)

print(f"Generated {response.audio_duration_ms}ms of audio ({response.billed_characters} chars)")
```

### 2. Streamed HTTP Audio (`stream`)

Yields chunked audio bytes in real-time as the server produces them:

```python
import assemblyai as aai

aai.settings.api_key = "YOUR_API_KEY"

tts = aai.TextToSpeech()

config = aai.TTSConfig(
    voice_id="aai-michael",
    encoding=aai.TTSEncoding.pcm_mulaw,
    sample_rate=8000,
)

with tts.stream("Streaming straight to your audio output.", config=config) as stream:
    for chunk in stream:
        pass  # Send chunk to audio output or telephony stream
```

### 3. Real-Time WebSocket Session (`TTSSession`)

Ideal for voice agents, LLM pipelines, and conversational interfaces:

```python
import assemblyai as aai

aai.settings.api_key = "YOUR_API_KEY"

session = aai.TTSSession(config=aai.TTSConfig(voice_id="aai-alba"))
session.connect()

# Simple request-response speaking
for chunk in session.speak("How can I assist you today?"):
    pass

session.close()
```

### 4. Pipelining LLM Tokens & Barge-in (`generate`, `flush`, `cancel`)

For ultra-low latency voice agents where text streams token-by-token from an LLM:

```python
import assemblyai as aai

aai.settings.api_key = "YOUR_API_KEY"

session = aai.TTSSession(config=aai.TTSConfig(voice_id="aai-jane"))
session.connect()

# Stream text in chunks as the LLM generates them
session.generate("I can help ")
session.generate("you find your order details.")
session.flush()

# Read the synthesized audio
for chunk in session.audio():
    pass

# If the user interrupts (barge-in): cancel pending audio immediately
session.cancel()

session.close()
```

### 5. Async Support (`AsyncTextToSpeech`, `AsyncTTSSession`)

```python
import assemblyai as aai

aai.settings.api_key = "YOUR_API_KEY"

async_tts = aai.AsyncTextToSpeech()
response = await async_tts.synthesize("Synthesized asynchronously.")

async_session = aai.AsyncTTSSession(config=aai.TTSConfig(voice_id="aai-paul"))
await async_session.connect()
async for chunk in async_session.speak("Speaking over async WebSocket."):
    pass
await async_session.close()
```

---

## JavaScript / Node.js SDK Reference (`assemblyai@^4.42.0`)

```typescript
import { AssemblyAI } from "assemblyai";

const client = new AssemblyAI({
  apiKey: "YOUR_API_KEY"
});

// 1. Buffered synthesis
const response = await client.tts.synthesize({
  text: "Hello from the Node.js SDK!",
  voice_id: "aai-jane",
  container: "wav"
});
// response.audio is a Uint8Array

// 2. Streamed synthesis
const stream = await client.tts.stream({
  text: "Streaming audio chunks directly.",
  voice_id: "aai-alba"
});
for await (const chunk of stream) {
  // stream chunk
}

// 3. WebSocket session
const session = client.tts.session({ voiceId: "aai-michael" });
await session.connect();

for await (const chunk of session.speak("WebSocket speech synthesis.")) {
  // handle audio chunk
}

await session.close();
```

---

## Error Handling

TTS errors raise `TTSError`, which contains the machine-readable error envelope:

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | string | Human-readable explanation. |
| `status_code` | int \| None | HTTP status (or `None` on WebSocket frames). |
| `error_code` | string \| None | Stable code: `invalid_parameter`, `voice_not_found`, `biometric_terms_not_accepted`, `rate_limited`, `at_capacity`, `auth_unavailable`. |
| `retryable` | bool \| None | `true` if retrying with the same parameters may succeed. |
| `retry_after` | int \| None | Backoff recommendation in seconds (from `Retry-After`). |
| `request_id` | string \| None | Request UUID to quote when contacting AssemblyAI support. |
| `param` | string \| None | Faulty parameter name. |

```python
import assemblyai as aai
from assemblyai import TTSError

try:
    tts = aai.TextToSpeech()
    res = tts.synthesize("Sample text")
except TTSError as e:
    if e.retryable:
        print(f"Transient error. Retry after {e.retry_after}s (Request: {e.request_id})")
    else:
        print(f"Fatal error ({e.error_code}): {e.message}")
```

---

## Common Mistakes

| Mistake | What Happens | Fix |
|---------|--------------|-----|
| Using `voice: "aai-jane"` | Request rejected with `ValueError` pointing to `voice_id` | Use `voice_id="aai-jane"` (or `TTSConfig(voice_id=...)`) |
| Passing `Authorization: Bearer KEY` | `401 Unauthorized` | Pass raw key `Authorization: KEY` with no Bearer prefix |
| Calling `https://api.assemblyai.com` for TTS | `404 Not Found` | Use the dedicated TTS host: `https://tts.us.assemblyai.com` |
| Setting `container="wav"` with `encoding="mp3"` | Rejected with validation error | WAV container is only supported for PCM and G.711 codecs |
| Putting private API key in frontend app | Security risk | Mint temporary tokens with `POST https://token.assemblyai.com/v1/token` |
| Forgetting to call `session.flush()` after `session.generate(...)` | Server waits for more text and does not complete audio stream | Always call `session.flush()` when done queueing speech turns |
| Trying to ingest URLs | TTS takes text in, returns speech out | Provide the text string in the `text` parameter |
