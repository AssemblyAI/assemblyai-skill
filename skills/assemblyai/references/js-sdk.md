# AssemblyAI JavaScript/TypeScript SDK Reference

```bash
npm i assemblyai@^4.41.1
```

**4.41.1 is the latest release (Sept 11, 2026).** Install it, or `npm i assemblyai@latest` for whatever is newest if you are reading this later. Requires Node `>=18`. The matched Python version is `assemblyai>=1.5.4` (Sept 14, 2026).

Anything below **4.40.0** has no `client.dictation`, and below **4.38.0** no `client.llmGateway` — check `npm ls assemblyai` before writing code against them in an existing project, and fall back to raw `fetch` (see `references/dictation.md`) if the project can't upgrade yet.

The oldest release with the current API surface is **4.37.0** (Aug 28, 2026), which **removed LeMUR** (`client.lemur`, `LemurService`, and every Lemur request/response type) — the counterpart to Python 1.0.0 doing the same. Nothing else broke in it: no renames, no signature changes, so upgrading from 4.36.x is a drop-in unless you called `client.lemur`.

Auth header format: `Authorization: KEY` (no Bearer prefix).

Recent additions worth knowing about, newest first:

| Version | Change |
|---------|--------|
| 4.41.1 | Dictation/sync config caps raised to match the service (`stt_prompt` 6000, keyterms 100 / 8000, `llm_instruction` 2048); `universal-3-6` streaming model |
| 4.40.0 | **`client.dictation`** for the Dictation API (§11); `client.sync.transcribeLive()` / `openLive()` streaming upload; no-speech fallback options for transcripts |
| 4.38.0 | `client.llmGateway` (`chatCompletions()`, `listModels()`, `understanding()`), `llmGatewayBaseUrl` option, `LlmGatewayError` |
| 4.37.1 | `universal-3-6-pro` added to `StreamingSpeechModel`. Not yet in the public docs or model picker — keep using `universal-3-5-pro` |
| 4.37.0 | **LeMUR removed.** Use the LLM Gateway (§9) |
| 4.36.7 | `StreamingTranscriber.close()` no longer hangs when the socket closes without a `Termination` message; new optional `terminationTimeout` argument on `close()` (5000ms default, `0` waits indefinitely) |
| 4.36.6 | `effort` (`"low"` \| `"medium"`) on the Speech Understanding feature requests |
| 4.36.4 | `aac` streaming encoding; opt-in `sessionHeartbeat` streaming param with a `heartbeat` event |
| 4.36.3 | Targets the canonical `/v1` sync API routes |
| 4.36.2 | Opt-in `timestamps` sync config option (`SyncWord.start`/`end` are optional and absent unless requested) |
| 4.36.0 | `client.sync` — synchronous transcription (§10) |

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

`speech_models` is a priority list — if the first model cannot process the audio, the next one is used. The singular `speech_model` field rejects current model names with a 400 (its TypeScript union still lists only the legacy `best`/`nano`/`slam-1`/`universal` values), so use the plural field:

```typescript
const transcript = await client.transcripts.transcribe({
  audio: "https://example.com/audio.mp3",
  speech_models: ["universal-3-5-pro", "universal-2"],
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

The top-level `summarization: true` param is **deprecated**. Use Speech Understanding summarization instead — the SDK's transcript params accept `speech_understanding` directly, so you do NOT need raw fetch for this:

```typescript
const transcript = await client.transcripts.transcribe({
  audio: "https://example.com/audio.mp3",
  speaker_labels: true,
  speech_understanding: {
    request: {
      summarization: { summary_type: "bullets", effort: "low" },
    },
  },
});

console.log(transcript.speech_understanding?.response?.summarization?.summary);
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

`close()` waits for the server's `Termination` message. Since 4.36.7 that wait is bounded: the signature is `close(waitForSessionTermination = true, terminationTimeout = 5000)`, with `terminationTimeout` in milliseconds and `0` meaning wait indefinitely. The socket closes either way.

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
      model: "claude-sonnet-4-6",
      messages: [
        { role: "user", content: "Summarize this transcript..." },
      ],
    }),
  }
);

const data = await response.json();
console.log(data.choices[0].message.content);
```

---

## 10. Sync STT (Short-Form Audio, ≤120s)

`client.sync` is a `SyncTranscriber` wrapping the Sync STT API — one HTTP round trip, no polling. The model defaults to `universal-3-5-pro`:

```typescript
import { AssemblyAI } from "assemblyai";

const client = new AssemblyAI({ apiKey: process.env.ASSEMBLYAI_API_KEY! });

await client.sync.warm(); // optional: pre-establish the connection (idempotent, cheap)

const result = await client.sync.transcribe("/path/to/local/recording.wav", {
  prompt: "Customer voice message about an online order.",
  keyterms_prompt: ["AssemblyAI"],
  timestamps: true, // opt-in word-level start/end (ms)
});
console.log(result.text);
```

The first argument accepts a local file path, raw audio bytes, a Blob, or a readable stream — **not a URL**. The config (second argument) mirrors the REST `config` part: `model`, `prompt`, `keyterms_prompt`, `conversation_context`, `language_codes`, `timestamps`, and `sample_rate`/`channels` for raw PCM. Word `start`/`end` appear only when `timestamps: true`. The client-side request timeout defaults to 60s (see `SyncTranscribeOptions`). See `references/api-reference.md` §16 for limits and error codes.

---

## 11. Dictation (Short-Form Dictation, ≤120s, Transcript + Rewrite)

`client.dictation` is a `DictationTranscriber` wrapping the **Dictation API** (`dictation.assemblyai.com`) — a separate service from `client.sync` that returns the verbatim transcript **and** an LLM-cleaned, send-ready rewrite in one call. Cleanup runs by default; `llm_instruction` asks for a different shape.

**Version gate:** added in **4.40.0** (Sept 11, 2026); install the current **4.41.1**. Anything older (e.g. 4.37.x) has no `client.dictation` — check `npm ls assemblyai` in an existing project and fall back to the raw `fetch` example in `references/dictation.md` if it can't upgrade yet.

```typescript
import { AssemblyAI } from "assemblyai";

const client = new AssemblyAI({
  apiKey: process.env.ASSEMBLYAI_API_KEY!,
  // dictationBaseUrl: "https://dictation.eu.assemblyai.com", // US/EU data residency
});

await client.dictation.warm(); // optional: as soon as you know audio is coming (idempotent)

const result = await client.dictation.transcribeLive("/path/to/local/recording.wav", {
  stt_prompt: "A doctor dictating a patient visit note.", // context, not instructions (≤6000 chars)
  keyterms_prompt: ["amoxicillin", "lisinopril", "metoprolol"], // ≤100 terms / 8000 chars
  llm_instruction: "Remove filler words and rewrite as a concise clinical chart note.", // ≤2048 chars
});

console.log(result.text); // verbatim transcript — never altered by the LLM
console.log(result.llm_response); // the rewrite, or null if the best-effort rewrite failed
console.log(result.final_text); // llm_response ?? text (derived by the SDK)
```

- `transcribeLive(audio, config?, options?)` accepts a local path, a data URL, `Uint8Array`/`ArrayBuffer`, `Blob`/`File`, a web `ReadableStream`, a Node stream, or any (async) iterable of `Uint8Array` chunks — the request starts immediately and uploads as chunks arrive. **Not an http(s) URL** (throws; use `client.transcripts` for URLs). `options`: `{ timeout?: number /* default 300_000 ms for the whole request */, signal?: AbortSignal }`.
- `openLive(config?, options?)` is the **push-style** counterpart for callback-driven sources — returns a `DictationLiveSession`: `session.write(chunk)` (never blocks), `session.close()` ends the audio, `await session.result()` resolves the `DictationResponse`, `session.abort()` drops the request.
- **Raw PCM** needs `sample_rate` **and** `channels` in the config (setting either marks the audio as PCM and both become required); leave both unset for WAV. Compressed formats are rejected by the service with `415`.
- `DictationConfig` is exactly `{ sample_rate, channels, language_codes, stt_prompt, keyterms_prompt, llm_instruction }` — **no** `model`, `prompt`, `timestamps`, or `conversation_context` (those are `client.sync`). Caps are validated client-side; keyterms are trimmed and empties dropped.
- `DictationResponse`: `text`, `words[{text, confidence}]` (no timestamps), `confidence`, `llm_response`, `llm_error`, `audio_duration_ms`, `session_id`, `request_time_ms`, `sync_time_ms`, plus the SDK-derived `final_text`. Never treat a non-null `llm_error` as a failed request.
- Failures throw `DictationError` (`.status`, `.errorCode`, `.retryAfter`). Auth, rate-limit, size and capacity errors can surface **mid-upload**.

```typescript
import { AssemblyAI } from "assemblyai";

const client = new AssemblyAI({ apiKey: process.env.ASSEMBLYAI_API_KEY! });

// Push-style: raw S16LE PCM from a microphone callback.
const session = client.dictation.openLive({ sample_rate: 16000, channels: 1 });
mic.on("data", (chunk) => session.write(chunk));
mic.on("end", () => session.close());
const { final_text } = await session.result();
console.log(final_text);
```

See `references/dictation.md` for the endpoint, config limits, error shapes, and the raw-`fetch` fallback.
