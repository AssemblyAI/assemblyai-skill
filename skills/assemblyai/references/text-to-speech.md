# AssemblyAI Text-to-Speech API Reference

AssemblyAI's Text-to-Speech (TTS) API converts text into ultra-realistic speech with low latency. It supports both **buffered and streamed HTTP synthesis** for single texts, and a **full-duplex WebSocket session** for streaming conversational audio in real-time voice applications.

TTS is a **separate service** from Speech-to-Text (STT), with its own dedicated endpoints and hostnames (`tts.us.assemblyai.com` and `tts.eu.assemblyai.com`). Voices are named by a library slug in `voice_id`, such as `aai-kyla`.

---

## Endpoints

### HTTP API (One-shot and Chunked Streaming)

```
POST https://tts.us.assemblyai.com/v1/speech
```

| Host | Region / Data Residency |
|------|------------------------|
| `tts.us.assemblyai.com` | US data zone (`us-east-1`) |
| `tts.eu.assemblyai.com` | EU data zone (`eu-north-1`) |

There is no global TTS host: the host picks the zone, and no parameter does.

- **Streamed synthesis** (`"stream": true`, the default): Returns chunked audio as the model generates it, allowing playback to begin long before synthesis ends.
- **Buffered synthesis** (`"stream": false`): Returns the complete audio in the response body, with metadata in `X-TTS-*` response headers.
- **Word timings**: `POST /v1/speech/events` returns the audio and its word boundaries as server-sent events. Its body differs from `/v1/speech`; see [Word Timings](#word-timings-post-v1speechevents).

### WebSocket API (Real-Time Bidirectional Session)

```
wss://tts.us.assemblyai.com/v1/ws
```

| Host | Region / Data Residency |
|------|------------------------|
| `wss://tts.us.assemblyai.com/v1/ws` | US data zone |
| `wss://tts.eu.assemblyai.com/v1/ws` | EU data zone |

The WebSocket session lets conversational applications stream text in as it is written (`Generate`), conclude a request (`Flush`), interrupt speech on barge-in (`Cancel`), receive word timings (`WordBoundaries` frames) and stream synthesized audio continuously over a persistent connection. See [WebSocket Protocol](#websocket-protocol) for the frames.

---

## Authentication

### Server-Side Applications

All HTTP and WebSocket requests authenticate with the API key in the `Authorization` header:

```
Authorization: YOUR_API_KEY
```

Send exactly one credential: when the header is present, a `token` query parameter is ignored.

### Client-Side / Browser Sessions

For browser or mobile apps, where the API key must not be exposed, mint a short-lived temporary token on your server. It is a `GET` with two required query parameters:

```bash
curl "https://token.assemblyai.com/v1/token?product=tts&expires_in_seconds=60" \
  -H "Authorization: YOUR_API_KEY"
```

```json
{ "token": "eyJhbGciOi...", "expires_in_seconds": 60 }
```

- `product=tts` (required) and `expires_in_seconds` (required, `1`–`600`: how long the token can wait before it opens a session). Optional `max_session_duration_seconds` (at least `60`) caps the session.
- `token.assemblyai.com` mints from the nearest region; `token.us.assemblyai.com` and `token.eu.assemblyai.com` mint within a zone.
- On the WebSocket, pass the token as the `token` query parameter (`wss://tts.us.assemblyai.com/v1/ws?token=...`). The HTTP API reads credentials only from `Authorization`, never from the query string.
- Mint a new token for every connection (reconnects included) and every HTTP request. A token works on either zone's TTS host.
- From a page, the HTTP API accepts every origin (`Access-Control-Allow-Origin: *`, without credentials mode) and exposes the `X-TTS-*` headers.
- SDKs: Node `await client.tts.createTemporaryToken({ expires_in_seconds: 60 })` returns the token string; Python opens a session with `aai.TTSSession(config, token=token)`.

---

## Voices

Name every voice with `voice_id`. **Use `aai-kyla` as the recommended voice** (American English, from the voice catalog; the dashboard's default). Leaving `voice_id` out gives the API's default voice, `aai-jane`.

### Built-in Voices

Eleven AssemblyAI voices are built into the model: `aai-jane` (default), `aai-alba`, `aai-anna`, `aai-charles`, `aai-eve`, `aai-george`, `aai-jean`, `aai-mary`, `aai-michael`, `aai-paul` and `aai-vera`. They speak English by default, and any of the six languages when you set `language`.

### Voice Catalog

Beyond the built-ins, the voice catalog has library voices named by the same `aai-` slug pattern, such as `aai-sara` and `aai-kyla` (American English), `aai-lola` (British English), `aai-giovanni` (Italian), `aai-rafael` (Spanish) and `aai-estelle` (French). Browse them, with descriptions and samples, in the dashboard's Voice Library, or list them with `GET https://tts.us.assemblyai.com/v1/voices?scope=public` (same `Authorization` header). Without `scope`, the listing returns only your own cloned voices (`scope=owned`). The public catalog has thousands of voices, so the response is paginated: `{voices, has_more, next_cursor, total_count}`; pass `cursor=<next_cursor>` while `has_more` is true. Each entry has `slug`, `name`, `language`, `description` and `tags`. A catalog voice speaks its own language unless `language` is set. Do not guess slugs: an unknown one is refused with `voice_not_found`.

### Cloned Voices

Cloned voices are created in the AssemblyAI dashboard and named by their ID (a UUID) or slug in `voice_id`. A cloned voice belongs to the data zone it was created in and works **only on that zone's host**. On the other host it is refused with `voice_not_found`. Cloned voices expire 60 days after they were created or their biometric consent was last renewed. Only **before** expiry can the owner renew it, by sending `extend_biometric_consent: true` with the voice. An expired voice cannot be renewed (`voice_expired`): create it again from a new consented recording, which gives it a new ID. Delete one of your voices with `DELETE /v1/voices/{voice_id}` on its zone's TTS host (API key; returns `204`).

### Languages

`language` takes the full English name: `english` (default), `spanish`, `german`, `italian`, `portuguese` or `french`. Case-insensitive. The API does not detect the language of the text: set `language` to match it.

> **Crucial Rule:** Always specify the voice with `voice_id` (e.g. `voice_id="aai-kyla"`). The `voice` parameter is retired. The HTTP API refuses it with `422 invalid_parameter`, the WebSocket closes `3006`, and `TTSConfig` raises a validation error. A bare name in `voice_id` (`voice_id="jane"`) is read as one of your own voices' slugs and refused with `voice_not_found`.

---

## HTTP Request Parameters (`POST /v1/speech`)

Send a JSON object with the following fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `text` | string | **Required** | The text to speak, 1 to 5,000 characters. |
| `voice_id` | string | `"aai-jane"` | Voice identifier: a library slug (`"aai-alba"`) or a cloned voice's ID or slug. |
| `stream` | boolean | `true` | `true` streams the audio as it is generated; `false` buffers it until complete. |
| `language` | string | `english` (a cloned or catalog voice: its own) | `english`, `spanish`, `german`, `french`, `italian`, `portuguese` (case-insensitive). |
| `model_id` | string | The language's default model | Such as `assemblyai-tts-1`. |
| `sample_rate` | integer | `24000` | Output rate in Hz: `8000`, `16000`, `22050`, `24000`, `44100`, `48000`. |
| `encoding` | string | `"pcm_s16le"` | Codec: `"pcm_s16le"` (16-bit linear PCM), `"pcm_mulaw"` / `"mulaw"` (8-bit G.711 μ-law), `"pcm_alaw"` / `"alaw"` (8-bit G.711 A-law), or `"mp3"`. Opus, AAC and FLAC are refused. |
| `container` | string | `"raw"` | `"raw"` (headerless audio bytes) or `"wav"`. `wav` needs a `pcm_*` encoding (not MP3). |
| `bit_rate` | integer | `64000` | MP3 bit rate in bps: `32000`, `48000`, `64000`, `96000`, `128000` (max `64000` at 8 kHz). Only with `encoding="mp3"`. |
| `extend_biometric_consent` | boolean | `false` | Renews the 60-day biometric consent of the cloned voice in `voice_id`; the voice's owner only. |
| `word_boundaries` | boolean | `false` | `true` is refused on `/v1/speech`; use `/v1/speech/events` for word timings. |
| `speed` | number | none | Only `1` is accepted: there is no speed control. |

Unknown fields are ignored and listed in `X-TTS-Unknown-Params`, so check it for typos. A body field sent in the query string is refused.

### Word Timings (`POST /v1/speech/events`)

Takes the `/v1/speech` body with these differences, and answers `text/event-stream` with the audio and its word boundaries:

- `word_boundaries` defaults to `true`; `false` turns them off.
- `encoding` is `pcm_s16le`, `pcm_mulaw` or `pcm_alaw`: no `mp3`.
- `container` is `raw` only.
- `bit_rate` and `"stream": false` are refused (`422`).

### Output Format

The default output is **raw** mono signed 16-bit little-endian PCM at 24 kHz with no header (`Content-Type: audio/pcm;rate=24000;channels=1`), not a playable WAV file. Ask for `"container": "wav"` to get a file a player opens, or play raw PCM with `ffplay -f s16le -ar 24000 -ac 1 speech.pcm`. G.711 is `audio/PCMU` / `audio/PCMA`, and MP3 is `audio/mpeg`.

### Response Headers (`X-TTS-*`)

On a `200 OK` response, metadata is returned in response headers:

| Header | Description |
|--------|-------------|
| `X-Request-Id` | Unique ID for support and diagnostics. |
| `X-TTS-Region` | Region that synthesized the audio (e.g. `us-east-1`). |
| `X-TTS-Model` | Model used (e.g. `assemblyai-tts-1`). |
| `X-TTS-Voice-Id` | Active voice ID. |
| `X-TTS-Voice-Expires-At` | A cloned voice's expiry, in Unix seconds. |
| `X-TTS-Language` | Language used (e.g. `english`). |
| `X-TTS-Encoding` | Codec (e.g. `pcm_s16le`, `pcm_mulaw`). |
| `X-TTS-Sample-Rate` | Sample rate in Hz. |
| `X-TTS-Container` | Container format (`raw` or `wav`); absent with MP3. |
| `X-TTS-Bit-Rate` | MP3 bit rate, with MP3 only. |
| `X-TTS-Billed-Characters` | Total billed character count. |
| `X-TTS-Audio-Duration-Ms` | Audio length in milliseconds (buffered responses only). |
| `X-TTS-Unknown-Params` | Body fields the API did not recognize. |
| `X-Client-Request-Id` | Your `X-Client-Request-Id`, echoed. |

---

## WebSocket Protocol

Connect to `wss://tts.us.assemblyai.com/v1/ws` with these query parameters (all optional): `voice_id` (default `aai-jane`), `model_id`, `language`, `sample_rate`, `encoding` (`pcm_s16le`, `pcm_mulaw`, `pcm_alaw`; no MP3 or WAV on the WebSocket), `word_boundaries` (default `true`), `inactivity_timeout` (`5`–`120` seconds, default `120`), `extend_biometric_consent`, and `token`.

The socket opens before the server checks the credential and parameters: a failed check arrives as an `Error` frame and a close, and `Begin` arrives only once every check passes. Handle `Error` from the start, and send frames after `Begin`.

**Client frames** are JSON text objects with a `type`. A binary frame is refused.

| `type` | Effect |
|--------|--------|
| `Generate` | `{"type": "Generate", "text": "..."}` appends text to the current request. Texts are joined exactly as sent, so include the spaces. At most 2,000 characters per frame. |
| `Flush` | Concludes the current request: everything sent is spoken, then one `FlushDone` arrives, even with no text. Short text gets no audio until its `Flush` (or the `Terminate` that ends the session, which flushes what is left). |
| `Cancel` | Barge-in: stops the request in flight and drops queued requests and unflushed text. The server answers `Cancelled`, and the session stays open for the next request. |
| `KeepAlive` | Restarts the inactivity timeout. |
| `Terminate` | Ends the session cleanly; the server answers `Termination` and closes `1000`. |

**Server frames**:

| `type` | Fields |
|--------|--------|
| `Begin` | `id`, `expires_at`, `configuration` (sent first) |
| `Audio` | `audio` (**base64** of raw mono codec bytes with no header: 16-bit little-endian PCM for `pcm_s16le`, 8-bit G.711 otherwise; in JSON, not a binary frame), `flush_id` |
| `FlushDone` | `flush_id`, `audio_duration_ms` |
| `WordBoundaries` | `flush_id`, `audio_start_ms`, `words` (each `{word, start, end, confidence}`) |
| `Cancelled` | `audio_duration_seconds` |
| `Termination` | `session_duration_seconds`, `total_input_char_length`, `audio_duration_seconds`, `voice_expires_at` |
| `Error` | `error_code`, `error`, `error_type`, `retryable`, `param`, `retry_after_seconds` |

**Close codes**:

- `1000`: clean end after `Terminate`.
- `1008`: credential refused.
- `1011`: the credential or the account's biometric terms could not be checked (`auth_unavailable`, retryable), or a ping went unanswered.
- `1012`: the server is restarting (`service_restart`, retryable).
- `3005`: server-side failure (retryable).
- `3006`: bad input (parameter, frame, voice or language), and the inactivity timeout.
- `3008`: the session reached `expires_at`.
- `3009`: too many new sessions this minute.
- `3010`: input sent too fast.
- `3011`: audio not read fast enough.
- `3012`: voice not found, expired or blocked.
- `3014`: cloned voice not paired with the model, or `model_id` names a retired model (`model_retired`).

Every close the server initiates is preceded by an `Error` frame: branch on its `error_type` and `retryable`. Closes from the WebSocket layer carry none: `1009` (message over 1 MiB), the keepalive `1011`, `1002` (protocol error), `1006` (connection dropped) and `1007` (text not UTF-8). Retry `1011`, `1012`, `3005` and `3009` with exponential backoff, waiting at least `retry_after_seconds` when set.

### Limits

Defaults that may change; a session reports its own in `Begin.configuration.limits`.

| Limit | WebSocket | HTTP |
|-------|-----------|------|
| Text | 2,000 characters per `Generate` | 5,000 characters per request |
| Duration | 3,600 s per session (`Begin.expires_at`; a temporary token can shorten it), then `3008` | 600 s per request |
| Idle | 120 s without a frame either way, then `3006` (send `KeepAlive`) | — |
| Text pacing | About 100 characters/s sustained after the first 1,500; at most 8,000 characters sent but not yet synthesized, else `3010` | — |
| Control frames | 20 per second sustained, else `3010` | — |
| Rate | New sessions per minute: 5 on a free plan, 100 or more on a paid plan (grows with use), else `3009` | Requests per minute: 50 free, 1,000 or more paid |

The US and EU hosts count separately. Keep one socket open for many requests rather than one per utterance: every connection counts as a new session start, reconnects included.

---

## OpenAI-Compatible Route

`POST /v1/openai/audio/speech` takes OpenAI's create-speech request, so OpenAI SDKs and tools built on them work by setting the base URL to `https://tts.us.assemblyai.com/v1/openai` (or the EU host) with your AssemblyAI API key:

```bash
curl https://tts.us.assemblyai.com/v1/openai/audio/speech \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "assemblyai-tts-en", "voice": "aai-kyla", "input": "Hello from AssemblyAI.", "response_format": "wav"}' \
  --output hello.wav
```

- `model`: `assemblyai-tts-<code>` (`en`, `es`, `de`, `it`, `pt`, `fr`) picks the language's default model and the language.
- `voice`: an AssemblyAI slug (`aai-kyla`), a voice ID, or an OpenAI voice name, which maps to a built-in voice (`alloy` → `aai-jane`, `nova` → `aai-eve`, `shimmer` → `aai-alba`, …).
- `response_format`: `mp3` (default), `pcm`, `wav`, `mulaw` or `alaw`. `speed` must be `1`.

For LiveKit or Pipecat voice agents, start from the reference agents in `references/voice-agents.md`, which use AssemblyAI text-to-speech.

---

## Python SDK Reference (`assemblyai>=1.8.2`)

Requests go to `aai.settings.tts_base_url` (`https://tts.us.assemblyai.com` by default; set `https://tts.eu.assemblyai.com` for the EU zone). The key comes from `aai.settings.api_key`, or pass it per client: `aai.TextToSpeech(api_key=...)`, `aai.TTSSession(config, api_key=...)`.

### 1. Buffered Synthesis (`synthesize`)

Returns the complete audio bytes in `response.audio` as a `bytes` object:

```python
import assemblyai as aai

aai.settings.api_key = "YOUR_API_KEY"

tts = aai.TextToSpeech()

# Generate a WAV file with Kyla, the recommended voice
config = aai.TTSConfig(
    voice_id="aai-kyla",
    container=aai.TTSContainer.wav,
    sample_rate=24000,
)
response = tts.synthesize("Hello from AssemblyAI Text-to-Speech!", config=config)

with open("output.wav", "wb") as f:
    f.write(response.audio)

print(f"Generated {response.audio_duration_ms}ms of audio ({response.billed_characters} chars)")
```

A per-call `config` replaces the instance's default config whole, so repeat `voice_id` in it.

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

Ideal for voice agents, LLM pipelines, and conversational interfaces. Open it with `with`: entering connects and waits for `Begin`; leaving sends `Terminate` and waits for the `Termination` summary. (`connect()` and `close()` also exist, but `close()` drops in-flight audio without `Terminate`.)

```python
import assemblyai as aai

aai.settings.api_key = "YOUR_API_KEY"

with aai.TTSSession(config=aai.TTSConfig(voice_id="aai-alba")) as session:
    # speak() sends one text, flushes it, and yields its audio
    for chunk in session.speak("How can I assist you today?"):
        pass
```

A session streams raw PCM or G.711: `TTSConfig` with `container="wav"` or `bit_rate` raises `ValueError` here. The SDK turns `WordBoundaries` frames off by default; pass `word_boundaries=True` to `TTSSession` to receive them.

### 4. Pipelining LLM Tokens & Barge-in (`generate`, `flush`, `cancel`)

For ultra-low latency voice agents where text streams token-by-token from an LLM:

```python
import assemblyai as aai

aai.settings.api_key = "YOUR_API_KEY"


def user_started_speaking() -> bool:
    return False  # Wire this to your STT turn detection


audio = bytearray()

with aai.TTSSession(config=aai.TTSConfig(voice_id="aai-kyla")) as session:
    # Stream text in chunks as the LLM generates them; include the spaces
    for token in ["I can help ", "you find ", "your order details."]:
        session.generate(token)
    flush_id = session.flush()  # Concludes the request and returns its id

    for chunk in session.audio(flush_id):
        if user_started_speaking():
            session.cancel()  # Barge-in: stop this request and drop anything queued
            break
        audio.extend(chunk)
```

Audio chunks are `bytes`. The session reads frames on its own thread, so `generate()`, `flush()` and `cancel()` can be called from another thread, and the session stays open after `cancel()` for the next reply. Read a flushed request's audio with `session.audio(flush_id)`, using the id `flush()` returned. `audio()` with no id reads the request still being written: call it that way only from another thread while `generate()` is still sending. After `flush()`, it waits for a request that never comes. Between replies further apart than the 120 s idle timeout, call `session.keep_alive()`.

### 5. Async Support (`AsyncTextToSpeech`, `AsyncTTSSession`)

```python
import asyncio

import assemblyai as aai

aai.settings.api_key = "YOUR_API_KEY"


async def main():
    async with aai.AsyncTextToSpeech() as async_tts:
        response = await async_tts.synthesize("Synthesized asynchronously.")

    async with aai.AsyncTTSSession(config=aai.TTSConfig(voice_id="aai-kyla")) as async_session:
        async for chunk in async_session.speak("Speaking over async WebSocket."):
            pass


asyncio.run(main())
```

---

## JavaScript / Node.js SDK Reference (`assemblyai@^4.42.0`)

```typescript
import { AssemblyAI } from "assemblyai";

const client = new AssemblyAI({
  apiKey: "YOUR_API_KEY",
  // ttsBaseUrl: "https://tts.eu.assemblyai.com", // EU data zone
});

// 1. Buffered synthesis (request fields are snake_case)
const response = await client.tts.synthesize({
  text: "Hello from the Node.js SDK!",
  voice_id: "aai-kyla",
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

// 3. WebSocket session (session params are camelCase)
const session = client.tts.session({ voiceId: "aai-michael" });
await session.connect();

for await (const chunk of session.speak("WebSocket speech synthesis.")) {
  // handle audio chunk
}

await session.close();

// 4. Temporary token for a browser session (server-side)
const token = await client.tts.createTemporaryToken({ expires_in_seconds: 60 });
```

Audio chunks are `Uint8Array`. Session params also take `language`, `sampleRate` and `encoding`; `session.keepAlive()` restarts the idle timeout. Failures throw `TextToSpeechError` (`errorCode`, `status`, `param`, `retryable`, `retryAfter`, `requestId`, `closeCode`, `body`), exported from `"assemblyai"`.

---

## Error Handling

Every API refusal raises `TTSError` (a rejected key included, as `401`), which contains the machine-readable error envelope:

| Attribute | Type | Description |
|-----------|------|-------------|
| `str(e)` | string | Human-readable explanation (there is no `.message` attribute). |
| `status_code` | int \| None | HTTP status (`None` on a WebSocket session). |
| `error_code` | string \| None | Stable code to branch on: `invalid_parameter`, `voice_not_found`, `biometric_terms_not_accepted`, `rate_limited`, `at_capacity`, `auth_unavailable`, … |
| `retryable` | bool \| None | `true` if retrying with the same parameters may succeed. |
| `retry_after` | int \| None | Backoff recommendation in seconds (from `Retry-After`). |
| `request_id` | string \| None | Request UUID to quote when contacting AssemblyAI support (the session id on a WebSocket). |
| `param` | string \| None | Faulty parameter name. |
| `errors` | list \| None | Every failing field of an `invalid_parameter` refusal. |
| `body` | dict \| None | The raw error envelope; on a WebSocket session `body["close_code"]` is the close code. |

`aai.TTSError` and `from assemblyai import TTSError` are the same class.

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
        print(f"Fatal error ({e.error_code}): {e}")
```

Without an SDK, an HTTP error before the first audio is a status with this JSON body (branch on `code`, not `message`):

```json
{
  "code": "invalid_parameter",
  "message": "sample_rate: must be given at most once (given 2 times)",
  "param": "sample_rate",
  "request_id": "0199c6f1-2d0b-7c3e-9a41-5b6f0e1d2c3a",
  "errors": [{ "message": "must be given at most once (given 2 times)", "param": "sample_rate" }],
  "retryable": false,
  "retry_after_seconds": null,
  "error": "sample_rate: must be given at most once (given 2 times)"
}
```

A streamed response cut after its first audio raises `TTSError` with `status_code` `200`, no `error_code` and `retryable` `True`: retry the whole request.

---

## Common Mistakes

| Mistake | What Happens | Fix |
|---------|--------------|-----|
| Using `voice: "aai-kyla"` | `422 invalid_parameter` (HTTP), close `3006` (WebSocket), validation error in `TTSConfig` | Use `voice_id="aai-kyla"` (or `TTSConfig(voice_id=...)`) |
| Using a bare voice name (`jane`) as `voice_id` | `voice_not_found` | Use the library slug, `aai-jane` |
| Calling `https://api.assemblyai.com` for TTS | `404 Not Found` | Use the dedicated TTS host: `https://tts.us.assemblyai.com` |
| Using a cloned voice on the other zone's host | `voice_not_found` | Call the host of the zone the voice was created in |
| Setting `container="wav"` with `encoding="mp3"` | Rejected with validation error | WAV container is only supported for PCM and G.711 codecs |
| Saving the default output as `.wav` | File has no header and won't play | Default is raw PCM; set `container="wav"` or save as `.pcm` |
| Putting private API key in frontend app | Security risk | Mint a temporary token with `GET https://token.assemblyai.com/v1/token?product=tts&expires_in_seconds=60` |
| Minting a token with `POST` and a JSON body, or without `product=tts` | Refused (`422` when a query parameter is missing) | `GET` with `product=tts` and `expires_in_seconds` in the query string |
| Forgetting to call `session.flush()` after `session.generate(...)` | Short text is not spoken until the session ends (`Terminate`, sent when the `with` block exits, flushes it), so the reply arrives late | Call `session.flush()` as soon as a reply's text is complete |
| `session.audio()` with no `flush_id` after `flush()` | Hangs until the session ends | `session.audio(session.flush())`, or `session.speak(text)` |
| One `Generate` over 2,000 characters | Close `3006` | Split the text across `Generate` frames |
| Trying to ingest URLs | TTS takes text in, returns speech out | Provide the text string in the `text` parameter |
