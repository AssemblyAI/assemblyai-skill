# AssemblyAI Streaming (Real-Time) Speech-to-Text Reference

## Streaming v3 Protocol (Current)

### Endpoints

- **Default (edge-routed):** `wss://streaming.assemblyai.com/v3/ws` — auto-routes to nearest region
- **EU region:** `wss://streaming.eu.assemblyai.com/v3/ws` (AWS eu-north-1, Stockholm; moved from eu-west-1 Ireland in March 2026 — endpoint host unchanged)
- **US region:** `wss://streaming.us.assemblyai.com/v3/ws` (AWS us-west-2 Oregon / us-east-1 Virginia)

### Authentication

Connect via query parameter: `?token=API_KEY` or use a temporary token (see Temporary Token Authentication below).

### Connection Query Parameters

For new realtime/streaming code, use **`speech_model=universal-3-5-pro`** by default. The raw API parameter is optional and defaults to `universal-3-5-pro`; set it explicitly when pinning behavior or using an SDK that requires the field.

| Parameter | Description |
|-----------|-------------|
| `speech_model` | **Optional at the raw API layer; default `universal-3-5-pro`.** Other current models: `universal-streaming-english`, `universal-streaming-multilingual`. The streaming spec `speech_model` enum now lists only these three. Two models are **legacy** — removed from the model picker and the spec enum but still seen in older code: `u3-rt-pro` (Universal-3 Pro Streaming, removed July 2026, superseded by `universal-3-5-pro`) and `whisper-rt` (99+ languages, removed June 2026, still functional via `speech_model=whisper-rt` for broadest language coverage). New integrations should use `universal-3-5-pro`. |
| `mode` | **universal-3-5-pro only.** Accuracy/latency tradeoff: `min_latency` (fastest time-to-text), `balanced` (**default** — best for voice agents), or `max_accuracy` (highest accuracy, for scribes/post-call). Sets the per-mode defaults for `min_turn_silence`, `max_turn_silence`, `interruption_delay`, `continuous_partials`, and `vad_threshold`. Set at connection time and updatable mid-stream via `UpdateConfiguration`. |
| `sample_rate` | Audio sample rate in Hz (e.g., 16000) |
| `encoding` | Audio encoding, default `pcm_s16le`. Raw PCM: `pcm_s16le` or `pcm_mulaw`. **Opus (added June 2026):** `opus` (raw Opus packets — each binary WebSocket message must contain exactly one packet) or `ogg_opus` (Ogg-encapsulated Opus stream, as produced by ffmpeg/gstreamer/opusenc/browser MediaRecorder — binary messages can be arbitrary chunks). **AAC (added July 2026):** `aac` (ADTS AAC stream, decoded at the edge). For the compressed encodings `sample_rate` is optional/ignored (the stream is self-describing; SDK support in Python ≥0.64.26 / Node ≥4.35.4) — for PCM it remains required (recent SDKs throw at construction if missing). |
| `end_of_turn_confidence_threshold` | Confidence threshold for turn detection. Only affects Universal Streaming (English/Multilingual), not universal-3-5-pro. **Officially deprecated** — tune `min_turn_silence`/`max_turn_silence` instead. |
| `format_turns` | Set to `true` to enable formatted final transcripts with punctuation, casing, and inverse text normalization (dates, times, phone numbers). Also activates turn-level keyterm boosting for Universal Streaming models. **Does NOT control digit rendering** — numerals (e.g. "22") are a model behavior, and lexical number output (e.g. "twenty-two") is not supported in streaming. |
| `prompt` | **universal-3-5-pro only.** Max **1750 characters.** Natural-language *context about the audio* (domain, topic, scenario, conversation details) — **NOT** behavioral/formatting instructions. The transcription instruction (verbatim behavior, punctuation, formatting) is built in and managed by AssemblyAI; formatting or behavioral commands placed in `prompt` are not supported. **Complementary with `keyterms_prompt`** — use either or both together. If omitted, a built-in default prompt optimized for turn detection is used automatically. Recommended: test with no prompt first, then add context only for domain vocabulary the model gets wrong. |
| `keyterms_prompt` | JSON-encoded array of strings (up to 100 terms, max 50 chars each) to bias transcription (universal-3-5-pro and Universal Streaming). **Complementary with `prompt`** — both can be set together. When passing via URL query param, must be JSON.stringify'd: `keyterms_prompt=["term1","term2"]`. Costs additional $0.04/hr. |
| `inactivity_timeout` | Seconds of silence before session auto-closes |
| `speaker_labels` | Enable diarization (`true`/`false`) |
| `max_speakers` | Integer 1–10. A **hard cap** (strict limit, not a hint) on speaker labels — once reached, additional speakers are merged into the closest existing label rather than given a new one. Give a little headroom above the expected count; setting it too high causes over-splitting. Only used when `speaker_labels` is enabled. |
| `domain` | Set to `"medical-v1"` to enable Medical Mode (improves accuracy for medical terminology). Supported models: all streaming models. Supported languages: en, es, de, fr. |
| `redact_pii` | Enable real-time PII redaction. Default `false`. Only applies to **final turns**. See Streaming PII Redaction below. |
| `redact_pii_policies` | PII entity types to redact. Pass a comma-separated string (e.g. `person_name,phone_number`) over the raw WebSocket or an array via the SDK. Default: all. |
| `redact_pii_sub` | Replacement scheme: `hash` (default — replaces with `#` chars) or `entity_name` (replaces with `[ENTITY_TYPE]`). |
| `include_partial_turns` | Whether to include partial (non-final) turns. Defaults to `true` normally, but **`false` automatically** when `redact_pii` is `true` so unredacted text never reaches the client. |
| `filter_profanity` | Filter profanity from transcripts (replaces with `***`). Default `false`. |
| `interruption_delay` | **universal-3-5-pro only.** Integer milliseconds (0–1000). Default is **mode-dependent** (set by the `mode` preset), not a fixed value. How soon the first partial is emitted — lower = faster TTFT and earlier barge-in but more false interruptions; higher = more confident interruptions but slower partials. The server adds a **fixed 256ms** on top (`interruption_delay: 0` → 256ms effective, `500` → 756ms effective). |
| `continuous_partials` | **universal-3-5-pro only.** Boolean — **default `true`** (changed June 2026; previously `false`). Now defaults to `true` on both the API directly and the LiveKit plugin. When `true`, emits additional partial transcripts approximately every ~3 seconds during long turns, each covering the full turn transcript so far. The first early partial (timed by `interruption_delay`) is unaffected. When `speaker_labels` is enabled, continuous partials are disabled by default. Set `false` if you only want silence-based partials. |
| `agent_context` | **universal-3-5-pro only.** String (≤1750 chars per value). Your voice agent's most recent spoken reply (TTS text), used as context for the next user turn — see Context Carryover below. Set at connection time to seed an opening greeting, and/or update mid-stream via `UpdateConfiguration`. |
| `previous_context_n_turns` | **universal-3-5-pro only.** Integer, range 0–100 (server default currently `5`). Max number of prior conversation entries (finalized user transcripts plus any `agent_context` values) carried forward as context for each transcription. Set to `0` to disable automatic context carryover entirely. Most integrations leave this unset — see Context Carryover below. |
| `vad_threshold` | Float 0.0–1.0. Confidence threshold for classifying audio frames as silence — frames below this are considered silent. Increase in noisy environments to reduce false speech detection. Defaults: `0.2` on universal-3-5-pro (`0.5` when `speaker_labels` is enabled), `0.4` on Universal Streaming. |
| `voice_focus` | **universal-3-5-pro only.** Noise suppression that isolates the primary voice and suppresses background chatter, keyboard clicks, fan hum, and room echo before audio reaches the model. Set to `near-field` (headsets, handsets, close-talking mics) or `far-field` (conference rooms, laptop/drive-thru mics, distant capture). Omit to disable. Set as a connection parameter. |
| `voice_focus_threshold` | **universal-3-5-pro only.** Optional float `0.0`–`1.0` controlling how aggressively background audio is suppressed when `voice_focus` is set — higher = more aggressive. |
| `language_codes` | **universal-3-5-pro only.** Optional **list** of ISO 639-1 codes, max **10** per session (the singular `language_code` connect param is deprecated but still accepted, read as a one-element list). Steers output toward the given languages on a per-token basis while still allowing native code-switching among them — it biases, it doesn't lock. Pass the languages you expect (e.g. `["en", "es"]`), or a single-element list (e.g. `["es"]`) for a monolingual session. When unset, no steering is applied and the model code-switches natively across all its supported languages. **Updatable mid-stream** via `UpdateConfiguration` — takes effect from the next turn; send `[]` to clear steering. Distinct from `language_detection` (which only reports the detected language). Accepted codes: en, es, fr, de, it, pt, tr, nl, sv, no, da, fi, hi, vi, ar, he, ja, zh, plus **ru and ko (added July 2026)**. |
| `language_detection` | **universal-3-5-pro and universal-streaming-multilingual only.** Boolean (default `false`). When `true`, each `Turn` message includes the detected `language_code` and `language_confidence`. universal-3-5-pro natively code-switches without this — use it only when you need the per-turn language reported. |
| `llm_gateway` | JSON-stringified LLM Gateway config — triggers LLM analysis on each completed turn, results delivered as `LLMGatewayResponse` messages |
| `session_heartbeat` | Boolean, opt-in (added July 2026). When `true`, the server emits periodic `Heartbeat` messages with session ingest stats — use them to detect pacing problems and dead sessions. Supported on universal-3-5-pro and Universal Streaming English/Multilingual. SDK support: Python ≥0.64.32 / Node ≥4.36.4. |

### Messages Sent (Client to Server)

- **Audio:** Binary WebSocket frames containing raw audio data
- **UpdateConfiguration:** JSON message to change settings mid-stream (see Dynamic Configuration)
- **ForceEndpoint:** JSON message to force-end the current turn immediately
- **KeepAlive:** `{"type": "KeepAlive"}` — resets the `inactivity_timeout` timer. **Not required** unless you set `inactivity_timeout` and want to keep the session open during periods with no audio.
- **Terminate:** JSON message to gracefully close the session

### Messages Received (Server to Client)

- **Begin:** Session start confirmation, includes session `id`
- **Turn:** Transcript data with `transcript` text, `end_of_turn` boolean flag, and `words` array
- **SpeechStarted:** Voice Activity Detection (VAD) event indicating speech has begun (universal-3-5-pro only — use for barge-in detection)
- **SpeakerRevision:** Revised speaker labels at session close (only when `speaker_labels` is enabled). See Streaming Diarization below.
- **LLMGatewayResponse:** LLM analysis result for the completed turn (only present when `llm_gateway` connection parameter is set)
- **Heartbeat:** Periodic session stats (only when `session_heartbeat=true`): `total_audio_received_ms`, `total_duration_ms`, `realtime_factor` (windowed ingest rate — 1.0 means realtime; sustained values well above 1.0 mean you're sending faster than realtime and heading for a 3007), `max_speech_probability`
- **Termination:** Session end confirmation

### Buffer Size

Send audio in **50ms chunks**.

### Graceful Shutdown

A graceful shutdown requires sending an explicit terminate message:

```json
{"type": "Terminate"}
```

Wait for the `Termination` message from the server before closing the WebSocket connection.

### Session-Based Billing

Streaming is billed on **WebSocket-open duration per session**, and concurrent sessions accumulate billed time **in parallel**. A single call **dual-streamed under two separate session IDs** for 5 minutes bills as **10 minutes** of session time — opening a second session to transcribe the same audio (e.g. two languages, or a redundant feed) doubles the cost.

---

## Streaming Models

### universal-3-5-pro (recommended default)

- Next-generation flagship streaming model; use it by default in new realtime/streaming integrations
- 18 languages with native code-switching: EN, ES, DE, FR, PT, IT, TR, NL, SV, NO, DA, FI, HI, VI, AR, HE, JA, ZH
- Punctuation-based turn detection, promptable, and enhanced conversational-context features; supports `mode`, `prompt`, `keyterms_prompt`, `agent_context`, `language_codes`, and language detection
- The only U3-Pro-family streaming model still in the spec — supersedes the removed `u3-rt-pro`

### u3-rt-pro (legacy)

- Universal-3 Pro Streaming (6 languages: EN, ES, DE, FR, PT, IT)
- **Removed July 2026** from the streaming docs, model picker, and the `speech_model` spec enum; superseded by `universal-3-5-pro`, which offers more languages and improved prompting/context. New integrations should use `universal-3-5-pro`.

### universal-streaming-english

- English only (1 language)
- Confidence-based turn detection

### universal-streaming-multilingual

- Supports 6 languages
- Per-utterance language detection

### whisper-rt (legacy)

- Supports 99+ languages
- Auto-detect language only (no manual language selection)
- Includes non-speech tags: `[Silence]`, `[Music]`
- **Legacy** as of June 2026: removed from the public model picker, model-selection table, and the streaming spec `speech_model` enums. The dedicated docs page still exists and the model still works via `speech_model=whisper-rt`, but new integrations should prefer `universal-3-5-pro` unless you need 99+ language coverage.

---

## Turn Detection

### Universal-3.5 Pro

Uses **punctuation-based** turn detection (`.` `?` `!`). The `end_of_turn_confidence_threshold` parameter has **NO effect** on universal-3-5-pro. Turn-end timing is set by the `mode` preset and tuned via `min_turn_silence`/`max_turn_silence`. Defaults by mode: `min_turn_silence` 128ms (`min_latency`/`balanced`) or 800ms (`max_accuracy`); `max_turn_silence` 1536ms. With `speaker_labels` enabled, the diarization profile takes over instead (640/768ms — see Streaming Diarization below).

### Universal Streaming

Uses **confidence-based** turn detection. The `end_of_turn_confidence_threshold` defaults to `0.4` (Universal Streaming English/Multilingual only); `max_turn_silence` defaults to 1280ms.

### Entity Splitting Caveat

A low `min_turn_silence` value can split entities like phone numbers across turns. To avoid this, dynamically increase `min_turn_silence` to **1000ms** during entity collection (e.g., when a user is dictating a phone number or address).

---

## Dynamic Configuration (UpdateConfiguration)

Change settings mid-stream without reconnecting. Fields are model-dependent:

- **Universal Streaming:** `keyterms_prompt`, `min_turn_silence`, `max_turn_silence`
- **universal-3-5-pro:** `mode`, `prompt`, `keyterms_prompt`, `min_turn_silence`, `max_turn_silence`, `continuous_partials`, `vad_threshold`, `interruption_delay`, `agent_context`, `language_codes` (applies from the next turn; `[]` clears steering)

Send a JSON message:

```json
{
  "type": "UpdateConfiguration",
  "keyterms_prompt": ["AssemblyAI", "LeMUR"],
  "prompt": "The caller is discussing a billing issue.",
  "min_turn_silence": 500,
  "max_turn_silence": 1500,
  "vad_threshold": 0.4,
  "interruption_delay": 300
}
```

All fields are optional — include only the ones you want to change.

---

## ForceEndpoint

Force-end the current turn immediately by sending:

```json
{"type": "ForceEndpoint"}
```

This causes the server to finalize and emit the current turn with `end_of_turn: true`, even if the model has not detected a natural endpoint.

---

## Temporary Token Authentication

For browser-based applications, use temporary tokens to avoid exposing your API key to the client.

### Request

```
GET https://streaming.assemblyai.com/v3/token?expires_in_seconds=N
Authorization: API_KEY
```

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `expires_in_seconds` | Yes | Token expiry time, 1–600 seconds |
| `max_session_duration_seconds` | No | Max session length, 60–10800 seconds (default: 10800 / 3 hours) |

### Usage Notes

- Each temporary token is **one-time use** — it can only be used to open a single WebSocket session.
- Critical for browser-based apps to prevent API key exposure.
- Connect with: `wss://streaming.assemblyai.com/v3/ws?token=TEMP_TOKEN`

---

## Streaming PII Redaction

Real-time PII redaction in streaming sessions. Detected PII is replaced in **final turns only** before being sent to the client.

- Supported models: `universal-3-5-pro`, `universal-streaming-english`, `universal-streaming-multilingual`
- When `redact_pii=true`, `include_partial_turns` defaults to `false` automatically — partials would otherwise leak unredacted text
- Audio redaction is **not** available for streaming. For redacted audio files, use [pre-recorded PII redaction](https://www.assemblyai.com/docs/guardrails/pii-redaction) with `redact_pii_audio`
- Same policies as pre-recorded redaction (`person_name`, `phone_number`, `email_address`, `credit_card_number`, `us_social_security_number`, `date_of_birth`, etc.)

Example connection URL:

```
wss://streaming.assemblyai.com/v3/ws?speech_model=universal-3-5-pro&sample_rate=16000&format_turns=true&redact_pii=true&redact_pii_policies=person_name,phone_number,email_address&redact_pii_sub=entity_name
```

Example output with `entity_name` substitution:

```
Hi, my name is [PERSON_NAME] and you can reach me at [PHONE_NUMBER].
```

---

## Streaming Diarization

Enable speaker diarization by setting query parameters on the WebSocket URL:

- `speaker_labels=true` — enables diarization
- `max_speakers=N` — sets the maximum number of expected speakers

### Behavior

- Speaker labels are assigned as `"A"`, `"B"`, `"C"`, etc.
- Turns under approximately **1 second** in duration receive the label `"UNKNOWN"`.
- Accuracy improves over time within a session as the model accumulates more speaker data.
- Real-time labels can shift as more audio arrives — early turns in particular may be reassigned.

### Diarization turn-detection profile (universal-3-5-pro)

Enabling `speaker_labels: true` **replaces the `mode` preset** with a dedicated diarization profile — `min_latency`/`balanced`/`max_accuracy` have **no effect** while diarization is on, and no warning is returned. The profile:

- Caps turns at **10 seconds** (force-finalized; with `mode` presets the cap is 60s). A turn boundary is therefore **not** a speaker change — long monologues get split. Compare `speaker_label` across turns instead.
- Slows mid-turn partials from ~1s to **~3s** cadence; set `continuous_partials: true` to restore the ~1s cadence.
- Sets silence-before-turn-end defaults to **640ms min / 768ms max**, VAD onset/offset thresholds to 0.5/0.35, and disables VAD probability smoothing.

Explicitly-supplied `min_turn_silence`, `max_turn_silence`, `max_turn_duration`, `vad_threshold`, and `interruption_delay` are applied **on top of** the profile — defaults shift, your overrides win. For voice-agent-grade latency with speaker labels, override the individual turn params rather than relying on `mode`.

### Revised speaker labels (SpeakerRevision)

When the session ends, the server runs a final refinement pass over the whole conversation and emits a **single `SpeakerRevision` message** (when `speaker_labels` is enabled). It arrives **right before `Termination`**, after the client sends `Terminate`. (Streaming diarization itself is supported across current streaming models; the `SpeakerRevision` message is defined for universal-3-5-pro.)

- A session emits **zero or one** `SpeakerRevision` message.
- It contains a `revisions` array with **only the turns whose speaker labels changed** — unchanged turns are omitted.
- Each item: `turn_order` (matches the original `Turn`'s `turn_order`), `speaker_label` (corrected, string or null), and `words` (with corrected per-word `speaker`).
- **Text content and word timestamps are never changed** — only speaker assignments.
- Adds approximately **400ms** of latency at session close; does not affect the real-time labels already delivered.
- To apply: match each `turn_order` against the turn you already received and replace its `speaker_label` and per-word `speaker` values. Use the revised labels for the final, highest-quality transcript (persisting, post-call summaries, downstream LLMs).

```json
{
  "type": "SpeakerRevision",
  "revisions": [
    {
      "turn_order": 3,
      "speaker_label": "B",
      "words": [
        { "text": "Hello",  "start": 1200, "end": 1450, "speaker": "B" },
        { "text": "there.", "start": 1450, "end": 1780, "speaker": "B" }
      ]
    }
  ]
}
```

---

## Context Carryover (universal-3-5-pro)

universal-3-5-pro automatically carries prior **finalized** turns (`end_of_turn: true`) forward as context to improve accuracy on the next turn. This is **on by default** — no configuration required — and is per-session (closing the WebSocket clears it).

**Defaults:** context carryover enabled, up to **5** prior entries carried (controlled by `previous_context_n_turns`, server default `5`, range 0–100). Older entries drop first. Set `previous_context_n_turns: 0` at connection time to disable automatic context carryover entirely.

You can additionally pass your voice agent's spoken reply (TTS text) via **`agent_context`** so the model knows the question the user is about to answer — especially valuable for short replies (`"yes"`, `"7pm"`, a single name) and spelled-out entities (emails, account IDs). For example, after the agent asks `"What's your email address?"`, `agent_context` helps the model produce `"user@assemblyai.com"` instead of `"user at assemblyai dot com"`.

Two ways to set it:

- **At connection time** — pass `agent_context` as a query parameter to seed the opening greeting before the user speaks.
- **Mid-stream** — send `UpdateConfiguration` with `agent_context` after each agent reply.

```json
{ "type": "UpdateConfiguration", "agent_context": "Sure — what date would you like to book?" }
```

**Limits:** `universal-3-5-pro` only. Per-value cap 1750 chars (`agent_context` and `prompt`). Not billed separately (streaming is billed on session duration).

---

## Voice Focus (Noise Suppression, universal-3-5-pro)

Voice Focus isolates the primary voice and suppresses background chatter, keyboard clicks, fan hum, and room echo **before** the audio reaches the transcription model. Set the `voice_focus` connection parameter when you open the WebSocket. Pick the variant by how close the speaker is to the mic:

| Variant | Value | When to use |
|---------|-------|-------------|
| Near field | `near-field` | Headsets, handsets, and other close-talking microphones |
| Far field | `far-field` | Conference rooms, drive-thru speakers, laptop mics, other distant capture |

Optionally tune `voice_focus_threshold` (float `0.0`–`1.0`, default `0.7`) to control how aggressively background audio is suppressed — higher = more aggressive. Omit `voice_focus` to disable. universal-3-5-pro only.

```python
CONNECTION_PARAMS = {
    "sample_rate": 16000,
    "speech_model": "universal-3-5-pro",
    "voice_focus": "near-field",
}
```

---

## Streaming Webhooks

Configure webhooks by adding query parameters to the WebSocket URL:

| Parameter | Description |
|-----------|-------------|
| `webhook_url` | URL to receive the webhook POST |
| `webhook_auth_header_name` | Name of the auth header sent with the webhook |
| `webhook_auth_header_value` | Value of the auth header sent with the webhook |

The webhook fires **once** after the session ends, delivering all finalized turns from the session.

---

## Error Codes

| Code | Meaning |
|------|---------|
| **3005** | Session cancelled (server error) |
| **3006** | Invalid message type, invalid JSON/message, **or** session terminated due to inactivity (the `inactivity_timeout` you configured elapsed with no audio/messages — send `KeepAlive` to reset the timer) |
| **3007** | Input duration violation — audio chunks must be 50ms–1000ms, or audio was sent faster than real-time. Usually caused by replaying a pre-recorded file without pacing: send ~100ms chunks (`frames_per_chunk = sample_rate * 0.1`) at wall-clock pace |
| **3008** | Session expired — 3-hour maximum reached or temporary token expired |
| **3009** | Too many concurrent sessions |
| **1008** | Missing authorization or account issue (insufficient balance, account disabled, etc.) |
| **1009** | A single WebSocket message exceeded the server's **128 KB** read limit — chunk your audio smaller |
| **1011** | Internal error — an unexpected server-side error while *establishing* the connection (e.g. during auth). Retry; if it persists, contact support |
| **1000 / 1006** | Normal/abnormal closure — these arrive **without** an `Error` message frame, so `on_error` never fires; put cleanup/reconnect logic in `on_close` |

---

## Session Limits

- **Maximum session duration:** 3 hours
- **Audio chunk size:** Must be between 50ms and 1000ms
- **Pacing:** Audio cannot be sent faster than real-time

---

## v2 to v3 Migration

### URL Change

- **v2:** `wss://api.assemblyai.com/v2/realtime/ws`
- **v3:** `wss://streaming.assemblyai.com/v3/ws`

### Message Type Changes

| v2 | v3 |
|----|-----|
| `SessionBegins` | `Begin` |
| `PartialTranscript` / `FinalTranscript` | `Turn` |

### Field Name Changes

| v2 | v3 |
|----|-----|
| `message_type` | `type` |
| `session_id` | `id` |
| `text` | `transcript` |

### Buffer Size Change

- **v2:** 200ms chunks
- **v3:** 50ms chunks

---

## Voice Agent Integration Tips

### Recommended Silence Settings (Universal Streaming models)

| Profile | `min_turn_silence` | `max_turn_silence` | Use case |
|---------|-------------------|--------------------|----------|
| **Aggressive** | 160ms | 400ms | IVR, quick confirmations, yes/no |
| **Balanced** | 400ms | 1280ms | General voice agents (recommended default) |
| **Conservative** | 800ms | 3600ms | Healthcare, complex speech, long pauses |

### Additional Recommendations

- Use **16kHz** sample rate for best balance of quality and bandwidth.
- Align VAD (Voice Activity Detection) thresholds at **0.3** for consistent behavior between your application's VAD and AssemblyAI's streaming endpoint.
