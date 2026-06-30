# AssemblyAI Python SDK Reference

## Installation

```bash
pip install assemblyai
```

## Authentication

The SDK uses the `Authorization: KEY` header (no Bearer prefix). Set your API key before making any calls:

```python
import assemblyai as aai

aai.settings.api_key = "YOUR_API_KEY"
```

---

## 1. Basic Transcription

### From a URL

```python
import assemblyai as aai

aai.settings.api_key = "YOUR_API_KEY"

transcriber = aai.Transcriber()
transcript = transcriber.transcribe("https://example.com/audio.mp3")

print(transcript.text)
```

### From a local file

```python
transcript = transcriber.transcribe("/path/to/local/audio.mp3")
```

The SDK automatically uploads the local file to AssemblyAI's servers before transcription. No separate upload step is needed.

### With TranscriptionConfig and speech_models fallback

Use `speech_models` to specify a preferred model with automatic fallback:

```python
config = aai.TranscriptionConfig(
    speech_models=["universal-3-pro", "universal-2"]
)

transcriber = aai.Transcriber(config=config)
transcript = transcriber.transcribe("https://example.com/audio.mp3")
print(transcript.text)
```

If the first model in the list cannot process the audio, the next model is used as a fallback.

---

## 2. Error Handling

Always check `transcript.status` after transcription:

```python
transcript = transcriber.transcribe("https://example.com/audio.mp3")

if transcript.status == aai.TranscriptStatus.error:
    print(f"Transcription failed: {transcript.error}")
else:
    print(transcript.text)
```

---

## 3. Speaker Diarization

Enable speaker labels and iterate over utterances:

```python
config = aai.TranscriptionConfig(speaker_labels=True)

transcriber = aai.Transcriber(config=config)
transcript = transcriber.transcribe("https://example.com/audio.mp3")

for utterance in transcript.utterances:
    print(f"Speaker {utterance.speaker}: {utterance.text}")
```

---

## 4. PII Redaction

### Basic redaction

```python
config = aai.TranscriptionConfig(
    redact_pii=True,
    redact_pii_policies=[
        aai.PIIRedactionPolicy.person_name,
        aai.PIIRedactionPolicy.phone_number,
        aai.PIIRedactionPolicy.email_address,
        aai.PIIRedactionPolicy.credit_card_number,
        aai.PIIRedactionPolicy.ssn,
    ],
)

transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)
print(transcript.text)  # PII is replaced with ###
```

### Substitution policy

Control how redacted text appears:

```python
config = aai.TranscriptionConfig(
    redact_pii=True,
    redact_pii_policies=[
        aai.PIIRedactionPolicy.person_name,
    ],
    redact_pii_sub=aai.PIISubstitutionPolicy.hash,  # or .entity_name
)
```

### Redacted audio

Get a version of the audio with PII bleeped out:

```python
config = aai.TranscriptionConfig(
    redact_pii=True,
    redact_pii_audio=True,
    redact_pii_policies=[
        aai.PIIRedactionPolicy.person_name,
    ],
)

transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)
redacted_audio_url = transcript.redacted_audio_url
```

---

## 5. Audio Intelligence

### Sentiment Analysis

```python
config = aai.TranscriptionConfig(sentiment_analysis=True)
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)

for result in transcript.sentiment_analysis:
    print(f"{result.text} — {result.sentiment}")  # POSITIVE, NEGATIVE, NEUTRAL
```

### Entity Detection

```python
config = aai.TranscriptionConfig(entity_detection=True)
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)

for entity in transcript.entities:
    print(f"{entity.text} ({entity.entity_type})")
```

### Auto Chapters

Generates chapters with headlines, summaries, and gist for sections of audio.

```python
config = aai.TranscriptionConfig(auto_chapters=True)
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)

for chapter in transcript.chapters:
    print(f"{chapter.headline}")
    print(f"  {chapter.summary}")
    print(f"  Gist: {chapter.gist}")
```

> **Note:** `auto_chapters` and `summarization` are mutually exclusive. Do not enable both in the same config.

### IAB Categories (Topic Detection)

```python
config = aai.TranscriptionConfig(iab_categories=True)
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)

for result in transcript.iab_categories.results:
    print(result.text)
    for label in result.labels:
        print(f"  {label.label} ({label.relevance:.2f})")
```

### Content Safety Detection

```python
config = aai.TranscriptionConfig(content_safety=True)
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)

for result in transcript.content_safety.results:
    print(result.text)
    for label in result.labels:
        print(f"  {label.label} ({label.confidence:.2f})")
```

### Summarization

```python
config = aai.TranscriptionConfig(
    summarization=True,
    summary_model=aai.SummarizationModel.informative,
    summary_type=aai.SummarizationType.bullets,
)
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)

print(transcript.summary)
```

> **Note:** `summarization` and `auto_chapters` are mutually exclusive. Do not enable both in the same config.

### Auto Highlights (Key Phrases)

```python
config = aai.TranscriptionConfig(auto_highlights=True)
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)

for result in transcript.auto_highlights.results:
    print(f"{result.text} (count: {result.count}, rank: {result.rank:.4f})")
```

---

## 6. Language Detection

### Automatic language detection

```python
config = aai.TranscriptionConfig(language_detection=True)
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)

print(transcript.json_response["language_code"])
print(transcript.text)
```

### Specifying a language code directly

```python
config = aai.TranscriptionConfig(language_code="es")  # Spanish
transcript = transcriber.transcribe("https://example.com/audio.mp3", config=config)
print(transcript.text)
```

---

## 7. Prompting with Universal-3.5 Pro

`prompt` and `keyterms_prompt` are **complementary** — use either, or both together. `prompt` is a contextual *description* of the audio (domain → scenario → full detail), **not** formatting/behavioral instructions (those are ignored). `keyterms_prompt` is an explicit list of terms to boost (up to 1,000 for async). Start with neither and add only for vocabulary the model gets wrong.

```python
config = aai.TranscriptionConfig(
    speech_models=["universal-3-5-pro"],
    prompt="Cardiology consultation about chest pain symptoms.",
    keyterms_prompt=["Dr. Smith", "ECG", "hypertension"],
)

transcript = aai.Transcriber().transcribe("https://example.com/audio.mp3", config)
print(transcript.text)
```

> **Note on disfluencies:** Enable `disfluencies=True` to keep "ums" and "uhs" in the transcript.

---

## 8. Streaming v3 (Realtime)

Use the `assemblyai.streaming.v3` client for new realtime STT code. Set `speech_model="universal-3-5-pro"` explicitly; the raw API defaults to it, but the Python SDK parameter is required. Requires `assemblyai>=0.64.21` — older SDKs such as `0.64.4` reject `universal-3-5-pro` during local parameter validation.

```python
import os

from assemblyai.streaming.v3 import StreamingClient, StreamingClientOptions, StreamingParameters

client = StreamingClient(
    StreamingClientOptions(api_key=os.environ["ASSEMBLYAI_API_KEY"])
)

client.connect(
    StreamingParameters(
        speech_model="universal-3-5-pro",
        sample_rate=16_000,
    )
)

# Send PCM16 audio chunks with client.stream(audio_generator), then:
client.disconnect(terminate=True)
```

---

## 9. LLM Gateway Usage from Python

The LLM Gateway provides access to LLMs via AssemblyAI's infrastructure. Use `requests` to call the gateway endpoint directly. **Do not use LeMUR — it is deprecated.**

```python
import requests

API_KEY = "YOUR_API_KEY"

response = requests.post(
    "https://llm-gateway.assemblyai.com/v1/chat/completions",
    headers={
        "Authorization": API_KEY,
        "Content-Type": "application/json",
    },
    json={
        "model": "claude-sonnet-4-20250514",
        "messages": [
            {
                "role": "user",
                "content": "Summarize the key themes from this transcript: ...",
            }
        ],
        "temperature": 0.5,
    },
)

result = response.json()
print(result["choices"][0]["message"]["content"])
```

The gateway follows the OpenAI-compatible chat completions format. The `Authorization` header uses the API key directly — no Bearer prefix.

---

## 10. File Upload

The SDK handles file uploads automatically when you pass a local file path to `transcribe()`:

```python
transcript = transcriber.transcribe("/path/to/local/recording.wav")
```

Under the hood, the SDK uploads the file to AssemblyAI's servers and then submits the returned URL for transcription. No manual upload step is required.

If you need to upload manually (e.g., to reuse the URL across multiple transcriptions):

```python
upload_url = transcriber.upload_file("/path/to/local/recording.wav")
transcript = transcriber.transcribe(upload_url)
```
