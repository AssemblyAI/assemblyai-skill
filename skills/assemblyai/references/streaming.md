# AssemblyAI Streaming (Real-Time) Speech-to-Text Reference

## Streaming v3 Protocol (Current)

### Endpoints

- **Default (edge-routed):** `wss://streaming.assemblyai.com/v3/ws` — auto-routes to nearest region
- **EU region:** `wss://streaming.eu.assemblyai.com/v3/ws` (AWS eu-north-1, Stockholm; moved from eu-west-1 Ireland in March 2026 — endpoint host unchanged)
- **US region:** `wss://streaming.us.assemblyai.com/v3/ws` (AWS us-west-2 Oregon / us-east-1 Virginia)

### Authentication

Connect via query parameter: `?token=API_KEY` or use a temporary token (see Temporary Token Authentication below).

### Connection Query Parameters

**`speech_model` is required** — there is no default model. Omitting it will cause the request to fail.

| Parameter | Description |
|-----------|-------------|
| `speech_model` | **Required.** Model to use: `u3-rt-pro`, `universal-streaming-english`, `universal-streaming-multilingual`, `whisper-rt` |
| `sample_rate` | Audio sample rate in Hz (e.g., 16000) |
| `encoding` | Audio encoding: `pcm_s16le` or `pcm_mulaw` |
| `end_of_turn_confidence_threshold` | Confidence threshold for turn detection (only affects Universal Streaming, not U3 Pro) |
| `format_turns` | Set to `true` to enable formatted final transcripts with punctuation, casing, and inverse text normalization (dates, times, phone numbers). Also activates turn-level keyterm boosting for Universal Streaming models. **Does NOT control digit rendering** — numerals (e.g. "22") are a model behavior, and lexical number output (e.g. "twenty-two") is not supported in streaming. |
| `prompt` | Natural language transcription instructions (u3-rt-pro only). Mutually exclusive with `keyterms_prompt`. If omitted, a built-in default prompt optimized for turn detection is used automatically. |
| `keyterms_prompt` | JSON-encoded array of strings (up to 100 terms, max 50 chars each) to bias transcription (u3-rt-pro and Universal Streaming). Mutually exclusive with `prompt`. When passing via URL query param, must be JSON.stringify'd: `keyterms_prompt=["term1","term2"]`. Costs additional $0.04/hr. |
| `inactivity_timeout` | Seconds of silence before session auto-closes |
| `speaker_labels` | Enable diarization (`true`/`false`) |
| `max_speakers` | Maximum number of speakers for diarization |
| `domain` | Set to `"medical-v1"` to enable Medical Mode (improves accuracy for medical terminology). Supported models: all streaming models. Supported languages: en, es, de, fr. |
| `redact_pii` | Enable real-time PII redaction. Default `false`. Only applies to **final turns**. See Streaming PII Redaction below. |
| `redact_pii_policies` | PII entity types to redact. Pass a comma-separated string (e.g. `person_name,phone_number`) over the raw WebSocket or an array via the SDK. Default: all. |
| `redact_pii_sub` | Replacement scheme: `hash` (default — replaces with `#` chars) or `entity_name` (replaces with `[ENTITY_TYPE]`). |
| `include_partial_turns` | Whether to include partial (non-final) turns. Defaults to `true` normally, but **`false` automatically** when `redact_pii` is `true` so unredacted text never reaches the client. |
| `filter_profanity` | Filter profanity from transcripts (replaces with `***`). Default `false`. |
| `interruption_delay` | **u3-rt-pro only.** Integer milliseconds (0–1000, default `500`). How soon the first partial is emitted — lower = faster TTFT and earlier barge-in but more false interruptions; higher = more confident interruptions but slower partials. Minimum effective turn duration is `300ms`. |
| `vad_threshold` | **u3-rt-pro only.** Float 0.0–1.0 (default `0.3`). Confidence threshold for classifying audio frames as silence. Increase in noisy environments to reduce false speech detection. |
| `llm_gateway` | JSON-stringified LLM Gateway config — triggers LLM analysis on each completed turn, results delivered as `LLMGatewayResponse` messages |

### Messages Sent (Client to Server)

- **Audio:** Binary WebSocket frames containing raw audio data
- **UpdateConfiguration:** JSON message to change settings mid-stream (see Dynamic Configuration)
- **ForceEndpoint:** JSON message to force-end the current turn immediately
- **Terminate:** JSON message to gracefully close the session

### Messages Received (Server to Client)

- **Begin:** Session start confirmation, includes session `id`
- **Turn:** Transcript data with `transcript` text, `end_of_turn` boolean flag, and `words` array
- **SpeechStarted:** Voice Activity Detection (VAD) event indicating speech has begun (U3 Pro only — use for barge-in detection)
- **LLMGatewayResponse:** LLM analysis result for the completed turn (only present when `llm_gateway` connection parameter is set)
- **Termination:** Session end confirmation

### Buffer Size

Send audio in **50ms chunks**.

### Graceful Shutdown

A graceful shutdown requires sending an explicit terminate message:

```json
{"type": "Terminate"}
```

Wait for the `Termination` message from the server before closing the WebSocket connection.

---

## Streaming Models

### universal-streaming-english

- English only (1 language)
- Confidence-based turn detection

### universal-streaming-multilingual

- Supports 6 languages
- Per-utterance language detection

### whisper-rt

- Supports 99+ languages
- Auto-detect language only (no manual language selection)
- Includes non-speech tags: `[Silence]`, `[Music]`

---

## Turn Detection

### U3 Pro

Uses **punctuation-based** turn detection (`.` `?` `!`). The `end_of_turn_confidence_threshold` parameter has **NO effect** on U3 Pro models.

### Universal Streaming

Uses **confidence-based** turn detection. The `end_of_turn_confidence_threshold` defaults to `0.4`.

### Entity Splitting Caveat

A low `min_turn_silence` value can split entities like phone numbers across turns. To avoid this, dynamically increase `min_turn_silence` to **1000ms** during entity collection (e.g., when a user is dictating a phone number or address).

---

## Dynamic Configuration (UpdateConfiguration)

Change settings mid-stream without reconnecting. Fields are model-dependent:

- **Universal Streaming:** `keyterms_prompt`, `min_turn_silence`, `max_turn_silence`
- **u3-rt-pro:** `prompt`, `keyterms_prompt`, `min_turn_silence`, `max_turn_silence`, `continuous_partials`, `vad_threshold`, `interruption_delay`

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

- Supported models: `u3-rt-pro`, `universal-streaming-english`, `universal-streaming-multilingual`
- When `redact_pii=true`, `include_partial_turns` defaults to `false` automatically — partials would otherwise leak unredacted text
- Audio redaction is **not** available for streaming. For redacted audio files, use [pre-recorded PII redaction](https://www.assemblyai.com/docs/guardrails/pii-redaction) with `redact_pii_audio`
- Same policies as pre-recorded redaction (`person_name`, `phone_number`, `email_address`, `credit_card_number`, `us_social_security_number`, `date_of_birth`, etc.)

Example connection URL:

```
wss://streaming.assemblyai.com/v3/ws?speech_model=u3-rt-pro&sample_rate=16000&format_turns=true&redact_pii=true&redact_pii_policies=person_name,phone_number,email_address&redact_pii_sub=entity_name
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
| **3006** | Invalid message type, invalid JSON, or invalid message |
| **3007** | Input duration violation — audio chunks must be 50ms–1000ms, or audio was sent faster than real-time |
| **3008** | Session expired — 3-hour maximum reached or temporary token expired |
| **3009** | Too many concurrent sessions |
| **1008** | Missing authorization or account issue |

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
