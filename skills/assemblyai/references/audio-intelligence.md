# Audio Intelligence Features

All Audio Intelligence features are enabled via boolean parameters on the `POST /v2/transcript` request.

## Speaker Diarization

- Enable with `speaker_labels: true`
- Response includes `utterances` array with `speaker`, `text`, `start`, `end`
- Each word also gets a `speaker` field

## PII Redaction

- Enable with `redact_pii: true`
- `redact_pii_policies`: array of policy strings. Common policies include:
  - `person_name`
  - `phone_number`
  - `email_address`
  - `us_social_security_number`
  - `credit_card_number`
  - `date_of_birth`
- `redact_pii_sub`: `"hash"` or `"entity_name"`
- `redact_pii_audio: true` generates audio with PII beeped out
- `redact_pii_audio_quality`: `"mp3"` or `"wav"`
- `redact_pii_audio_options.override_audio_redaction_method`: set to `"silence"` to replace PII with silence instead of the default beep
- `redact_pii_return_unredacted: true` returns the original unredacted transcript alongside the redacted one in **a single API request**. The response then includes `unredacted_text`, `unredacted_words`, and `unredacted_utterances` fields. Default `false` — `text`/`words`/`utterances` remain fully redacted unless this flag is set.

**IMPORTANT:** Redacted audio files expire after 24 hours.

**IMPORTANT:** PII redaction only affects the `text` property — other feature outputs (entity detection, summarization, etc.) may still expose sensitive data in their results.

**IMPORTANT:** Setting `redact_pii_return_unredacted: true` opts in to receiving sensitive data in the response. Treat the `unredacted_*` fields with the same care as any unredacted source.

## Sentiment Analysis

- Enable with `sentiment_analysis: true`
- Response includes `sentiment_analysis_results` array
- Each result has `text`, `sentiment` (POSITIVE/NEGATIVE/NEUTRAL), `confidence`, `speaker`

## Entity Detection

- Enable with `entity_detection: true`
- Response includes `entities` array with `entity_type`, `text`, `start`, `end`

## Summarization (Deprecated)

**Deprecated — use the LLM Gateway instead.** Transcribe first, then send transcript text to the LLM Gateway for summarization. This gives better results and more control over output format.

Legacy parameters (still functional but not recommended for new code):
- `summarization: true`, `summary_model`, `summary_type`

## Auto Chapters (Deprecated)

**Deprecated — use the LLM Gateway instead.** Transcribe first, then prompt the LLM to segment and summarize the transcript into chapters.

Legacy parameters (still functional but not recommended for new code):
- `auto_chapters: true`

## Topic Detection (IAB Taxonomy)

- Enable with `iab_categories: true`
- Response includes `iab_categories_result` with `results` and `summary`

## Content Moderation

- Enable with `content_safety: true`
- `content_safety_confidence`: adjustable threshold (25-100, default 50)
- Detects categories including hate speech, violence, drugs, profanity, etc.
- Response includes `content_safety_labels` with results per segment

## Auto Highlights

- Enable with `auto_highlights: true`
- Extracts key phrases from the transcript
- Response includes `auto_highlights_result` with `results` array

## Medical Mode (Add-On)

- Enable with `domain: "medical-v1"` in the request body
- Improves accuracy for medical terminology: medications, procedures, conditions, dosages
- Supported models: Universal-3.5 Pro, Universal-2 (pre-recorded); all streaming models
- Supported languages: English, Spanish, German, French only
- Billed as a separate add-on
- If used with an unsupported language, the API ignores `domain` and returns a warning — no charge is applied
- Can be combined with diarization and keyterms prompting
