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
| `speech_model` | **Optional at the raw API layer; default `universal-3-5-pro`.** Other models: `u3-rt-pro`, `universal-streaming-english`, `universal-streaming-multilingual`. `whisper-rt` (99+ languages) is **legacy** — removed from the public model picker and the streaming spec enums (June 2026) but still functional via `speech_model=whisper-rt` |
| `mode` | **universal-3-5-pro / u3-rt-pro only.** Accuracy/latency tradeoff: `min_latency` (fastest time-to-text), `balanced` (**default** — best for voice agents), or `max_accuracy` (highest accuracy, for scribes/post-call). Sets the per-mode defaults for `min_turn_silence`, `max_turn_silence`, `interruption_delay`, `continuous_partials`, and `vad_threshold`. Set at connection time and updatable mid-stream via `UpdateConfiguration`. |
| `sample_rate` | Audio sample rate in Hz (e.g., 16000) |
| `encoding` | Audio encoding: `pcm_s16le` or `pcm_mulaw` |
| `end_of_turn_confidence_threshold` | Confidence threshold for turn detection. Only affects Universal Streaming, not U3 Pro. **Officially deprecated** — tune `min_turn_silence`/`max_turn_silence` instead. |
| `format_turns` | Set to `true` to enable formatted final transcripts with punctuation, casing, and inverse text normalization (dates, times, phone numbers). Also activates turn-level keyterm boosting for Universal Streaming models. **Does NOT control digit rendering** — numerals (e.g. "22") are a model behavior, and lexical number output (e.g. "twenty-two") is not supported in streaming. |
| `prompt` | **universal-3-5-pro / u3-rt-pro only.** Natural-language *context about the audio* (domain, topic, scenario, conversation details) — **NOT** behavioral/formatting instructions. The transcription instruction (verbatim behavior, punctuation, formatting) is built in and managed by AssemblyAI; formatting or behavioral commands placed in `prompt` are not supported. **Complementary with `keyterms_prompt`** — use either or both together. If omitted, a built-in default prompt optimized for turn detection is used automatically. Recommended: test with no prompt first, then add context only for domain vocabulary the model gets wrong. |
| `keyterms_prompt` | JSON-encoded array of strings (up to 100 terms, max 50 chars each) to bias transcription (universal-3-5-pro, u3-rt-pro, and Universal Streaming). **Complementary with `prompt`** — both can be set together. When passing via URL query param, must be JSON.stringify'd: `keyterms_prompt=["term1","term2"]`. Costs additional $0.04/hr. |
| `inactivity_timeout` | Seconds of silence before session auto-closes |
| `speaker_labels` | Enable diarization (`true`/`false`) |
| `max_speakers` | Maximum number of speakers for diarization |
| `domain` | Set to `"medical-v1"` to enable Medical Mode (improves accuracy for medical terminology). Supported models: all streaming models. Supported languages: en, es, de, fr. |
| `redact_pii` | Enable real-time PII redaction. Default `false`. Only applies to **final turns**. See Streaming PII Redaction below. |
| `redact_pii_policies` | PII entity types to redact. Pass a comma-separated string (e.g. `person_name,phone_number`) over the raw WebSocket or an array via the SDK. Default: all. |
| `redact_pii_sub` | Replacement scheme: `hash` (default — replaces with `#` chars) or `entity_name` (replaces with `[ENTITY_TYPE]`). |
| `include_partial_turns` | Whether to include partial (non-final) turns. Defaults to `true` normally, but **`false` automatically** when `redact_pii` is `true` so unredacted text never reaches the client. |
| `filter_profanity` | Filter profanity from transcripts (replaces with `***`). Default `false`. |
| `interruption_delay` | **universal-3-5-pro / u3-rt-pro only.** Integer milliseconds (0–1000, default `500`). How soon the first partial is emitted — lower = faster TTFT and earlier barge-in but more false interruptions; higher = more confident interruptions but slower partials. The server adds a minimum of ~256–300ms on top (`interruption_delay: 0` → ~256–300ms effective, `500` → ~756–800ms effective). The LiveKit plugin keeps the API default of `500`. |
| `continuous_partials` | **universal-3-5-pro / u3-rt-pro only.** Boolean — **default `true`** (changed June 2026; previously `false`). Now defaults to `true` on both the API directly and the LiveKit plugin. When `true`, emits additional partial transcripts approximately every ~3 seconds during long turns, each covering the full turn transcript so far. The first early partial (at 750ms / your `interruption_delay`) is unaffected. Set `false` if you only want silence-based partials. |
| `agent_context` | **universal-3-5-pro / u3-rt-pro only.** String (≤~1500 chars). Your voice agent's most recent spoken reply (TTS text), used as context for the next user turn — see Context Carryover below. Set at connection time to seed an opening greeting, and/or update mid-stream via `UpdateConfiguration`. |
| `previous_context_n_turns` | **universal-3-5-pro / u3-rt-pro only.** Integer (default `3`). Max number of prior conversation entries (finalized user transcripts plus any `agent_context` values) carried forward as context for each transcription. Set to `0` to disable automatic context carryover entirely. Most integrations leave this at the default — see Context Carryover below. |
| `vad_threshold` | **universal-3-5-pro / u3-rt-pro only.** Float 0.0–1.0 (default `0.3`). Confidence threshold for classifying audio frames as silence. Increase in noisy environments to reduce false speech detection. |
| `voice_focus` | **universal-3-5-pro / u3-rt-pro only.** Noise suppression that isolates the primary voice and suppresses background chatter, keyboard clicks, fan hum, and room echo before audio reaches the model. Set to `near-field` (headsets, handsets, close-talking mics) or `far-field` (conference rooms, laptop/drive-thru mics, distant capture). Omit to disable. Set as a connection parameter. |
| `voice_focus_threshold` | **universal-3-5-pro / u3-rt-pro only.** Optional float `0.0`–`1.0` controlling how aggressively background audio is suppressed when `voice_focus` is set — higher = more aggressive. |
| `language_code` | **universal-3-5-pro / u3-rt-pro only.** Optional ISO 639-1 code that biases the model toward a single language when you know the session is monolingual (improves language accuracy). Omit to keep default multilingual code-switching. `universal-3-5-pro` supports en, es, de, fr, pt, it, tr, nl, sv, no, da, fi, hi, vi, ar, he, ja, zh; `u3-rt-pro` supports en, es, fr, de, it, pt. |
| `language_detection` | **universal-3-5-pro / u3-rt-pro only.** Boolean (default `false`). When `true`, each `Turn` message includes the detected `language_code` and `language_confidence`. U3 Pro-family models natively code-switch without this — use it only when you need the per-turn language reported. |
| `llm_gateway` | JSON-stringified LLM Gateway config — triggers LLM analysis on each completed turn, results delivered as `LLMGatewayResponse` messages |

### Messages Sent (Client to Server)

- **Audio:** Binary WebSocket frames containing raw audio data
- **UpdateConfiguration:** JSON message to change settings mid-stream (see Dynamic Configuration)
- **ForceEndpoint:** JSON message to force-end the current turn immediately
- **KeepAlive:** `{"type": "KeepAlive"}` — resets the `inactivity_timeout` timer. **Not required** unless you set `inactivity_timeout` and want to keep the session open during periods with no audio.
- **Terminate:** JSON message to gracefully close the session

### Messages Received (Server to Client)

- **Begin:** Session start confirmation, includes session `id`
- **Turn:** Transcript data with `transcript` text, `end_of_turn` boolean flag, and `words` array
- **SpeechStarted:** Voice Activity Detection (VAD) event indicating speech has begun (U3 Pro only — use for barge-in detection)
- **SpeakerRevision:** Revised speaker labels at session close (only when `speaker_labels` is enabled). See Streaming Diarization below.
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

### Session-Based Billing

Streaming is billed on **WebSocket-open duration per session**, and concurrent sessions accumulate billed time **in parallel**. A single call **dual-streamed under two separate session IDs** for 5 minutes bills as **10 minutes** of session time — opening a second session to transcribe the same audio (e.g. two languages, or a redundant feed) doubles the cost.

---

## Streaming Models

### universal-3-5-pro (recommended default)

- Next-generation flagship streaming model; use it by default in new realtime/streaming integrations
- More languages than u3-rt-pro: EN, ES, DE, FR, PT, IT, TR, NL, SV, NO, DA, FI, HI, VI, AR, HE, JA, ZH
- Improved prompting and enhanced conversational-context features; supports `mode`, `prompt`, `agent_context`, and language detection like u3-rt-pro

### u3-rt-pro

- Universal-3 Pro Streaming — use when you intentionally need Universal-3 Pro behavior
- 6 languages (EN, ES, DE, FR, PT, IT) with native code-switching
- Punctuation-based turn detection, promptable, supports the `mode` accuracy/latency tradeoff

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
- **universal-3-5-pro / u3-rt-pro:** `mode`, `prompt`, `keyterms_prompt`, `min_turn_silence`, `max_turn_silence`, `continuous_partials`, `vad_threshold`, `interruption_delay`, `agent_context`

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

- Supported models: `universal-3-5-pro`, `u3-rt-pro`, `universal-streaming-english`, `universal-streaming-multilingual`
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

### Revised speaker labels (SpeakerRevision)

When the session ends, the server runs a final refinement pass over the whole conversation and emits a **single `SpeakerRevision` message** (when `speaker_labels` is enabled). It arrives **right before `Termination`**, after the client sends `Terminate`. (Streaming diarization itself is supported across current streaming models; the `SpeakerRevision` message is defined in the Universal-3 Pro-family streaming message set.)

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

## Context Carryover (universal-3-5-pro / u3-rt-pro)

Universal-3 Pro-family streaming models automatically carry prior **finalized** turns (`end_of_turn: true`) forward as context to improve accuracy on the next turn. This is **on by default** — no configuration required — and is per-session (closing the WebSocket clears it).

**Defaults:** context carryover enabled, ~3 prior entries carried (controlled by `previous_context_n_turns`, default `3`), ~1500-character max context. Older entries drop first. Set `previous_context_n_turns: 0` at connection time to disable automatic context carryover entirely.

You can additionally pass your voice agent's spoken reply (TTS text) via **`agent_context`** so the model knows the question the user is about to answer — especially valuable for short replies (`"yes"`, `"7pm"`, a single name) and spelled-out entities (emails, account IDs). For example, after the agent asks `"What's your email address?"`, `agent_context` helps the model produce `"user@assemblyai.com"` instead of `"user at assemblyai dot com"`.

Two ways to set it:

- **At connection time** — pass `agent_context` as a query parameter to seed the opening greeting before the user speaks.
- **Mid-stream** — send `UpdateConfiguration` with `agent_context` after each agent reply.

```json
{ "type": "UpdateConfiguration", "agent_context": "Sure — what date would you like to book?" }
```

**Limits:** `universal-3-5-pro` or `u3-rt-pro` only. Per-value cap ~1500 chars. Not billed separately (streaming is billed on session duration).

---

## Voice Focus (Noise Suppression, universal-3-5-pro / u3-rt-pro)

Voice Focus isolates the primary voice and suppresses background chatter, keyboard clicks, fan hum, and room echo **before** the audio reaches the transcription model. Set the `voice_focus` connection parameter when you open the WebSocket. Pick the variant by how close the speaker is to the mic:

| Variant | Value | When to use |
|---------|-------|-------------|
| Near field | `near-field` | Headsets, handsets, and other close-talking microphones |
| Far field | `far-field` | Conference rooms, drive-thru speakers, laptop mics, other distant capture |

Optionally tune `voice_focus_threshold` (float `0.0`–`1.0`) to control how aggressively background audio is suppressed — higher = more aggressive. Omit `voice_focus` to disable. Universal-3 Pro-family streaming models only.

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
| **3007** | Input duration violation — audio chunks must be 50ms–1000ms, or audio was sent faster than real-time |
| **3008** | Session expired — 3-hour maximum reached or temporary token expired |
| **3009** | Too many concurrent sessions |
| **1008** | Missing authorization or account issue (insufficient balance, account disabled, etc.) |
| **1011** | Internal error — an unexpected server-side error while *establishing* the connection (e.g. during auth). Retry; if it persists, contact support |

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
