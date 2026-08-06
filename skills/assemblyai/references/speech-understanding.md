# Speech Understanding

## Overview

Speech Understanding provides post-transcription intelligence: **Translation, Speaker Identification, Custom Formatting, Summarization, and Action Items**. (Entity Detection, Sentiment Analysis, Key Phrases, and Topic Detection are *not* part of this object — they remain classic boolean transcript params; see `audio-intelligence.md`. The docs now group all of these under a single "Speech Understanding" section, but the request shapes are unchanged — only the five features here use the `speech_understanding` object.)

> **Summarization vs the deprecated `summarization`/`auto_chapters` params:** the top-level `summarization` and `auto_chapters` boolean params on `POST /v2/transcript` are **deprecated**. The modern replacements are the Speech Understanding `summarization` (chaptered summary with timestamps + headlines) and `action_items` features below — or the LLM Gateway for fully custom prompts.

Two ways to run it:

1. **Inline during transcription** — include the `speech_understanding` object in the `POST /v2/transcript` body. Results come back when the transcript completes.
2. **Post-hoc on an existing transcript** — `POST https://llm-gateway.assemblyai.com/v1/understanding` (EU: `https://llm-gateway.eu.assemblyai.com/v1/understanding`) with a `transcript_id`.

Auth header: `Authorization: API_KEY` (no `Bearer` prefix).

> **CRITICAL structure:** every feature nests under `speech_understanding.request.<feature>` — there is a `request` wrapper. Writing `speech_understanding.translation` directly (without `.request`) is invalid. Results come back under `speech_understanding.response.<feature>`.

```json
{
  "audio_url": "https://example.com/audio.mp3",
  "speaker_labels": true,
  "speech_understanding": {
    "request": {
      "translation": { "target_languages": ["es"] }
    }
  }
}
```

## Translation

Translates the transcript into one or more target languages.

- **Models:** Universal-3.5 Pro and Universal-2 only. **Regions:** US & EU. Supports 100+ language codes.

### Parameters (`speech_understanding.request.translation`)

- `target_languages` (array, **required**): language codes to translate into (e.g., `["es", "de"]`).
- `formal` (boolean, default `false`): when `true`, uses formal pronouns/grammatical forms.
- `match_original_utterance` (boolean, default `false`): when `true`, adds a `translated_texts` key to each utterance. **Requires `speaker_labels: true`.**
- `force_translation` (boolean, default `false`, added August 2026): translate even when the detected source language equals the target language (by default such targets are skipped).

### Example Request

```json
{
  "audio_url": "https://example.com/audio.mp3",
  "speaker_labels": true,
  "speech_understanding": {
    "request": {
      "translation": {
        "target_languages": ["es", "de"],
        "formal": true,
        "match_original_utterance": true
      }
    }
  }
}
```

### Response

The original transcript response gains a top-level `translated_texts` object (language code → full translated text). When `match_original_utterance` is enabled, each entry in `utterances` also gets its own `translated_texts`. Status lives at `speech_understanding.response.translation.status`.

```json
{
  "id": "735d90b6-...",
  "status": "completed",
  "text": "Smoke from hundreds of wildfires...",
  "translated_texts": {
    "es": "El humo de cientos de incendios forestales...",
    "de": "Rauch von Hunderten von Waldbränden..."
  },
  "speech_understanding": {
    "request": { "translation": { "formal": true, "target_languages": ["es", "de"] } },
    "response": { "translation": { "status": "success" } }
  }
}
```

## Speaker Identification

Distinct from diarization. Maps generic diarization labels (Speaker A, B, …) to actual names or roles. **Requires `speaker_labels: true`.**

### Parameters (`speech_understanding.request.speaker_identification`)

- `speaker_type` (string): `"name"` or `"role"`.
- `known_values` (array of strings): list of known names or roles, max 35 chars each. Required when `speaker_type` is `"role"` (and `speakers` is absent); optional when `"name"`.
- `speakers` (array of objects): richer metadata for better accuracy. Each object **must include `name` (for `speaker_type: "name"`) or `role` (for `speaker_type: "role"`)** plus an optional `description`. Any additional custom properties (`company`, `title`, `department`, …) are allowed. Use `known_values` **or** `speakers`, not both.

The current docs now lead with `speakers` as the primary form for **both** name and role identification (e.g. `[{"name": "Michel Martin"}]` or `[{"role": "Interviewer"}]`); `known_values` remains fully supported in the API.

### Example with known_values

```json
{
  "audio_url": "https://example.com/audio.mp3",
  "speaker_labels": true,
  "speech_understanding": {
    "request": {
      "speaker_identification": {
        "speaker_type": "name",
        "known_values": ["Michel Martin", "Peter DeCarlo"]
      }
    }
  }
}
```

### Example with speakers (role-based)

```json
{
  "audio_url": "https://example.com/audio.mp3",
  "speaker_labels": true,
  "speech_understanding": {
    "request": {
      "speaker_identification": {
        "speaker_type": "role",
        "speakers": [
          { "role": "interviewer", "description": "Hosts the program and interviews the guests" },
          { "role": "guest", "description": "Answers questions from the interview" }
        ]
      }
    }
  }
}
```

For name-based identification, replace `role` with `name` in each object (and optionally add custom fields like `company`/`title`).

### Response

`speech_understanding.response.speaker_identification.mapping` maps each diarization label to the identified value, and the rewritten `utterances`/`words` carry the identified label in their `speaker` field.

```json
{
  "speech_understanding": {
    "response": {
      "speaker_identification": {
        "mapping": { "A": "Michel Martin", "B": "Peter DeCarlo" },
        "status": "success"
      }
    }
  },
  "utterances": [
    { "speaker": "Michel Martin", "text": "Smoke from hundreds of wildfires...", "start": 240, "end": 26560 }
  ]
}
```

## Custom Formatting

Reformats dates, phone numbers, emails (and more) in the transcript according to format patterns you specify.

### Parameters (`speech_understanding.request.custom_formatting`)

The format params are **strings (format patterns), not booleans**:

- `date` (string): pattern for dates, e.g. `"mm/dd/yyyy"`, `"dd/mm/yyyy"`, `"yyyy-mm-dd"`.
- `phone_number` (string): pattern, e.g. `"(xxx)xxx-xxxx"`, `"xxx-xxx-xxxx"`.
- `email` (string): pattern, e.g. `"username@domain.com"`.
- `format_utterances` (boolean, default `false`): also format utterance-level text (preserves word timestamps).

### Example

```json
{
  "audio_url": "https://example.com/audio.mp3",
  "speech_understanding": {
    "request": {
      "custom_formatting": {
        "date": "mm/dd/yyyy",
        "phone_number": "(xxx)xxx-xxxx",
        "email": "username@domain.com",
        "format_utterances": true
      }
    }
  }
}
```

### Response

`speech_understanding.response.custom_formatting` contains `formatted_text`, `formatted_utterances` (only when `format_utterances: true`), and a `mapping` object (original → formatted).

## Summarization

Generates a chaptered summary of the transcript — each chapter has timestamps, a `text` summary, and a `headline`. Replaces the deprecated top-level `summarization`/`auto_chapters` params. **Open beta.** Models: `universal-3-5-pro`, `universal-2`. Regions: US & EU.

### Parameters (`speech_understanding.request.summarization`)

- `summary_type` (string, **required**): `"paragraph"` (longer, more detailed) or `"bullets"` (short, concise).
- `effort` (string, default `"low"`): `"low"` or `"medium"`. `medium` spends more processing power for higher-quality summaries — use it for high-stakes meetings, multilingual audio, or very long audio (≈1.5h+). Default `low` is sufficient for most cases.

### Example

```json
{
  "audio_url": "https://example.com/audio.mp3",
  "speech_understanding": {
    "request": {
      "summarization": { "summary_type": "paragraph", "effort": "low" }
    }
  }
}
```

### Response

`speech_understanding.response.summarization` → `{ status, summary_type, effort, summary: [{ start, end, text, headline }] }`:

```json
{
  "speech_understanding": {
    "response": {
      "summarization": {
        "status": "success",
        "summary_type": "paragraph",
        "effort": "low",
        "summary": [
          { "start": 240, "end": 37100, "text": "Smoke from hundreds of Canadian wildfires...", "headline": "Smoke from Canadian Wildfires Affects US Air Quality" }
        ]
      }
    }
  }
}
```

## Action Items

Extracts action items from the transcript, each with the source `quote` and a `timestamp`. **Open beta.** Models: `universal-3-5-pro`, `universal-2`. Regions: US & EU.

### Parameters (`speech_understanding.request.action_items`)

- `include_decisions` (boolean, default `false`): when `true`, also captures decisions made in the conversation as action items.
- `effort` (string, default `"low"`): `"low"` or `"medium"` (see Summarization for guidance on `medium`).

Pass an empty object (`"action_items": {}`) to use defaults.

### Example

```json
{
  "audio_url": "https://example.com/audio.mp3",
  "speech_understanding": {
    "request": {
      "action_items": { "include_decisions": true }
    }
  }
}
```

### Response

`speech_understanding.response.action_items` → `{ status, effort, items: [{ action_item, quote, timestamp }] }`:

```json
{
  "speech_understanding": {
    "response": {
      "action_items": {
        "status": "success",
        "effort": "low",
        "items": [
          { "action_item": "Observe the expansion and contraction of the Arctic ice cap throughout the seasons.", "quote": "The Arctic ice cap ... expands in winter and contracts in summer.", "timestamp": 9520 }
        ]
      }
    }
  }
}
```

## Post-hoc via the Understanding Endpoint

To run Speech Understanding on an **existing** transcript, POST to `/v1/understanding` with a `transcript_id` (same `speech_understanding.request.<feature>` structure):

```bash
curl -X POST "https://llm-gateway.assemblyai.com/v1/understanding" \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "transcript_id": "abc123",
    "speech_understanding": {
      "request": {
        "translation": { "target_languages": ["de"], "formal": true }
      }
    }
  }'
```

## Rate Limits (`/understanding` endpoint)

Per-account, 60-second window: **Free = 2 req/min, Paid = 30 req/min**. A single multi-feature request counts once.
