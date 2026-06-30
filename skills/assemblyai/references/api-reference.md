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
| `speech_models` | array | **Optional** (as of June 2026). Priority-ordered list of speech models to use (e.g., `["universal-3-5-pro", "universal-2"]`). First model is used if supported; falls back to next. If omitted, defaults to `["universal-3-pro", "universal-2"]`. Universal-3.5 Pro is accepted here (`["universal-3-5-pro"]`). |
| `prompt` | string | For Universal-3.5 Pro, a contextual *description* of the audio (domain → scenario → full detail), **not** formatting/behavioral instructions (those are ignored). **Complementary with `keyterms_prompt`** — both can be set together. |
| `keyterms_prompt` | array | List of key terms/phrases (strings) to boost recognition accuracy — up to **1000** terms for Universal-3.5 Pro, **200** for Universal-2, max **6 words per phrase**. **Complementary with `prompt`** — both can be set together. |
| `language_code` | string | Language code (e.g., `"en_us"`, `"es"`, `"fr"`). Defaults to `"en_us"`. |
| `language_detection` | boolean | Enable automatic language detection. Default `false`. |
| `language_detection_options` | object | Options for language detection: `expected_languages` (array of language codes), `fallback_language` (string), `code_switching` (boolean, Universal-2 only), `code_switching_confidence_threshold` (float, default 0.3). |
| `language_confidence_threshold` | float | Minimum confidence threshold for language detection (0-1). |
| `speaker_labels` | boolean | Enable speaker diarization. Default `false`. |
| `sentiment_analysis` | boolean | Enable sentiment analysis on each sentence. Default `false`. |
| `entity_detection` | boolean | Enable entity detection. Default `false`. |
| `auto_chapters` | boolean | **Deprecated.** Enable auto chapters. Use LLM Gateway instead. |
| `iab_categories` | boolean | Enable IAB content category detection. Default `false`. |
| `content_safety` | boolean | Enable content safety detection. Default `false`. |
| `content_safety_confidence` | integer | Minimum confidence threshold (25-100) for content safety labels. |
| `summarization` | boolean | **Deprecated.** Enable summarization. Use LLM Gateway instead. |
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
| `temperature` | float | 0–1. Controls randomness. Universal-3 Pro only. |
| `domain` | string | Domain-specific model variant. `"medical-v1"` enables Medical Mode (EN, ES, DE, FR). Supported on Universal-3 Pro and Universal-2. |
| `remove_audio_tags` | string | Remove inline annotations from the transcript. `"all"` removes all (audio event markers and speaker cues); `"speaker"` removes only speaker cues while keeping other annotations. Universal-3 Pro only. |
| `language_codes` | array | List of language codes for code-switching (must include `"en"`). Universal-3 Pro only. |
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
      { "message": "'ja' is not supported in universal-3-pro — transcription is handled by universal-2. To silence this warning, set speech_models: [\"universal-3-pro\", \"universal-2\"]." }
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

### U3-Pro

Set `language_detection: true` and include a `prompt` mentioning code-switching behavior (e.g., "The speaker switches between English and Spanish").

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

### Response Fields

- `language_code` — detected language
- `language_confidence` — confidence score
- `speech_model_used` — which speech model was applied

### Requirements

- Minimum **15 seconds** of spoken audio required.
- **15-90 seconds** of audio improves detection accuracy.

---

## 13. PII Policies

Full list of supported PII policy values for `redact_pii_policies`:

`account_number`, `banking_information`, `blood_type`, `credit_card_cvv`, `credit_card_expiration`, `credit_card_number`, `date`, `date_interval`, `date_of_birth`, `drivers_license`, `drug`, `duration`, `email_address`, `event`, `filename`, `gender`, `gender_sexuality`, `healthcare_number`, `injury`, `ip_address`, `language`, `location`, `location_address`, `location_address_street`, `location_city`, `location_coordinate`, `location_country`, `location_state`, `location_zip`, `marital_status`, `medical_condition`, `medical_process`, `money_amount`, `nationality`, `number_sequence`, `occupation`, `organization`, `organization_medical_facility`, `passport_number`, `password`, `person_age`, `person_name`, `phone_number`, `physical_attribute`, `political_affiliation`, `religion`, `sexuality`, `statistics`, `time`, `url`, `us_social_security_number`, `username`, `vehicle_id`, `zodiac_sign`

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
POST https://sync.assemblyai.com/transcribe
```

- `sync.assemblyai.com` — global default (routes to nearest region)
- `sync.us.assemblyai.com` — US residency (us-west-2, us-east-1)
- `sync.eu.assemblyai.com` — EU residency (eu-north-1)

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
| `prompt` | string | Custom instruction prepended to the model's system prompt. Max **4096** chars. Default applied when omitted. |
| `word_boost` | string[] | Keyterms that bias the decoder. Max **2048** chars total across all terms. (This is the documented keyterms param for Sync — *not* `keyterms_prompt`.) |
| `conversation_context` | string \| string[] | Prior turns from the same conversation in chronological order (oldest first, most recent last). Supplies the preceding dialogue as context for greater continuity across a multi-turn conversation (e.g. a user talking with a voice agent). A single string is treated as one turn. Oldest turns dropped first when over the context-window limit. |
| `language_code` | string \| string[] | Language of the audio as an ISO 639-1 code, or a list for multilingual audio. Steers the default transcription prompt toward the named language(s). **Ignored when a custom `prompt` is set.** Default `en`. One of: en, es, de, fr, it, pt, tr, nl, sv, no, da, fi, hi, vi, ar, he, ja, ur, zh. |
| `sample_rate` | integer | Required for `audio/pcm`. One of 8000, 16000, 22050, 24000, 32000, 44100, 48000. WAV reads it from the header. |
| `channels` | integer | Required for `audio/pcm`. `1` or `2` (stereo down-mixed to mono internally). |

`prompt` and `word_boost` can both be set in the same `config` part.

### Response

```json
{
  "text": "Hi, I'm calling about my Best Buy order...",
  "words": [
    { "text": "Hi",  "start": 0,   "end": 200, "confidence": 0.91 }
  ],
  "confidence": 0.87,
  "audio_duration_ms": 101567,
  "session_id": "eb92c4ff-4bbb-429f-9b99-7279d7fe738f"
}
```

Word timestamps use the fields `start` / `end` (integer **milliseconds**) — same field names as the async API. Note the clip-level `audio_duration_ms` does carry the `_ms` suffix. Include `session_id` in support requests.

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
curl -X POST https://sync.assemblyai.com/transcribe \
  -H 'Authorization: YOUR_API_KEY' \
  -H 'X-AAI-Model: universal-3-5-pro' \
  -F 'audio=@sample.wav;type=audio/wav' \
  -F 'config={"prompt":"Transcribe verbatim.","word_boost":["AssemblyAI"]};type=application/json'
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
| `GET /v1/agents/{agent_id}` | Retrieve one agent. Tool header **values** are masked as `"***"`. |
| `PUT /v1/agents/{agent_id}` | Update an agent. Every field optional — send only what you want to change. |
| `DELETE /v1/agents/{agent_id}` | Delete an agent. Returns `204`, no body. |

**Create body** (`application/json`): required `name`, `system_prompt`, `voice`; optional `greeting`, `input`, `output`, `tools`. Note `voice` is a **top-level** field here (in the WebSocket `session.update` it lives under `output.voice`). `greeting` is spoken straight to TTS on connect — omit it to have the agent listen first.

```bash
curl -X POST https://agents.assemblyai.com/v1/agents \
  -H 'Authorization: YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"name":"Support Bot","system_prompt":"You are a concise support agent.","voice":"ivy","greeting":"Hi, how can I help?"}'
```
