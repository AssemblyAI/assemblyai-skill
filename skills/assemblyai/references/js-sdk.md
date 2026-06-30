# AssemblyAI JavaScript/TypeScript SDK Reference

SDK: `npm i assemblyai`

Auth header format: `Authorization: KEY` (no Bearer prefix).

---

## 1. Basic Transcription

### Simple transcription

```typescript
import { AssemblyAI } from "assemblyai";

const client = new AssemblyAI({ apiKey: process.env.ASSEMBLYAI_API_KEY! });

const transcript = await client.transcripts.transcribe({
  audio: "https://example.com/audio.mp3",
});

console.log(transcript.text);
```

### With speaker labels

```typescript
const transcript = await client.transcripts.transcribe({
  audio: "https://example.com/audio.mp3",
  speaker_labels: true,
});

for (const utterance of transcript.utterances!) {
  console.log(`Speaker ${utterance.speaker}: ${utterance.text}`);
}
```

### With speech model fallback

```typescript
const transcript = await client.transcripts.transcribe({
  audio: "https://example.com/audio.mp3",
  speech_model: "nano",
  // Falls back to "best" if nano is unavailable for the detected language
});
```

---

## 2. Error Handling

```typescript
import { AssemblyAI } from "assemblyai";

const client = new AssemblyAI({ apiKey: process.env.ASSEMBLYAI_API_KEY! });

try {
  const transcript = await client.transcripts.transcribe({
    audio: "https://example.com/audio.mp3",
  });

  if (transcript.status === "error") {
    console.error("Transcription failed:", transcript.error);
    return;
  }

  console.log(transcript.text);
} catch (err) {
  console.error("API request failed:", err);
}
```

---

## 3. Speaker Diarization

```typescript
const transcript = await client.transcripts.transcribe({
  audio: "https://example.com/audio.mp3",
  speaker_labels: true,
  speakers_expected: 3, // optional hint
});

for (const utterance of transcript.utterances!) {
  console.log(`Speaker ${utterance.speaker} [${utterance.start}-${utterance.end}]: ${utterance.text}`);
}
```

---

## 4. PII Redaction

```typescript
import { AssemblyAI, PiiPolicy } from "assemblyai";

const client = new AssemblyAI({ apiKey: process.env.ASSEMBLYAI_API_KEY! });

const transcript = await client.transcripts.transcribe({
  audio: "https://example.com/audio.mp3",
  redact_pii: true,
  redact_pii_policies: [
    PiiPolicy.PersonName,
    PiiPolicy.PhoneNumber,
    PiiPolicy.EmailAddress,
    PiiPolicy.CreditCardNumber,
  ],
  redact_pii_sub: "hash", // "hash" or "entity_name"
});

console.log(transcript.text); // PII is redacted in the text
```

---

## 5. Audio Intelligence Features

**Note:** `auto_chapters` and `summarization` are mutually exclusive. You cannot enable both on the same transcription request.

### Sentiment analysis

```typescript
const transcript = await client.transcripts.transcribe({
  audio: "https://example.com/audio.mp3",
  sentiment_analysis: true,
});

for (const result of transcript.sentiment_analysis_results!) {
  console.log(`${result.text} — ${result.sentiment} (${result.confidence})`);
}
```

### Entity detection

```typescript
const transcript = await client.transcripts.transcribe({
  audio: "https://example.com/audio.mp3",
  entity_detection: true,
});

for (const entity of transcript.entities!) {
  console.log(`${entity.entity_type}: ${entity.text}`);
}
```

### Auto chapters

```typescript
const transcript = await client.transcripts.transcribe({
  audio: "https://example.com/audio.mp3",
  auto_chapters: true,
});

for (const chapter of transcript.chapters!) {
  console.log(`[${chapter.start}-${chapter.end}] ${chapter.headline}`);
  console.log(chapter.summary);
}
```

### Summarization

```typescript
const transcript = await client.transcripts.transcribe({
  audio: "https://example.com/audio.mp3",
  summarization: true,
  summary_model: "informative", // "informative", "conversational", "catchy"
  summary_type: "bullets",      // "bullets", "bullets_verbose", "gist", "headline", "paragraph"
});

console.log(transcript.summary);
```

### Content safety

```typescript
const transcript = await client.transcripts.transcribe({
  audio: "https://example.com/audio.mp3",
  content_safety: true,
});

for (const result of transcript.content_safety_labels!.results!) {
  for (const label of result.labels) {
    console.log(`${label.label}: ${label.confidence}`);
  }
}
```

---

## 6. Prompting with Universal-3.5 Pro

`prompt` and `keyterms_prompt` are **complementary** — use either or both together. `prompt` is a contextual *description* of the audio (domain → scenario → full detail), **not** formatting/behavioral instructions (those are ignored). `keyterms_prompt` is an explicit list of terms to boost (up to 1,000 for async). Start with neither and add only for vocabulary the model gets wrong.

```typescript
const transcript = await client.transcripts.transcribe({
  audio: "https://example.com/audio.mp3",
  speech_models: ["universal-3-5-pro"],
  prompt: "Cardiology consultation about chest pain symptoms.",
  keyterms_prompt: ["Dr. Smith", "ECG", "hypertension"],
});
```

---

## 7. Real-Time Streaming v2

Uses `RealtimeTranscriber` with event-based handling.

```typescript
import { AssemblyAI, RealtimeTranscriber } from "assemblyai";

const client = new AssemblyAI({ apiKey: process.env.ASSEMBLYAI_API_KEY! });

const transcriber = client.realtime.transcriber({
  sampleRate: 16_000,
});

transcriber.on("open", ({ sessionId }) => {
  console.log("Session opened:", sessionId);
});

transcriber.on("transcript.partial", (transcript) => {
  if (transcript.text) {
    process.stdout.write(`\rPartial: ${transcript.text}`);
  }
});

transcriber.on("transcript.final", (transcript) => {
  if (transcript.text) {
    console.log("\nFinal:", transcript.text);
  }
});

transcriber.on("error", (err) => {
  console.error("Realtime error:", err);
});

transcriber.on("close", (code, reason) => {
  console.log("Session closed:", code, reason);
});

await transcriber.connect();

// Send audio data (PCM16 chunks)
// transcriber.sendAudio(audioBuffer);

// When done:
// await transcriber.close();
```

---

## 8. Streaming v3 Turn-Based

Uses `client.streaming.transcriber` with a turn-based event model.

```typescript
import { AssemblyAI } from "assemblyai";

const client = new AssemblyAI({ apiKey: process.env.ASSEMBLYAI_API_KEY! });

const transcriber = client.streaming.transcriber({
  speechModel: "universal-3-5-pro",
  sampleRate: 16_000,
});

transcriber.on("turn", (turn) => {
  console.log(`Turn [${turn.start}-${turn.end}]: ${turn.transcript}`);

  if (turn.end_of_turn) {
    console.log("-- End of turn --");
  }
});

await transcriber.connect();

// Send audio data (PCM16 chunks)
// transcriber.sendAudio(audioBuffer);

// When done:
// await transcriber.close();
```

---

## 9. LLM Gateway

Use `fetch` to call the AssemblyAI LLM Gateway directly. Auth is `Authorization: KEY` (no Bearer).

```typescript
const response = await fetch(
  "https://llm-gateway.assemblyai.com/v1/chat/completions",
  {
    method: "POST",
    headers: {
      Authorization: process.env.ASSEMBLYAI_API_KEY!,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "claude-sonnet-4-5-20250929",
      messages: [
        { role: "user", content: "Summarize this transcript..." },
      ],
    }),
  }
);

const data = await response.json();
console.log(data.choices[0].message.content);
```
