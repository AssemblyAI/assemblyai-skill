# AssemblyAI Streaming (Real-Time) Speech-to-Text Reference

## Streaming v3 Protocol (Current)

### Endpoints

- **Default (edge-routed):** `wss://streaming.assemblyai.com/v3/ws` — auto-routes to nearest region
- **EU data residency:** `wss://streaming.eu.assemblyai.com/v3/ws`. Data never leaves the EU; processed in AWS eu-central-1 (Frankfurt), eu-north-1 (Stockholm), eu-south-1 (Milan), eu-south-2 (Spain), eu-west-1 (Ireland), eu-west-3 (Paris)
- **US data residency:** `wss://streaming.us.assemblyai.com/v3/ws`. Data never leaves the US; processed in AWS us-east-1, us-east-2, us-west-1, us-west-2
- The default edge-routed endpoint may process in **any** of the US or EU regions, so use a data-zone host when residency matters

### Authentication

Server-side, send your API key in the `Authorization` header (raw key, no `Bearer`). Where headers can't be set (browsers), pass a temporary token as `?token=TEMP_TOKEN` (see Temporary Token Authentication below). Never put your permanent API key in a URL or client-side code.

Optional header `AssemblyAI-Version` pins the API version (defaults to the latest, currently `2025-05-12`; echoed back as `Begin.configuration.api_version`).

### Connection Query Parameters

For new realtime/streaming code, use **`speech_model=universal-3-6-pro`** (Universal-3.6 Pro Streaming, launched Sept 29, 2026). The raw API parameter is optional and defaults to `universal-3-6-pro`, but set it explicitly: the LiveKit/Pipecat plugins still default to `universal-3-5-pro`, and unrecognized or misspelled query params are **ignored, not rejected**, so check `Begin.configuration.model`.

Everything below marked **U3.6/3.5 Pro** works identically on `universal-3-6-pro` and `universal-3-5-pro`. Some API-spec descriptions still say "Universal-3.5 Pro Streaming only"; that's stale wording, and 3.6 Pro supports all of them.

| Parameter | Description |
|-----------|-------------|
| `speech_model` | **Optional at the raw API layer; default `universal-3-6-pro`.** Spec enum: `universal-3-6-pro`, `universal-3-5-pro` (previous flagship, still fully supported), `universal-streaming-english`, `universal-streaming-multilingual`. Two models are **legacy**, removed from the model picker and the spec enum but still seen in older code: `u3-rt-pro` (Universal-3 Pro Streaming, removed July 2026) and `whisper-rt` (99+ languages, removed June 2026, still functional via `speech_model=whisper-rt` for broadest language coverage). The SDK enums also contain `universal-3-6` (no `-pro`), which is not a documented model. New integrations should use `universal-3-6-pro`. |
| `mode` | **U3.6/3.5 Pro.** Accuracy/latency tradeoff: `min_latency` (fastest time-to-text), `balanced` (**default**, best for voice agents), or `max_accuracy` (highest accuracy, for scribes/post-call). Sets the defaults for `min_turn_silence`, `max_turn_silence`, and `interruption_delay` (see the preset table under Turn Detection); explicit params override the preset. Set at connection time and updatable mid-stream via raw `UpdateConfiguration`, which re-applies the whole preset. The Python/Node SDK update methods don't expose `mode`. |
| `sample_rate` | Audio sample rate in Hz, any integer 8000–96000 (default 16000). Ignored for `opus`/`ogg_opus`/`aac`. |
| `encoding` | Audio encoding, default `pcm_s16le`. Raw PCM: `pcm_s16le` or `pcm_mulaw`. **Opus (added June 2026):** `opus` (raw Opus packets — each binary WebSocket message must contain exactly one packet) or `ogg_opus` (Ogg-encapsulated Opus stream, as produced by ffmpeg/gstreamer/opusenc/browser MediaRecorder — binary messages can be arbitrary chunks). **AAC (added July 2026):** `aac` (ADTS AAC stream, decoded at the edge). For the compressed encodings `sample_rate` is optional/ignored (the stream is self-describing; SDK support in Python ≥0.64.26 / Node ≥4.35.4) — for PCM it remains required (recent SDKs throw at construction if missing). |
| `end_of_turn_confidence_threshold` | Confidence threshold for turn detection. Only affects Universal Streaming (English/Multilingual), not Universal-3.6/3.5 Pro. **Officially deprecated**: tune `min_turn_silence`/`max_turn_silence` instead. |
| `format_turns` | **Universal Streaming only.** No effect on Universal-3.6/3.5 Pro, whose finals are always formatted (`turn_is_formatted` matches `end_of_turn`). Set to `true` to enable formatted final transcripts with punctuation, casing, and inverse text normalization (dates, times, phone numbers). Also activates turn-level keyterm boosting for Universal Streaming models. **Does NOT control digit rendering** — numerals (e.g. "22") are a model behavior, and lexical number output (e.g. "twenty-two") is not supported in streaming. |
| `prompt` | **U3.6/3.5 Pro.** Max **1750 characters.** Natural-language *context about the audio* (domain, topic, scenario, conversation details) — **NOT** behavioral/formatting instructions. The transcription instruction (verbatim behavior, punctuation, formatting) is built in and managed by AssemblyAI; formatting or behavioral commands placed in `prompt` are not supported. **Complementary with `keyterms_prompt`** — use either or both together. If omitted, a built-in default prompt optimized for turn detection is used automatically. Recommended: test with no prompt first, then add context only for domain vocabulary the model gets wrong. |
| `keyterms_prompt` | JSON-encoded array of strings (up to 100 terms, max 50 chars each; more than 100 is an error) to bias transcription (all streaming models). **Complementary with `prompt`**: both can be set together. When passing via URL query param, must be JSON.stringify'd: `keyterms_prompt=["term1","term2"]`. **Included** in the Universal-3.6 Pro price; $0.04/hr add-on on Universal Streaming. |
| `inactivity_timeout` | Seconds (integer, 5–3600) without audio/messages before the session auto-closes. Unset = no inactivity timeout. |
| `speaker_labels` | Enable diarization (`true`/`false`). Adds `speaker_label` to each `Turn`, `speaker` to each final word, experimental `speaker_confidence` (turn + word), and `SpeakerRevision` messages. See Streaming Diarization below. |
| `speaker_labels_revision_interval_ms` | Integer ms of **audio** time between mid-session `SpeakerRevision` messages. `0`/unset (default) = only the final revision before `Termination`. Minimum **120000** (lower values are raised), recommended `300000`. The Node SDK changelog says values above 300000 are clamped to it, while one docs table says larger values are honored, so don't depend on intervals over 5 min. The first arrives after ~2 min of audio. Only with `speaker_labels`. SDK: Python ≥1.6.1 / Node ≥4.41.5 (`speakerLabelsRevisionIntervalMs`). |
| `max_speakers` | Integer 1–10. A **hard cap** (strict limit, not a hint) on speaker labels — once reached, additional speakers are merged into the closest existing label rather than given a new one. Give a little headroom above the expected count; setting it too high causes over-splitting. Only used when `speaker_labels` is enabled. |
| `domain` | Set to `"medical-v1"` to enable Medical Mode (improves accuracy for medical terminology). Supported models: all streaming models. Supported languages: en, es, de, fr. |
| `redact_pii` | Enable real-time PII redaction. Default `false`. Only applies to **final turns**. See Streaming PII Redaction below. |
| `redact_pii_policies` | PII entity types to redact. Pass a comma-separated string (e.g. `person_name,phone_number`) over the raw WebSocket or an array via the SDK. Default: all. |
| `redact_pii_sub` | Replacement scheme: `hash` (default — replaces with `#` chars) or `entity_name` (replaces with `[ENTITY_TYPE]`). |
| `include_partial_turns` | Whether to include partial (non-final) turns. Defaults to `true` normally, but **`false` automatically** when `redact_pii` is `true` so unredacted text never reaches the client. |
| `filter_profanity` | Filter profanity from transcripts (replaces with `***`). Default `false`. |
| `interruption_delay` | **U3.6/3.5 Pro.** Integer milliseconds (0–1000). Default is **mode-dependent** (`min_latency` 0, `balanced`/`max_accuracy` 500), not a fixed value. How soon the first partial is emitted — lower = faster TTFT and earlier barge-in but more false interruptions; higher = more confident interruptions but slower partials. The server adds a **fixed 256ms** on top (`interruption_delay: 0` → 256ms effective, `500` → 756ms effective). |
| `continuous_partials` | **U3.6/3.5 Pro.** Boolean, **default `true`** (changed June 2026). Controls mid-turn partial cadence during uninterrupted speech: ~**1s** when `true`, ~3s when `false`. Each partial covers the full turn transcript so far. The early partial (timed by `interruption_delay`) and pause partials are unaffected. Off by default when `speaker_labels` is enabled (so ~3s partials). No longer listed in the public API spec, but still accepted at connect time and by the SDKs/plugins. |
| `agent_context` | **U3.6/3.5 Pro.** String (≤1750 chars per value). Your voice agent's most recent spoken reply (TTS text), used as context for the next user turn — see Context Carryover below. Set at connection time to seed an opening greeting, and/or update mid-stream via `UpdateConfiguration`. |
| `previous_context_n_turns` | **U3.6/3.5 Pro.** Connect-time only. Integer, range 0–100 (server default currently `5`). **Not exposed by the Python/Node SDKs**; set it via the raw WebSocket URL, LiveKit, or Pipecat. Max number of prior conversation entries (finalized user transcripts plus any `agent_context` values) carried forward as context for each transcription. Set to `0` to disable automatic context carryover entirely. Most integrations leave this unset — see Context Carryover below. |
| `vad_threshold` | Float 0.0–1.0. Confidence threshold for classifying audio frames as silence — frames below this are considered silent. Increase in noisy environments to reduce false speech detection. Defaults: `0.2` on Universal-3.6/3.5 Pro in every `mode` (`0.5` when `speaker_labels` is enabled), `0.4` on Universal Streaming. |
| `voice_focus` | **U3.6/3.5 Pro.** Noise suppression that isolates the primary voice and suppresses background chatter, keyboard clicks, fan hum, and room echo before audio reaches the model. Set to `near-field` (headsets, handsets, close-talking mics) or `far-field` (conference rooms, laptop/drive-thru mics, distant capture). Omit to disable. Connection-time only. $0.10/hr add-on. |
| `voice_focus_threshold` | **U3.6/3.5 Pro.** Optional float `0.0`–`1.0` controlling how aggressively background audio is suppressed. Higher = more aggressive. Requires `voice_focus` (otherwise a validation error). Leave unset for the server default. |
| `language_codes` | **U3.6/3.5 Pro.** Optional **list** of ISO 639-1 codes, max **10** per session (the singular `language_code` connect param is deprecated but still accepted, read as a one-element list). Steers output toward the given languages on a per-token basis while still allowing native code-switching among them — it biases, it doesn't lock. Pass the languages you expect (e.g. `["en", "es"]`), or a single-element list (e.g. `["es"]`) for a monolingual session. When unset, no steering is applied and the model code-switches natively across all its supported languages. **Updatable mid-stream** via `UpdateConfiguration` — takes effect from the next turn; send `[]` to clear steering. Distinct from `language_detection` (which only reports the detected language). Accepted codes (Universal-3.6 Pro, 32): `af` `ar` `yue` `ca` `da` `nl` `en` `et` `fi` `fr` `gl` `de` `he` `hi` `it` `ja` `ko` `zh` `mr` `no` `nn` `fa` `pt` `ro` `ru` `es` `sv` `tr` `ur` `vi` `xh` `zu`. Universal-3.5 Pro is documented for 19 of them; `af yue et gl ko mr nn fa ro ru ur xh zu` are 3.6 Pro only. Neither SDK validates codes client-side. If you know the session's languages, set this: it improves accuracy on short or ambiguous turns. |
| `language_detection` | **U3.6/3.5 Pro and universal-streaming-multilingual.** Boolean (default `false`). When `true`, final `Turn` messages include the detected `language_code` and `language_confidence`. It only controls reporting: the Pro models code-switch natively without it, but you still need `true` to get `language_code` back. |
| `llm_gateway` | JSON-stringified LLM Gateway config — triggers LLM analysis on each completed turn, results delivered as `LLMGatewayResponse` messages |
| `session_heartbeat` | Boolean, opt-in (added July 2026). When `true`, the server emits a `Heartbeat` message every **5s of wall-clock time** (during speech and silence) with session ingest stats. Use them to detect pacing problems and dead sessions. Also toggleable mid-stream via `UpdateConfiguration`. All current streaming models. SDK support: Python ≥0.64.32 / Node ≥4.36.4. |

### Messages Sent (Client to Server)

- **Audio:** Binary WebSocket frames containing raw audio data
- **UpdateConfiguration:** JSON message to change settings mid-stream (see Dynamic Configuration)
- **ForceEndpoint:** JSON message to force-end the current turn immediately
- **KeepAlive:** `{"type": "KeepAlive"}` — resets the `inactivity_timeout` timer. **Not required** unless you set `inactivity_timeout` and want to keep the session open during periods with no audio.
- **Terminate:** JSON message to gracefully close the session

### Messages Received (Server to Client)

- **Begin:** Session start confirmation: `id`, `expires_at`, and `configuration`, an echo of what the server applied (`model`, `mode`, `api_version`, `speaker_labels`, `redact_pii`, `filter_profanity`, `domain`, `voice_focus`; unset optionals are `null`). **Assert `configuration.model` matches the `speech_model` you requested**, since unknown/misspelled query params are silently ignored.
- **Turn:** `turn_order`, `transcript`, `end_of_turn`, `turn_is_formatted`, `end_of_turn_confidence` (on U3.6/3.5 Pro: `1.0` on finals, `0.0` otherwise), `words[{text, start, end, confidence, word_is_final}]`, plus `utterance` (the finalized text on `end_of_turn` messages, `""` on partials). Optional: `language_code`/`language_confidence` (with `language_detection`), and `speaker_label`, per-word `speaker`, and experimental `speaker_confidence` (with `speaker_labels`). Each `Turn` re-transcribes the whole turn, so **replace** the rendered text rather than appending.
- **SpeechStarted:** `{timestamp, confidence}`, sent once per turn right before its first `Turn` and only when the model actually produces a transcript, so background noise alone doesn't trigger it (U3.6/3.5 Pro; use it for barge-in detection)
- **SpeakerRevision:** Revised speaker labels for earlier turns: at most one right before `Termination` (only if some label changed), plus mid-session ones when `speaker_labels_revision_interval_ms` is set (only when `speaker_labels` is enabled). See Streaming Diarization below.
- **LLMGatewayResponse:** LLM analysis result for the completed turn (only present when `llm_gateway` connection parameter is set)
- **Heartbeat:** Periodic session stats (only when `session_heartbeat=true`): `total_audio_received_ms`, `total_duration_ms`, `realtime_factor` (windowed ingest rate — 1.0 means realtime; sustained values well above 1.0 mean you're sending faster than realtime and heading for a 3007), `max_speech_probability`
- **Termination:** Session end confirmation with `audio_duration_seconds` and `session_duration_seconds`

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

### universal-3-6-pro (recommended default)

- Universal-3.6 Pro Streaming, launched **Sept 29, 2026**. The streaming flagship and the server default when `speech_model` is omitted
- **32 languages** with native (mid-sentence) code-switching: Afrikaans, Arabic, Cantonese, Catalan, Danish, Dutch, English, Estonian, Finnish, French, Galician, German, Hebrew, Hindi, Italian, Japanese, Korean, Mandarin, Marathi, Norwegian, Norwegian Nynorsk, Persian, Portuguese, Romanian, Russian, Spanish, Swedish, Turkish, Urdu, Vietnamese, Xhosa, Zulu
- **Drop-in replacement for `universal-3-5-pro`**: same connection params, `UpdateConfiguration` fields, messages, and features (`mode`, `prompt`, `keyterms_prompt`, `agent_context`/context carryover, `language_codes`, language detection, voice focus, diarization, Medical Mode, PII redaction). Migrating is just the `speech_model` string
- **Streaming-only.** There is no Universal-3.6 Pro for pre-recorded (`/v2/transcript`) or Sync STT, so use `universal-3-5-pro` there. Dictation has no model selector
- $0.45/hr, keyterms included. Published benchmark figures are still for 3.5 Pro
- Integrations: LiveKit `livekit-agents` **1.8.0+** (LiveKit Inference `stt="assemblyai/universal-3-6-pro"` needs **1.8.3+**), `pipecat-ai` **1.9.0+** (1.11.0+ for all 32 `language_codes`). Both plugins still **default to `universal-3-5-pro`**, so pass the model explicitly. Self-hosted streaming serves 3.5 Pro only

### universal-3-5-pro (previous flagship)

- Still **fully supported**, with the same features and parameters as 3.6 Pro
- Documented for 19 languages: EN, ES, DE, FR, PT, IT, TR, NL, SV, NO, DA, FI, HI, VI, AR, HE, JA, ZH, CA
- Keep it only for integrations deliberately pinned to it (or self-hosted); new code should use `universal-3-6-pro`

### u3-rt-pro (legacy)

- Universal-3 Pro Streaming (6 languages: EN, ES, DE, FR, PT, IT)
- **Removed July 2026** from the streaming docs, model picker, and the `speech_model` spec enum; superseded by the Universal-3.5/3.6 Pro models. New integrations should use `universal-3-6-pro`.

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
- **Legacy** as of June 2026: removed from the public model picker, model-selection table, and the streaming spec `speech_model` enums. The dedicated docs page still exists and the model still works via `speech_model=whisper-rt`, but new integrations should prefer `universal-3-6-pro` (32 languages) unless you need 99+ language coverage.

---

## Turn Detection

### Universal-3.6 Pro / Universal-3.5 Pro

Turn ends are **content-based**, not confidence-based. After `min_turn_silence` of silence the model checks whether the turn reads as complete (terminal punctuation `.` `?` `!`). If it does, the turn ends. If not, a pause partial is emitted and the turn stays open until `max_turn_silence` forces it to end. `end_of_turn_confidence_threshold` has **NO effect**. Defaults come from the `mode` preset; any explicit param overrides the preset:

| `mode` | `min_turn_silence` | `max_turn_silence` | `interruption_delay` |
|--------|-------------------:|-------------------:|---------------------:|
| `min_latency` | 128ms | 640ms | 0 |
| `balanced` (default) | 128ms | 1280ms | 500 |
| `max_accuracy` | 512ms | 2560ms | 500 |

`max_accuracy` holds turns open longer (higher `min_turn_silence`), so mid-entity pauses in phone numbers, addresses, or card numbers don't end the turn, trading latency for accuracy. All presets use `vad_threshold` 0.2 and a 60s max turn duration. With `speaker_labels` enabled, the diarization profile replaces the preset (640/768ms; see Streaming Diarization below). `min_turn_silence` is clamped to 50–10000ms.

Partials come at three points: an **early partial** timed by `interruption_delay` (+256ms fixed), **pause partials** when a silence check finds the turn incomplete, and **continuous partials** about every 1s during uninterrupted speech (~3s with `continuous_partials: false` or diarization on).

### Universal Streaming

Uses **confidence-based** turn detection. The `end_of_turn_confidence_threshold` defaults to `0.4` (Universal Streaming English/Multilingual only); `max_turn_silence` defaults to 1280ms.

### Entity Splitting Caveat

A low `min_turn_silence` value can split entities like phone numbers across turns. To avoid this, dynamically increase `min_turn_silence` to **1000ms** during entity collection (e.g., when a user is dictating a phone number or address).

---

## Dynamic Configuration (UpdateConfiguration)

Change settings mid-stream without reconnecting. Fields are model-dependent:

- **Universal Streaming:** `keyterms_prompt`, `min_turn_silence`, `max_turn_silence`
- **Universal-3.6/3.5 Pro:** `mode` (re-applies that preset's defaults), `prompt` (`""` clears), `keyterms_prompt` (replaces the set; `[]` clears), `min_turn_silence`, `max_turn_silence`, `continuous_partials`, `vad_threshold`, `interruption_delay`, `agent_context`, `language_codes` (applies from the next turn; `[]` clears steering)
- **All models:** `session_heartbeat` (toggle `Heartbeat` messages)
- **Connect-time only:** `speech_model`, `sample_rate`, `encoding`, `previous_context_n_turns`, `voice_focus`/`voice_focus_threshold`, `speaker_labels`/`max_speakers`/`speaker_labels_revision_interval_ms`, `redact_pii*`, `domain`, `language_detection`

There is no acknowledgement message; changes apply to audio processed after the update. **SDK methods differ from the wire format:** Python uses `transcriber.set_params(RealTimeSessionParameters(...))`, and Node uses `transcriber.updateConfiguration({...})` with snake_case keys. Neither SDK's update type includes `mode` (see `python-sdk.md` / `js-sdk.md`).

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

- Supported models: `universal-3-6-pro`, `universal-3-5-pro`, `universal-streaming-english`, `universal-streaming-multilingual`. $0.12/hr add-on
- When `redact_pii=true`, `include_partial_turns` defaults to `false` automatically — partials would otherwise leak unredacted text
- Audio redaction is **not** available for streaming. For redacted audio files, use [pre-recorded PII redaction](https://www.assemblyai.com/docs/guardrails/pii-redaction) with `redact_pii_audio`
- Same policies as pre-recorded redaction (`person_name`, `phone_number`, `email_address`, `credit_card_number`, `us_social_security_number`, `date_of_birth`, etc.)

Example connection URL:

```
wss://streaming.assemblyai.com/v3/ws?speech_model=universal-3-6-pro&sample_rate=16000&redact_pii=true&redact_pii_policies=person_name,phone_number,email_address&redact_pii_sub=entity_name
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
- Turns under approximately **1 second** (and words not yet attributed) get the label **`"PENDING"`** (it replaced `"UNKNOWN"` in June 2026; the API spec's field descriptions still say `UNKNOWN`). `SpeakerRevision` resolves these by session end. Treat any non-letter label as unattributed.
- Per-word `speaker` may be absent on individual words even with diarization on. Fall back to the turn-level `speaker_label`.
- Accuracy improves over time within a session as the model accumulates more speaker data.
- Real-time labels can shift as more audio arrives — early turns in particular may be reassigned.

### Speaker confidence (experimental)

With `speaker_labels` on, final `Turn` messages carry a turn-level `speaker_confidence` and each final word carries its own (every word in a sentence shares one value). Scores run 0.0–1.0 but are **not calibrated probabilities**, so compare them relatively (e.g. flag a turn's label as shaky vs the session's other turns) and don't use absolute thresholds. The word-level field is **omitted** when unavailable (normal on a session's first words), and a turn-level `0.0` means "no score", not "wrong". `SpeakerRevision` carries no confidences, so discard a stored score when a revision changes that turn's label. Neither SDK types this field; read it from the raw message.

### Diarization turn-detection profile (Universal-3.6/3.5 Pro)

Enabling `speaker_labels: true` **replaces the `mode` preset** with a dedicated diarization profile — `min_latency`/`balanced`/`max_accuracy` have **no effect** while diarization is on, and no warning is returned. The profile:

- Caps turns at **10 seconds** (force-finalized; with `mode` presets the cap is 60s). A turn boundary is therefore **not** a speaker change — long monologues get split. Compare `speaker_label` across turns instead.
- Slows mid-turn partials from ~1s to **~3s** cadence; set `continuous_partials: true` to restore the ~1s cadence.
- Sets silence-before-turn-end defaults to **640ms min / 768ms max**, `vad_threshold` to 0.5, and `interruption_delay` to 500.

Explicitly-supplied `min_turn_silence`, `max_turn_silence`, `max_turn_duration`, `vad_threshold`, and `interruption_delay` are applied **on top of** the profile — defaults shift, your overrides win. For voice-agent-grade latency with speaker labels, override the individual turn params rather than relying on `mode`.

### Revised speaker labels (SpeakerRevision)

When `speaker_labels` is enabled, the server runs a refinement pass over the whole conversation at session end and emits a final **`SpeakerRevision` message right before `Termination`** (after the client sends `Terminate`) when any label changed. Set **`speaker_labels_revision_interval_ms`** to also receive revisions **mid-session**. The minimum is 120000ms of audio time, recommended `300000` (intervals over 300000 may be clamped), the first arrives after ~2 minutes of audio, and one is sent only when some earlier label actually changed. SDK support: Python ≥1.6.1, Node ≥4.41.5.

- Without the interval param: zero or one message, at session end. With it: possibly **many** messages.
- Each message is an **incremental delta**: a `revisions` array with **only the turns whose labels changed since the previous message**; unchanged turns are omitted and not re-sent. Apply messages **in arrival order; for a given `turn_order` the last one wins**.
- Each item: `turn_order` (matches the original `Turn`'s `turn_order`), `speaker_label` (corrected, string or null), and `words` (with corrected per-word `speaker`).
- **Text content and word timestamps are never changed** — only speaker assignments.
- The end-of-session pass adds approximately **400ms** of latency at session close; revisions never alter the real-time labels already delivered, so you apply them yourself.
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

## Context Carryover (Universal-3.6/3.5 Pro)

Universal-3.6 Pro and 3.5 Pro automatically carry prior **finalized** turns (`end_of_turn: true`) forward as context to improve accuracy on the next turn. This is **on by default** — no configuration required — and is per-session (closing the WebSocket clears it).

**Defaults:** context carryover enabled, up to **5** prior entries carried (controlled by `previous_context_n_turns`, server default `5`, range 0–100). Older entries drop first. Set `previous_context_n_turns: 0` at connection time to disable automatic context carryover entirely.

You can additionally pass your voice agent's spoken reply (TTS text) via **`agent_context`** so the model knows the question the user is about to answer — especially valuable for short replies (`"yes"`, `"7pm"`, a single name) and spelled-out entities (emails, account IDs). For example, after the agent asks `"What's your email address?"`, `agent_context` helps the model produce `"user@assemblyai.com"` instead of `"user at assemblyai dot com"`.

Two ways to set it:

- **At connection time** — pass `agent_context` as a query parameter to seed the opening greeting before the user speaks.
- **Mid-stream** — send `UpdateConfiguration` with `agent_context` after each agent reply.

```json
{ "type": "UpdateConfiguration", "agent_context": "Sure — what date would you like to book?" }
```

**Limits:** Universal-3.6/3.5 Pro only. Per-value cap 1750 chars (`agent_context` and `prompt`). Each `agent_context` you send is added to the carryover history as its own entry, interleaved with user turns, and counts against `previous_context_n_turns` (oldest entries drop first). So send each agent reply once, right after it's spoken. `previous_context_n_turns` is connect-time only and not in the Python/Node SDKs. Context carryover is included in the price (not billed separately).

---

## Voice Focus (Noise Suppression, Universal-3.6/3.5 Pro)

Voice Focus isolates the primary voice and suppresses background chatter, keyboard clicks, fan hum, and room echo **before** the audio reaches the transcription model. Set the `voice_focus` connection parameter when you open the WebSocket. Pick the variant by how close the speaker is to the mic:

| Variant | Value | When to use |
|---------|-------|-------------|
| Near field | `near-field` | Headsets, handsets, and other close-talking microphones |
| Far field | `far-field` | Conference rooms, drive-thru speakers, laptop mics, other distant capture |

Optionally tune `voice_focus_threshold` (float `0.0`–`1.0`; leave unset for the server default) to control how aggressively background audio is suppressed. Higher = more aggressive, and setting it without `voice_focus` is a validation error. Omit `voice_focus` to disable. Connection-time only; $0.10/hr add-on. Universal-3.6/3.5 Pro only.

```python
CONNECTION_PARAMS = {
    "sample_rate": 16000,
    "speech_model": "universal-3-6-pro",
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
