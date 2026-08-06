# AssemblyAI REST API Reference

Base URL: `https://api.assemblyai.com`

All requests require the header `authorization: YOUR_API_KEY`.

---

## 1. File Upload

**`POST /v2/upload`**

Upload a local audio file to AssemblyAI's hosted storage.

- Content-Type: `application/octet-stream`
- Supports `transfer-encoding: chunked` for streaming uploads
- Returns: `{ "upload_url": "..." }`
- The returned `upload_url` is only accessible for transcription using the same API key project. Using a different project's key returns a **403** error.
- SDKs handle upload automatically when you pass a local file path to the transcription method.
- **Send the file as raw bytes.** With cURL use `--data-binary @file` (note the `@`). Using `-d`/`--data`, a JSON body, or a file-path *string* returns a successful `upload_url` but then fails downstream at transcription with `Transcoding failed. File type application/json` (or `text/plain`). This silent split between a 200 on upload and a later transcription failure is a common gotcha.

---

## 2. Submit Transcription

**`POST /v2/transcript`**

Submit an audio file for transcription. Send a JSON body with the parameters below.

### Parameter Table

| Parameter | Type | Description |
|---|---|---|
| `audio_url` | string | **Required.** URL of the audio file to transcribe. Can be a public URL or an `upload_url` from the upload endpoint. |
| `speech_models` | array | **Optional.** Priority-ordered list of speech models. First supported model is used; falls back to the next. **If omitted, defaults to `["universal-3-5-pro", "universal-2"]`** for accounts created on/after July 7, 2026 — all remaining accounts switch to this default on **September 2, 2026** (from that date `["universal-3-pro"]` returns an error). The enum now accepts only `universal-3-5-pro` and `universal-2` — `universal-3-pro` was removed (superseded by `universal-3-5-pro`). The `speech_model_used` response field reports which model actually ran. |
| `prompt` | string | For Universal-3.5 Pro, a contextual *description* of the audio (domain → scenario → full detail), **not** formatting/behavioral instructions (those are ignored). **Complementary with `keyterms_prompt`** — both can be set together. |
| `keyterms_prompt` | array | List of key terms/phrases (strings) to boost recognition accuracy — up to **1000** terms for Universal-3.5 Pro, **200** for Universal-2, max **6 words per phrase**. **Complementary with `prompt`** — both can be set together. |
| `language_code` | string | Language code (e.g., `"en_us"`, `"es"`, `"fr"`). Defaults to `"en_us"`. |
| `language_detection` | boolean | Enable automatic language detection. Default `false`. |
| `language_detection_options` | object | Options for language detection: `expected_languages` (array of language codes), `fallback_language` (string), `code_switching` (boolean, Universal-2 only), `code_switching_confidence_threshold` (float, default 0.3). |
| `language_confidence_threshold` | float | Minimum confidence threshold for language detection (0-1). |
| `speaker_labels` | boolean | Enable speaker diarization. Default `false`. |
| `sentiment_analysis` | boolean | Enable sentiment analysis on each sentence. Default `false`. |
| `entity_detection` | boolean | Enable entity detection. Default `false`. |
| `auto_chapters` | boolean | **Deprecated.** Use Speech Understanding `summarization` (chaptered summary; see `speech-understanding.md`) or the LLM Gateway instead. |
| `iab_categories` | boolean | Enable IAB content category detection. Default `false`. |
| `content_safety` | boolean | Enable content safety detection. Default `false`. |
| `content_safety_confidence` | integer | Minimum confidence threshold (25-100) for content safety labels. |
| `summarization` | boolean | **Deprecated.** Use Speech Understanding `summarization`/`action_items` (see `speech-understanding.md`) or the LLM Gateway instead. |
| `summary_model` | string | **Deprecated.** Model for summarization. |
| `summary_type` | string | **Deprecated.** Type of summary. |
| `redact_pii` | boolean | Enable PII redaction. Default `false`. |
| `redact_pii_policies` | array | List of PII policies to redact (see PII Policies section). |
| `redact_pii_sub` | string | Substitution type: `"hash"` (default) or `"entity_name"`. |
| `redact_pii_audio` | boolean | Generate a redacted audio file. Default `false`. |
| `redact_pii_audio_quality` | string | Quality of redacted audio: `"mp3"` or `"wav"`. |
| `redact_pii_audio_options` | object | `override_audio_redaction_method: "silence"` replaces PII with silence instead of default beep. `return_redacted_no_speech_audio: true` also redacts non-speech segments. |
| `redact_pii_return_unredacted` | boolean | When `true`, returns the original unredacted transcript alongside the redacted one in a single request. Response then includes `unredacted_text`, `unredacted_words`, and `unredacted_utterances`. Default `false`. |
| `redact_static_entities` | object | Literal find-and-replace redaction layered on top of standard PII redaction. Maps a custom label to a list of exact terms, e.g. `{"INTERNAL_TOOL": ["Bearclaw", "Cubclaw"]}`. Requires `redact_pii: true` (else 400); matched terms are also redacted in audio when `redact_pii_audio` is on. |
| `filter_profanity` | boolean | Filter profanity from transcript text. Default `false`. |
| `disfluencies` | boolean | Include disfluencies (um, uh, etc.) in transcript. Default `false`. |
| `multichannel` | boolean | Enable multichannel transcription. Default `false`. |
| `custom_spelling` | array | Array of custom spelling rules. See Custom Spelling section. |
| `webhook_url` | string | URL to receive a webhook when transcription completes. |
| `webhook_auth_header_name` | string | Custom header name for webhook authentication. |
| `webhook_auth_header_value` | string | Custom header value for webhook authentication. |
| `auto_highlights` | boolean | Enable key phrase detection. Default `false`. |
| `speech_understanding` | object | Enable Speech Understanding inline. Features nest under `speech_understanding.request` (the `request` wrapper is required): `translation`, `speaker_identification`, and/or `custom_formatting`. See `speech-understanding.md`. |
| `speakers_expected` | integer | Hint for number of speakers (diarization). Deprecated in favor of `speaker_options`. |
| `speaker_options` | object | Diarization options: `min_speakers_expected` (int, default 1), `max_speakers_expected` (int). |
| `temperature` | float | 0–1. Controls randomness. Universal-3.5 Pro only. |
| `domain` | string | Domain-specific model variant. `"medical-v1"` enables Medical Mode (EN, ES, DE, FR). Supported on Universal-3.5 Pro and Universal-2. |
| `remove_audio_tags` | string | Remove inline annotations from the transcript. `"all"` removes all (audio event markers and speaker cues); `"speaker"` removes only speaker cues while keeping other annotations. Universal-3.5 Pro only. |
| `language_codes` | array | List of language codes for code-switching (must include `"en"`). Universal-3.5 Pro only. |
| `audio_start_from` | integer | Start transcription from this time offset, in **milliseconds**. |
| `audio_end_at` | integer | End transcription at this time offset, in **milliseconds**. |
| `speech_threshold` | float | Confidence threshold (0-1) for filtering low-confidence speech. Requires at least **30 seconds** of audio. |

---

## 3. Poll for Result

**`GET /v2/transcript/{id}`**

Poll this endpoint until the response `status` field is `completed` or `error`.

- `status: "queued"` — waiting in queue
- `status: "processing"` — currently being transcribed
- `status: "completed"` — transcription finished; full result available
- `status: "error"` — transcription failed; check `error` field for details

### HTTP Rate Limit

The async REST API allows **20,000 HTTP requests per 5-minute window**, counted across submissions (`POST /v2/transcript`) **and** polling (`GET /v2/transcript/{id}`) combined. Exceeding it returns **403**. Tight polling loops over many concurrent jobs are the usual cause — prefer webhooks (`webhook_url`) over polling, or widen and jitter your polling interval. (Separately, parallel in-flight transcriptions are capped at 200+ for paid accounts; jobs beyond that queue rather than erroring.)

### Response `metadata`

The transcript response may include an optional `metadata` object with additional information about how the request was processed. The field is **omitted entirely** when there is nothing to report.

```json
{
  "id": "...",
  "status": "completed",
  "text": "...",
  "metadata": {
    "domain_used": null,
    "warnings": [
      { "message": "'ur' is not supported in universal-3-5-pro — transcription is handled by universal-2. To silence this warning, set speech_models: [\"universal-3-5-pro\", \"universal-2\"]." }
    ]
  }
}
```

- `metadata.domain_used` — the domain-specific model that was applied (e.g. `"medical-v1"` for Medical Mode), or `null` if none was used. Always present when `metadata` is present.
- `metadata.warnings` — array of `{message}` objects describing issues encountered during processing — e.g. an audio language that the requested model can't handle (and was routed to a fallback model), or Medical Mode skipped for an unsupported language. The field is **omitted** when there are no warnings.

Check `metadata.warnings` after every transcription to catch silent fallbacks (model routing, or Medical Mode requested but not applied because the language wasn't supported — the request still completes and is NOT charged for Medical Mode). Separately, the top-level `speech_model_used` field always reports which model actually ran.

---

## 4. Export Endpoints

### SRT Subtitles

**`GET /v2/transcript/{id}/srt`**

Returns subtitles in SRT format. Optional query parameter:

- `chars_per_caption` (integer) — maximum characters per caption line

### WebVTT Subtitles

**`GET /v2/transcript/{id}/vtt`**

Returns subtitles in WebVTT format. Optional query parameter:

- `chars_per_caption` (integer) — maximum characters per caption line

### Sentences

**`GET /v2/transcript/{id}/sentences`**

Returns a sentence-level breakdown of the transcript with timestamps.

### Paragraphs

**`GET /v2/transcript/{id}/paragraphs`**

Returns a paragraph-level breakdown of the transcript with timestamps.

---

## 5. Word Search

**`GET /v2/transcript/{id}/word-search?words=word1,word2`**

Search for specific words in the transcript. Returns matches with timestamps and match counts.

---

## 6. List Transcripts

**`GET /v2/transcript`**

Returns a paginated list of transcripts. Supports pagination query parameters (`limit`, `after_id`, `before_id`, `status`, etc.).

---

## 7. Delete Transcript

**`DELETE /v2/transcript/{id}`**

Permanently deletes a transcript and its associated data.

---

## 8. Webhooks

Set `webhook_url` in the transcript request body to receive a POST notification when transcription completes.

### Requirements

- The webhook endpoint **must return a 2xx status** within **10 seconds**.
- AssemblyAI retries up to **10 times** on failure.
- A **4xx** response stops retries immediately.

### IP Allowlisting

If your firewall requires IP allowlisting:

- **US region:** `44.238.19.20`
- **EU region:** `54.220.25.36`

### Custom Authentication

Use `webhook_auth_header_name` and `webhook_auth_header_value` in the transcript request to include a custom authentication header on webhook requests.

### Metadata via Query Parameters

You can append metadata as query parameters on the `webhook_url` (e.g., `https://example.com/hook?user_id=123&job_id=abc`). These are passed through on the webhook POST.

---

## 9. Custom Spelling

Use `custom_spelling` to correct domain-specific terms or names in the transcript.

```json
{
  "custom_spelling": [
    { "from": ["goethe", "gothe"], "to": "Goethe" },
    { "from": ["biolojee"], "to": "Biology" }
  ]
}
```

Rules:

- `to` is **case-sensitive** (the replacement preserves the casing you specify).
- `from` is **case-insensitive**.
- `to` must be a **single word**.

---

## 10. Multichannel Transcription

Set `multichannel: true` to transcribe each audio channel independently.

- The response includes an `audio_channels` field with the detected channel count.
- Speaker labels use per-channel diarization with the format `{channel}{speaker}` (e.g., `"1A"`, `"1B"`, `"2A"`).
- Adds approximately **25% additional processing time**.

---

## 11. Code Switching

Code switching allows transcription of audio that switches between multiple languages.

### Universal-3.5 Pro

Code-switching across its 18 languages is native — no configuration required. Optionally set `language_detection: true` to have the detected language reported, and mention the languages in the contextual `prompt` (e.g., "The speaker switches between English and Spanish") to reinforce steering.

### Universal-2

Set `code_switching: true` inside `language_detection_options`, along with an optional `code_switching_confidence_threshold` (default `0.3`):

```json
{
  "language_detection": true,
  "language_detection_options": {
    "code_switching": true,
    "code_switching_confidence_threshold": 0.3
  }
}
```

---

## 12. Language Detection

Set `language_detection: true` to automatically detect the spoken language.

### Options

Use `language_detection_options` to refine detection:

- `expected_languages` (array) — restrict detection to specific language codes
- `fallback_language` (string) — fallback language code if detection fails
- `localization` (array, added July 2026) — apply regional English spelling: only `en_au` and `en_uk` are accepted (anything else is a 400; max one locale per base language)

### Response Fields

- `language_code` — detected language; when `localization` matched, this surfaces the applied locale (e.g. `en_au`)
- `language_confidence` — confidence score
- `speech_model_used` — which speech model was applied

### Requirements

- Minimum **15 seconds** of spoken audio required.
- **15-90 seconds** of audio improves detection accuracy.

---

## 13. PII Policies

Full list of supported PII policy values for `redact_pii_policies`:

`account_number`, `banking_information`, `blood_type`, `credit_card_cvv`, `credit_card_expiration`, `credit_card_number`, `date`, `date_interval`, `date_of_birth`, `drivers_license`, `drug`, `duration`, `email_address`, `event`, `filename`, `gender`, `gender_sexuality`, `healthcare_number`, `injury`, `ip_address`, `language`, `location`, `location_address`, `location_address_street`, `location_city`, `location_coordinate`, `location_country`, `location_state`, `location_zip`, `marital_status`, `medical_condition`, `medical_process`, `money_amount`, `nationality`, `number_sequence`, `occupation`, `organization`, `organization_medical_facility`, `passport_number`, `password`, `person_age`, `person_name`, `phone_number`, `physical_attribute`, `political_affiliation`, `religion`, `sexuality`, `statistics`, `time`, `url`, `us_social_security_number`, `username`, `vehicle_id`, `zodiac_sign`

The granular `location_*` policies (July 2026) behave hierarchically: a full contiguous spoken address is redacted as a **single `location_address` span**, while standalone fragments ("I live in Denver") are tagged with their subtype (`location_city`).

---

## 14. Data Retention & Compliance

### Retention Policies

- **Streaming (real-time):** Zero data retention when opted out of training data usage.
- **Async transcription with TTL:** Audio files are deleted after **3 days**. Transcript data deletion starts at **1 hour**.

### Certifications

- SOC 2 Type 1 and Type 2 certified.

### Encryption

- **At rest:** AES-128/256 encryption.
- **In transit:** TLS 1.2+ encryption.

---

## 15. cURL Examples

### Upload, Transcribe, and Poll

```bash
# Step 1: Upload audio file
UPLOAD_RESPONSE=$(curl -s -X POST "https://api.assemblyai.com/v2/upload" \
  -H "authorization: YOUR_API_KEY" \
  -H "content-type: application/octet-stream" \
  --data-binary @audio.mp3)

UPLOAD_URL=$(echo "$UPLOAD_RESPONSE" | jq -r '.upload_url')
echo "Upload URL: $UPLOAD_URL"

# Step 2: Submit transcription
TRANSCRIPT_RESPONSE=$(curl -s -X POST "https://api.assemblyai.com/v2/transcript" \
  -H "authorization: YOUR_API_KEY" \
  -H "content-type: application/json" \
  -d "{\"audio_url\": \"$UPLOAD_URL\"}")

TRANSCRIPT_ID=$(echo "$TRANSCRIPT_RESPONSE" | jq -r '.id')
echo "Transcript ID: $TRANSCRIPT_ID"

# Step 3: Poll until completed
while true; do
  RESULT=$(curl -s -X GET "https://api.assemblyai.com/v2/transcript/$TRANSCRIPT_ID" \
    -H "authorization: YOUR_API_KEY")
  STATUS=$(echo "$RESULT" | jq -r '.status')
  echo "Status: $STATUS"

  if [ "$STATUS" = "completed" ]; then
    echo "$RESULT" | jq -r '.text'
    break
  elif [ "$STATUS" = "error" ]; then
    echo "Error: $(echo "$RESULT" | jq -r '.error')"
    break
  fi

  sleep 5
done
```

### With Speaker Labels and PII Redaction

```bash
curl -s -X POST "https://api.assemblyai.com/v2/transcript" \
  -H "authorization: YOUR_API_KEY" \
  -H "content-type: application/json" \
  -d '{
    "audio_url": "https://example.com/audio.mp3",
    "speaker_labels": true,
    "redact_pii": true,
    "redact_pii_policies": [
      "person_name",
      "phone_number",
      "email_address",
      "us_social_security_number",
      "credit_card_number"
    ],
    "redact_pii_sub": "entity_name"
  }'
```

---

## 16. Sync STT API (Short-Form Audio)

A separate **synchronous** endpoint for clips between **80ms and 120s** — submit audio and receive the transcript in a single request/response, with no polling, no transcript ID, and no upload step. Distinct service from the async REST API above.

### Endpoint

```
POST https://sync.assemblyai.com/v1/transcribe
```

Routes are versioned as of July 2026 — the unprefixed `/transcribe` still works for legacy clients, but new code should use `/v1/`.

- `sync.assemblyai.com` — global default (routes to nearest region)
- `sync.us.assemblyai.com` — US residency (us-west-2, us-east-1)
- `sync.eu.assemblyai.com` — EU residency (eu-north-1)

**Pre-warming:** `GET https://sync.assemblyai.com/v1/warm` establishes the connection ahead of the first real request (returns `200 {"warm":"toasty"}`). Python SDK: `SyncTranscriber.warm()` + `aai.settings.keepalive_expiry`; the Node SDK also ships `SyncTranscriber`.

### Headers

| Header | Required | Notes |
|--------|----------|-------|
| `Authorization` | Yes | `YOUR_API_KEY` — `Bearer ` prefix is *optionally* accepted here. Alternatively pass `?token=YOUR_API_KEY`. |
| `X-AAI-Model` | Yes | Model to use. The current quickstart uses **`universal-3-5-pro`**; `u3-sync-pro` (Universal-3 Pro) is also accepted (it's the value in the formal `sync-api.yaml` enum). |

### Request Body (`multipart/form-data`)

| Part | Content-Type | Notes |
|------|-------------|-------|
| `audio` | `audio/wav` or `audio/pcm` | **Required.** Raw audio bytes. For raw PCM use S16LE little-endian. |
| `config` | `application/json` | Optional config object (below). |

`config` fields:

| Field | Type | Notes |
|-------|------|-------|
| `prompt` | string | Contextual *description* of the audio (domain/scenario/details), prepended to the model's built-in transcription prompt. Max **4096** chars. Default applied when omitted. Like the async/streaming `prompt`, it carries context — not formatting/behavioral instructions. |
| `keyterms_prompt` | string[] | Keyterms that bias the decoder. Max **2048** chars total across all terms. **Renamed from `word_boost` in July 2026** — the aliases `word_boost` and `keyterms` are still accepted. |
| `conversation_context` | string \| string[] | Prior turns from the same conversation in chronological order (oldest first, most recent last). Supplies the preceding dialogue as context for greater continuity across a multi-turn conversation (e.g. a user talking with a voice agent). A single string is treated as one turn. Oldest turns dropped first when over the context-window limit. |
| `language_codes` | string[] \| string | Language(s) of the audio as ISO 639-1 codes (singular `language_code` also accepted). Steers the default transcription prompt toward the named language(s). **Ignored when a custom `prompt` is set.** Default `en`. One of: en, es, de, fr, it, pt, tr, nl, sv, no, da, fi, hi, vi, ar, he, ja, ur, zh. |
| `timestamps` | boolean | Default `false`. Opt-in per-word `start`/`end` (integer ms) via forced alignment. Works for all request languages; timestamps are **omitted** (never estimated) if the aligner is unavailable. |
| `sample_rate` | integer | Required for `audio/pcm`. One of 8000, 16000, 22050, 24000, 32000, 44100, 48000. WAV reads it from the header. |
| `channels` | integer | Required for `audio/pcm`. `1` or `2` (stereo down-mixed to mono internally). |

`prompt` and `keyterms_prompt` can both be set in the same `config` part. **Unknown `config` fields are rejected with a 400** — don't pass async-API params here.

### Response

```json
{
  "text": "Hi, I'm calling about my Best Buy order...",
  "words": [
    { "text": "Hi",  "start": 0,   "end": 200, "confidence": 0.91 }
  ],
  "confidence": 0.87,
  "audio_duration_ms": 101567,
  "session_id": "eb92c4ff-4bbb-429f-9b99-7279d7fe738f",
  "request_time_ms": 143
}
```

Word `start` / `end` (integer **milliseconds** — same field names as the async API) appear **only when `timestamps: true`** is set in `config`; otherwise `words[]` carries `text` + `confidence` only. Note the clip-level durations carry the `_ms` suffix. Include `session_id` in support requests.

### Audio Requirements

| Constraint | Value |
|------------|-------|
| Duration | 80ms – 120s |
| Max file size | 40 MB |
| Sample width | 16-bit only |
| Channels | Mono or stereo (stereo down-mixed) |
| Sample rates | 8000, 16000, 22050, 24000, 32000, 44100, 48000 Hz |
| Formats | WAV (`audio/wav`) or raw PCM S16LE (`audio/pcm`) |

### Error Codes

Errors return JSON with either `error_code` + `message` (audio/capacity/inference) or `detail` (auth/rate-limit).

| HTTP | `error_code` | Cause |
|------|-------------|-------|
| 400 | `bad_audio` | Malformed WAV, misaligned PCM, or missing `sample_rate`/`channels` for PCM |
| 400 | `audio_too_short` | Audio below 80ms |
| 400 | `bad_request` | Missing `audio` part, invalid config JSON, or field limits exceeded |
| 401 | — | Missing or invalid API key |
| 413 | `audio_too_large` | Duration > 120s or file > 40 MB |
| 415 | `unsupported_media_type` | Unsupported format, non-16-bit audio, or unsupported sample rate |
| 429 | — | Rate limit exceeded — retry after `Retry-After` header |
| 503 | `capacity_exceeded` / `service_unavailable` | At concurrency cap, or model cold-starting — retry after `Retry-After` |
| 504 | `inference_timeout` | Exceeded the **30s** per-request deadline |
| 500 | `inference_error` | Internal model error |

### Example

```bash
curl -X POST https://sync.assemblyai.com/v1/transcribe \
  -H 'Authorization: YOUR_API_KEY' \
  -H 'X-AAI-Model: universal-3-5-pro' \
  -F 'audio=@sample.wav;type=audio/wav' \
  -F 'config={"prompt":"Customer voice message about an online order.","keyterms_prompt":["AssemblyAI"],"timestamps":true};type=application/json'
```

When to use: short pre-recorded clips needing an immediate response (voice messages, short call recordings, externally-segmented voice-agent utterances). For audio > 120s use the async REST API; for live mic audio use Streaming.

## 17. Voice Agents REST API (Stored Agents)

A REST API for creating **reusable** voice agents. An agent stores its `system_prompt`, `greeting`, `voice`, `tools`, `input`, and `output` server-side; you then bind a WebSocket session to it by sending `{"agent_id": "<id>"}` as the only field in your first `session.update` (see `references/voice-agents.md`). The same stored agent can be reused across the WebSocket API, browser, or Twilio.

- **Base URL:** `https://agents.assemblyai.com` (same host as the Voice Agent WebSocket API)
- **Auth:** `Authorization: YOUR_API_KEY` — the raw key works directly; a `Bearer ` prefix is also accepted.

| Method & Path | Description |
|---------------|-------------|
| `POST /v1/agents` | Create an agent. Returns `201` with the full record including a generated `id`. |
| `GET /v1/agents` | List agents (lightweight records, no tools/prompt), newest first. |
| `GET /v1/agents/{agent_id}` | Retrieve one agent. Read responses return tool-header **names** and `last_set_at` only — header **values are never returned** (write-only, encrypted at rest; they are *not* masked as `"***"`). Likewise a connected LLM (`llm`) comes back as `base_url` + `model` only, never `api_key`. |
| `PUT /v1/agents/{agent_id}` | Update an agent. Every field optional — send only what you want to change. |
| `DELETE /v1/agents/{agent_id}` | Delete an agent. Returns `204`, no body. |
| `GET /v1/builtin-tools` | List platform built-in tools (`{name, description, parameters, execution_mode}`) — added July 2026. Attach one to an agent by passing its `name` in `tools[]`. The `aai_` name prefix is reserved for these. |
| `GET /v1/voices` | Authoritative live list of TTS voices. |

### Sessions API (session history — added July 2026)

Retrieve past Voice Agent sessions — the documented way to get recordings and conversation timelines after a call (poll this, or use webhook subscriptions below):

| Method & Path | Description |
|---------------|-------------|
| `GET /v1/sessions` | List sessions, newest first. `limit` 1–200 (default 50), cursor-paged; filter by `status` and/or `agent_id`. Records include `agent_id`. |
| `GET /v1/sessions/{session_id}` | One session with its **recording** and conversation **timeline**. |
| `DELETE /v1/sessions/{session_id}` | Delete a session record. |
| `GET /v1/token` | Generate a temporary client token for browser use (see `references/voice-agents.md`). |

**Create body** (`application/json`): required `name`, `system_prompt`, `voice`; optional `greeting`, `input`, `output`, `tools`, `llm`. Note `voice` is a **top-level** field here (in the WebSocket `session.update` it lives under `output.voice`). `greeting` is spoken straight to TTS on connect — omit it to have the agent listen first.

```bash
curl -X POST https://agents.assemblyai.com/v1/agents \
  -H 'Authorization: YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"name":"Support Bot","system_prompt":"You are a concise support agent.","voice":"ivy","greeting":"Hi, how can I help?"}'
```

### Server-side HTTP tools (`headers` shape)

A tool with an `http` block (`url`, `http_method`, `headers`) is executed **server-side** — AssemblyAI makes the request on your behalf. As of June 2026 `headers` is a **list of `{name, value}` entries**, NOT a `{name: value}` dict:

```json
{ "http": { "url": "https://api.example.com/orders", "http_method": "POST",
  "headers": [ { "name": "Authorization", "value": "Bearer xyz" } ] } }
```

- **Write (create/update):** each entry is `{ name, value?, remove? }`. Provide `value` to set/rotate; provide name only to keep the stored value unchanged (round-tripping on update); `remove: true` deletes it. Sending both `value` and `remove: true` is rejected.
- **Read (get/list):** each entry is `{ name, last_set_at }` — values are never returned.
- Server-side constraints: `https` + public hosts only (private/loopback/CGNAT blocked); redirects not followed; response body capped at 8 KiB; per-call timeout from `timeout_seconds`.

### Bring your own LLM (`llm`)

Point an agent at your own **OpenAI-compatible** chat-completions endpoint instead of AssemblyAI's managed model. Set the `llm` field (a list; **only one entry accepted today**) on create/update:

```json
{ "llm": [ { "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini", "api_key": "sk-..." } ] }
```

- `base_url` (required, `https` + public host — the agent calls `POST {base_url}/chat/completions`), `model` (required), `api_key` (required, **write-only**, never returned).
- Must support **streamed** chat completions. Send `"llm": []` to switch back to the managed model.
- To use a frontier model without your own provider account, point `base_url` at the **LLM Gateway** (`https://llm-gateway.assemblyai.com/v1`, EU: `https://llm-gateway.eu.assemblyai.com/v1`) and pass your AssemblyAI key as `api_key`.

## 18. Voice Agent Webhooks API

A REST API (base URL `https://agents.assemblyai.com`, same auth) to subscribe URLs to Voice Agent lifecycle events.

| Method & Path | Description |
|---------------|-------------|
| `POST /v1/webhook-subscriptions` | Subscribe a URL to one or more events. Scope to one agent with `agent_id`, or omit for account-wide events. Returns the created subscription. |
| `GET /v1/webhook-subscriptions` | List subscriptions (paginated). |
| `GET /v1/webhook-subscriptions/{subscription_id}` | Retrieve one subscription. |
| `PUT /v1/webhook-subscriptions/{subscription_id}` | Update `url`, `events`, `secret`, or `enabled`. Sending a new `secret` rotates it and increments `secret_version`. |
| `DELETE /v1/webhook-subscriptions/{subscription_id}` | Delete a subscription. Returns `204`. |

- **Events:** `session.started`, `session.completed`, `call.connected`, `call.ended`, `call.failed`.
- **Body fields:** `url` (`https` + public host, required), `events` (array, required), `secret` (32–256 printable ASCII chars, no whitespace — signing secret, **write-only**, only its `secret_version` is returned), `agent_id` (optional; omit for account-wide).
