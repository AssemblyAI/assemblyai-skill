# Voice Agent Integrations

AssemblyAI supports four paths for building voice agents:

1. **Speech-to-Speech API** — single WebSocket for full voice agent (speech-in → LLM → speech-out)
2. **LiveKit Agents** — fastest path to deployment using U3 Pro STT
3. **Pipecat (by Daily)** — open-source, maximum customizability using U3 Pro STT
4. **Direct WebSocket** — fully custom STT builds (see `streaming.md`)

## Voice Agent API

AssemblyAI's Voice Agent API is a single WebSocket that handles the full voice agent loop: speech-in → LLM → speech-out. It includes built-in turn detection, TTS, tool calling, and barge-in handling.

### Connection

```
wss://agents.assemblyai.com/v1/ws
Authorization: Bearer YOUR_API_KEY
```

**EU endpoint:** `wss://agents.eu.assemblyai.com/v1/ws` (AWS eu-west-1, Dublin) for EU data residency.

For browser-based clients, generate a [temporary token](https://www.assemblyai.com/docs/voice-agents/voice-agent-api/browser-integration) and pass it as a query parameter instead: `wss://agents.assemblyai.com/v1/ws?token=YOUR_TEMP_TOKEN`.

### Audio Format

All audio exchanged is **base64-encoded, mono**. The encoding determines the sample rate. Input and output encodings are configured independently under `session.input.format` and `session.output.format`.

| Encoding       | Sample rate  | Bit depth                            | Best for                                   |
| -------------- | ------------ | ------------------------------------ | ------------------------------------------ |
| `audio/pcm`    | 24,000 Hz    | 16-bit signed int (little-endian)    | Default — highest quality, browser/desktop |
| `audio/pcmu`   | 8,000 Hz     | 8-bit μ-law                          | Telephony (G.711 μ-law)                    |
| `audio/pcma`   | 8,000 Hz     | 8-bit A-law                          | Telephony (G.711 A-law)                    |

Defaults to `audio/pcm` (24 kHz) on both input and output if omitted. ~50ms chunks work well.

### Client Events

| Event | Description |
|-------|-------------|
| `input.audio` | Send audio chunk: `{"type": "input.audio", "audio": "<base64>"}` |
| `session.update` | Configure session: `system_prompt`, `greeting`, `tools`, `input` (format/keyterms/turn_detection), `output` (voice/format/volume) |
| `session.resume` | Reconnect to an existing session: `{"type": "session.resume", "session_id": "..."}` |
| `tool.result` | Return tool call result back to the agent: `{"type": "tool.result", "call_id": "...", "result": "<JSON string>"}` |
| `reply.create` | Ask the agent to generate a reply right now, optionally with one-shot `instructions`: `{"type": "reply.create", "instructions": "Tell the user we're still processing."}`. Primarily used to deliver status updates during a `hold`-mode tool call |

### Server Events

| Event | Description |
|-------|-------------|
| `session.ready` | Session is initialized; includes `session_id` (always present) for `session.resume` |
| `session.updated` | Session configuration has been updated |
| `input.speech.started` | Turn detection determined the user has started speaking (for barge-in) |
| `input.speech.stopped` | Turn detection determined the user has stopped speaking |
| `transcript.user.delta` | Partial user transcript |
| `transcript.user` | Final user transcript with `item_id` |
| `reply.started` | Agent is starting a reply (includes `reply_id`) |
| `reply.audio` | Agent audio chunk (base64-encoded in configured output encoding) |
| `transcript.agent` | Agent's reply text with `interrupted` boolean (true if user barged in) |
| `reply.done` | Agent reply complete; optional `status: "interrupted"` if user barged in |
| `tool.call` | Agent wants to call a tool — payload includes `call_id`, `name`, `arguments` (dict, **not** `args`) |
| `session.error` | Connection / handshake / message validation error — see error code table below |

### Session Resume

Sessions are preserved for **30 seconds** after disconnection. Reconnect using `session.resume` with the session ID to continue without losing context.

### Example session.update

**Note:** Voice Agent `session.update` wraps all config under a `"session"` key. Tool definitions use a **flat format** (not the nested `function` object used by the LLM Gateway). All fields are optional — only include what you want to set.

```json
{
  "type": "session.update",
  "session": {
    "system_prompt": "You are a helpful customer support agent for Acme Corp.",
    "greeting": "Hello! How can I help you today?",
    "input": {
      "format": { "encoding": "audio/pcm" },
      "keyterms": ["Acme", "OrderPro"],
      "turn_detection": {
        "vad_threshold": 0.5,
        "min_silence": 1000,
        "max_silence": 3000,
        "interrupt_response": true
      }
    },
    "output": {
      "voice": "ivy",
      "format": { "encoding": "audio/pcm" },
      "volume": 100
    },
    "tools": [
      {
        "type": "function",
        "name": "lookup_order",
        "description": "Look up an order by order ID. Call this whenever the user references an order, asks for status, or wants to make changes to an existing order.",
        "parameters": {
          "type": "object",
          "properties": {
            "order_id": {"type": "string", "description": "The order ID, e.g. ORD-12345"}
          },
          "required": ["order_id"]
        },
        "execution_mode": "interactive",
        "timeout_seconds": 120
      }
    ]
  }
}
```

### Tool Definition Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `type` | string | (required) | Always `"function"` |
| `name` | string | (required) | snake_case, verb-noun. Referenced by `tool.call` |
| `description` | string | `""` | The model's main signal for **when** to call. State the trigger ("Call this when the user asks about X"); weak descriptions are the #1 cause of tools not being called |
| `parameters` | object | `{}` | JSON Schema. **NOT validated at `session.update` time** — malformed schemas are accepted silently and break tool calling at runtime |
| `execution_mode` | string | `"interactive"` | `"interactive"` (agent fills wait with transition phrase) or `"hold"` (agent silent; user replies suppressed). Interactive for sub-5s tools; hold for >10s, transfers, payment |
| `timeout_seconds` | number | `120` | 1–300. On timeout the agent apologises; the session continues |

`session.tools` updates **replace** the previous array (not merge). Pattern: progressive tool reveal — start with minimal tools, add the next phase's tools after each successful `tool.result`.

### Mutability After `session.ready`

| Field | Mutable? |
|-------|----------|
| `system_prompt`, `input.turn_detection`, `input.keyterms` (up to 100 strings), `input.format`, `tools`, `output.volume` | **Yes** |
| `greeting`, `output.voice`, `output.format` | **No** — raises `immutable_field` |

**Greeting goes straight to TTS, NOT through the LLM.** Whatever string you set is exactly what the user hears, word for word. Don't write meta-greetings like "Greet the user warmly and ask how you can help" — the TTS will literally speak that sentence.

### Voice Agent Turn Detection

All fields under `session.input.turn_detection` — **note the field names differ from the streaming/LiveKit/Pipecat APIs**:

| Field                | Type    | Default | Description                                                                |
| -------------------- | ------- | ------- | -------------------------------------------------------------------------- |
| `vad_threshold`      | float   | `0.5`   | Speech detection sensitivity (0.0–1.0). Lower = more sensitive to speech.  |
| `min_silence`        | integer | `1000`  | Minimum silence to consider a confident end-of-turn, in milliseconds.      |
| `max_silence`        | integer | `3000`  | Maximum silence before forcing end-of-turn, in milliseconds.               |
| `interrupt_response` | boolean | `true`  | Whether user speech interrupts the agent. Set `false` to disable barge-in. |

### Tool Call Pattern

**Rule: send `tool.result` when `reply.done` is the latest event you've received.** Not earlier (the agent is still mid-transition-phrase), not later (a new `reply.started` or `input.speech.started` means a turn has begun). The cleanest implementation tracks `last_event` and flushes whenever the rule holds — this handles both fast tools (drain on `reply.done`) and slow tools (drain on `tool.call` completion when `reply.done` already fired).

```python
last_event = None
pending_tools = []

async def flush_if_idle():
    if last_event != "reply.done" or not pending_tools:
        return
    for tool in pending_tools:
        await ws.send(json.dumps({
            "type": "tool.result",
            "call_id": tool["call_id"],
            "result": json.dumps(tool["result"]),  # JSON string
        }))
    pending_tools.clear()

if t == "tool.call":
    name = event["name"]
    arguments = event.get("arguments", {})  # dict — NOT "args"
    result = run_tool(name, arguments)
    pending_tools.append({"call_id": event["call_id"], "result": result})
    await flush_if_idle()  # slow-tool case: reply.done may already have fired

elif t in ("reply.started", "input.speech.started"):
    last_event = t  # turn in flight — hold results

elif t == "reply.done":
    last_event = t
    if event.get("status") == "interrupted":
        pending_tools.clear()  # discard — user barged in
    else:
        await flush_if_idle()
```

### Execution Modes

`execution_mode` on each tool definition controls how the agent waits:

| `"interactive"` (default) | `"hold"` |
|--------------------------|----------|
| Agent speaks a short transition phrase ("let me check that") while the tool runs, then delivers the result conversationally | Agent stays silent while the tool runs; user-triggered replies are suppressed |
| DB lookups, REST calls, short calculations | Phone transfers, escalations, payment auth, long async jobs |
| Returns under ~5 seconds | Returns >10 seconds |

**Hold-mode rules:**
- The agent emits NO `reply.started` while held — sending audio looks like dead air to the user.
- `tool.result` **auto-fires** the next reply. **Do NOT also send `reply.create` after** — that produces a duplicate reply.
- Send `reply.create` (with optional `instructions`) DURING the hold to deliver status updates.
- `transcript.user.delta` / `transcript.user` are NOT emitted in real time during a hold — they flush when the hold ends.

```json
{
  "type": "function",
  "name": "transfer_call",
  "description": "Transfer the call to a human agent. Takes 15-30 seconds.",
  "parameters": {"type": "object", "properties": {"department": {"type": "string"}}, "required": ["department"]},
  "execution_mode": "hold",
  "timeout_seconds": 60
}
```

### Output Volume

`session.output.volume` accepts `0` (silent) to `100` (loudest). Unlike `voice` and `format`, **`volume` can be updated mid-session**. Send another `session.update` with a new value at any time; the change applies to subsequent `reply.audio` chunks.

### Handling Interruptions (Barge-In)

On user barge-in, the server emits `reply.done` with `status: "interrupted"` and `transcript.agent` with `interrupted: true`. Your client should flush the audio playback buffer and restart the output stream:

| Platform           | Flush approach                                                                                   |
| ------------------ | ------------------------------------------------------------------------------------------------ |
| **Python** (sounddevice) | `speaker.abort()` then `speaker.start()`                                                   |
| **Web** (AudioContext)   | Disconnect the source node, create a new `AudioBufferSourceNode`, reconnect              |
| **iOS** (AVAudioEngine)  | `playerNode.stop()` then `playerNode.play()`                                              |
| **Android** (AudioTrack) | `audioTrack.pause()`, `audioTrack.flush()`, then `audioTrack.play()`                      |

For browser apps, enable echo cancellation via `getUserMedia({ audio: { echoCancellation: true, noiseSuppression: false } })`. **Disable** browser-level `noiseSuppression` and skip Krisp/RNNoise/BVC — the Voice Agent API runs server-side voice focus (noise cancellation) by default; stacking client-side denoising on top adds artifacts that hurt accuracy more than the original noise. For terminal/desktop apps, use headphones — native audio APIs (PortAudio, sounddevice) don't include AEC.

### Available Voices

Set a voice via `session.output.voice` in `session.update` **before `session.ready`**. `output.voice` and `output.format` are immutable once the session is established — the voice **cannot be changed mid-conversation**. (`output.volume` is the exception — it remains mutable.) Default is `ivy`.

**English voices** (US unless noted):
`ivy`, `james`, `tyler`, `autumn`, `sam`, `mia`, `bella`, `david`, `jack`, `kyle`, `helen`, `martha`, `river`, `emma`, `victor`, `eleanor`; `sophie`, `oliver` (UK)

**Multilingual voices** (also speak English with code-switching):
`arjun` (Hindi/Hinglish), `ethan`/`mei` (Mandarin), `dmitri` (Russian), `lukas`/`lena` (German), `pierre` (French), `mina`/`joon` (Korean), `ren`/`hana` (Japanese), `giulia`/`luca` (Italian), `lucia`/`mateo` (Spanish), `diego` (Colombian Spanish)

```json
{"type": "session.update", "session": {"output": {"voice": "ivy"}}}
```

### Voice Agent Error Codes

`session.error` payloads include `code`, `message`, and `timestamp`. Some validation errors also include `param`.

| Code                | Phase                           | Meaning                                                          |
| ------------------- | ------------------------------- | ---------------------------------------------------------------- |
| `UNAUTHORIZED`      | Connection (closes 1008)        | Missing or invalid `Authorization` token                         |
| `FORBIDDEN`         | Connection (closes 1008)        | Valid token, insufficient permissions                            |
| `INTERNAL_ERROR`    | Connection (closes 1011)        | Unexpected exception during connection setup                     |
| `session_not_found` | `session.resume` (closes 1008)  | Unknown `session_id` or 30-second grace window expired           |
| `session_forbidden` | `session.resume` (closes 1008)  | `session_id` belongs to a different account                      |
| `session_expired`   | Live (closes 1008)              | Session TTL elapsed                                              |
| `agent_init_failed` | After upgrade, before ready     | Agent worker reported initialization failure                     |
| `agent_timeout`     | After upgrade, before ready     | Agent did not signal ready within 10 seconds                     |
| `invalid_format`    | Live (session stays open)       | Bad JSON, missing/unknown `type`, validation failure             |
| `invalid_audio`    | Live (session stays open)       | `input.audio` payload failed base64/PCM decode                   |
| `invalid_value`     | Live (session stays open)       | `session.update` with invalid voice or field type                |
| `immutable_field`   | Live (session stays open)       | Tried to change `greeting` or `output` after first update applied |
| `invalid_config`    | Live (session stays open)       | `session.update` raised a validation error                       |

In browsers, pre-handshake failures (like `UNAUTHORIZED`) surface as `close` event with code `1006` — no `session.error` payload arrives. Always fetch a fresh temporary token immediately before each connection attempt.

---

## Recommended Model (STT-based paths)

**`u3-rt-pro`** (Universal-3 Pro Streaming) is the recommended model for all new voice agent work.

| Feature | u3-rt-pro | universal-streaming-english | universal-streaming-multilingual |
|---------|-----------|------------------------------|----------------------------------|
| Turn detection | Punctuation-based | Confidence-based | Confidence-based |
| Custom prompting (beta) | Yes | No | No |
| Keyterms boosting | Yes | Yes | Yes |
| Speaker diarization | Yes | Yes | Yes |
| Dynamic mid-session updates | Yes | Yes | Yes |
| Multilingual code switching | Yes | No | Yes |
| Languages | 6 (en, es, fr, de, it, pt) | English only | Multiple |

`end_of_turn_confidence_threshold` does NOT work with u3-rt-pro — it only applies to older universal-streaming models.

## Turn Detection (u3-rt-pro)

1. User pauses for `min_turn_silence` (e.g., 100ms)
2. Model checks for terminal punctuation (`.` `?` `!`)
3. If found: turn ends immediately (`end_of_turn: true`)
4. If not found: partial emitted, listening continues
5. If silence reaches `max_turn_silence`: turn forced to end regardless

## Silence Settings by Use Case

These are for **Universal Streaming** models. U3 Pro defaults differ.

| Profile | min_turn_silence | max_turn_silence | Use Case |
|---------|-----------------|-----------------|----------|
| **Aggressive** | 160ms | 400ms | IVR, yes/no, quick confirmations |
| **Balanced** | 400ms | 1280ms | Most voice agents (recommended default) |
| **Conservative** | 800ms | 3600ms | Healthcare, complex speech, long pauses |

Low `min_turn_silence` can split entities (phone numbers, emails) across turns. Dynamically increase `max_turn_silence` to 2000-3000ms during entity collection phases, then reduce it afterward.

---

## LiveKit Integration

### Setup

```bash
# For u3-rt-pro (requires livekit-agents >= 1.4.4)
pip install "livekit-agents[assemblyai,silero,codecs]~=1.5" python-dotenv
# If using MultilingualModel turn detection, also install:
pip install "livekit-plugins-turn-detector~=1.0"
```

Required env vars: `ASSEMBLYAI_API_KEY`, `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, plus LLM/TTS provider keys.

### Turn Detection Modes

#### STT-based (recommended for u3-rt-pro)

```python
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, TurnHandlingOptions
from livekit.plugins import assemblyai, silero

load_dotenv()

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful voice AI assistant.")

async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()
    session = AgentSession(
        turn_handling=TurnHandlingOptions(
            turn_detection="stt",
            endpointing={"min_delay": 0},  # CRITICAL: avoid additive 500ms delay
        ),
        stt=assemblyai.STT(
            model="u3-rt-pro",
            min_turn_silence=100,
            max_turn_silence=1000,
            vad_threshold=0.3,
        ),
        vad=silero.VAD.load(activation_threshold=0.3),
    )
    await session.start(room=ctx.room, agent=Assistant())
    await session.generate_reply(instructions="Greet the user and offer your assistance.")

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
```

Run with `python voice_agent.py dev`, test at `https://agents-playground.livekit.io/`.

#### MultilingualModel (LiveKit's own turn detection)

```python
from livekit.agents import AgentSession, TurnHandlingOptions
from livekit.plugins.turn_detector.multilingual import MultilingualModel

session = AgentSession(
    turn_handling=TurnHandlingOptions(
        turn_detection=MultilingualModel(),
        endpointing={"min_delay": 0.5, "max_delay": 3.0},
    ),
    stt=assemblyai.STT(model="u3-rt-pro", vad_threshold=0.3),
    vad=silero.VAD.load(activation_threshold=0.3),
)
```

Other modes: **VAD-only** (purely silence-based) and **Manual** (explicit `session.commit_user_turn()`, `session.clear_user_turn()`, `session.interrupt()`).

### LiveKit Pitfalls

| Pitfall | Fix |
|---------|-----|
| `max_turn_silence` defaults to **100ms** in LiveKit plugin (API default is 1000ms) | Always set `max_turn_silence=1000` explicitly in STT mode |
| `endpointing.min_delay` adds **500ms** on top of AssemblyAI endpointing | Set `endpointing={"min_delay": 0}` inside `TurnHandlingOptions` in STT mode |
| Silero VAD default threshold is 0.5, AssemblyAI default is 0.3 | Set both to 0.3 — mismatch creates a dead zone delaying interruption |
| u3-rt-pro requires livekit-agents >= 1.4.4 | Check version before debugging |
| Old API: `turn_detection="stt"` directly on `AgentSession` | Use `turn_handling=TurnHandlingOptions(turn_detection="stt", ...)` (livekit-agents v1.5+) |

---

## Pipecat Integration

### Setup

```bash
pip install "pipecat-ai[assemblyai,openai,cartesia]"
# or swap providers:
pip install "pipecat-ai[assemblyai,anthropic,elevenlabs]"
```

### Turn Detection Modes

#### Pipecat-controlled (default, recommended)

```python
from pipecat.services.assemblyai.stt import AssemblyAISTTService
from pipecat.services.assemblyai.config import AssemblyAIConnectionParams

stt = AssemblyAISTTService(
    api_key=os.getenv("ASSEMBLYAI_API_KEY"),
    connection_params=AssemblyAIConnectionParams(
        speech_model="u3-rt-pro",
        min_turn_silence=100,
    ),
    vad_force_turn_endpoint=True,  # Default — Pipecat controls turns
)
```

In Pipecat mode, VAD + Smart Turn analyzer controls endpointing. `max_turn_silence` auto-syncs with `min_turn_silence`. A `ForceEndpoint` message is sent to AssemblyAI when silence is detected.

#### AssemblyAI's built-in turn detection

```python
stt = AssemblyAISTTService(
    api_key=os.getenv("ASSEMBLYAI_API_KEY"),
    connection_params=AssemblyAIConnectionParams(
        speech_model="u3-rt-pro",
        min_turn_silence=100,
        max_turn_silence=1000,
    ),
    vad_force_turn_endpoint=False,  # AssemblyAI controls turns
)
```

### Keyterms Boosting

```python
stt = AssemblyAISTTService(
    api_key=os.getenv("ASSEMBLYAI_API_KEY"),
    connection_params=AssemblyAIConnectionParams(
        speech_model="u3-rt-pro",
        min_turn_silence=100,
        keyterms_prompt=["Xiomara", "Saoirse", "Pipecat", "AssemblyAI"],
    ),
)
```

### Dynamic Mid-Session Updates

```python
from pipecat.frames.frames import STTUpdateSettingsFrame
from pipecat.services.assemblyai.stt import AssemblyAISTTSettings

await task.queue_frame(
    STTUpdateSettingsFrame(
        delta=AssemblyAISTTSettings(
            connection_params=AssemblyAIConnectionParams(
                keyterms_prompt=["NewName", "NewCompany"],
                min_turn_silence=200,
                max_turn_silence=3000,
            )
        )
    )
)
```

### Speaker Diarization

```python
stt = AssemblyAISTTService(
    api_key=os.getenv("ASSEMBLYAI_API_KEY"),
    connection_params=AssemblyAIConnectionParams(
        speech_model="u3-rt-pro",
        speaker_labels=True,
    ),
    speaker_format="<Speaker {speaker}>{text}</Speaker {speaker}>",
)
```

### Pipecat Pitfall

`keyterms_prompt` and `prompt` cannot be used simultaneously — choose one.

---

## Barge-In / Interruption Handling

Monitor `SpeechStarted` events from AssemblyAI:
```json
{"type": "SpeechStarted", "timestamp": 14400, "confidence": 0.79}
```

On detection: stop TTS playback immediately, switch to listening mode, wait for full turn before responding.

---

## Dynamic Configuration by Conversation Stage

Both frameworks support updating parameters mid-session without reconnecting:

| Stage | Configuration |
|-------|--------------|
| Caller identification | Boost specific names via `keyterms_prompt` |
| Entity dictation (email, phone) | Increase `max_turn_silence` to 3000ms |
| Yes/no questions | Use prompt anticipating short responses |
| Payment collection | Boost card brand terms + extend silence |

---

## Latency Optimization

1. **Set `min_endpointing_delay=0`** in LiveKit STT mode — default 500ms is additive
2. **Use 16kHz sample rate** — higher rates don't improve accuracy
3. **Synchronize VAD thresholds** — set both local VAD and AssemblyAI `vad_threshold` to 0.3
4. **Avoid audio preprocessing/noise cancellation** before sending to AssemblyAI — artifacts cause more harm than background noise
5. **Only enable features you need** — skip `speaker_labels` unless required
6. **Use dynamic configuration** to adjust silence only when needed

### Latency Breakdown

| Component | Latency |
|-----------|---------|
| Network transmission | ~50ms |
| Speech-to-text processing | 200-300ms (sub-300ms P50) |
| `min_turn_silence` check | 100ms+ (configurable) |
| `max_turn_silence` fallback | 1000ms+ (only if no terminal punctuation) |

---

## Telnyx Telephony Integration

### Via LiveKit
SIP trunking routes phone calls into LiveKit rooms. Configure inbound/outbound trunks and dispatch rules.

### Via Pipecat
WebSocket media streaming with TeXML. **Critical: Telnyx uses 8kHz audio**, not 16kHz:

```python
transport = TelnyxTransport(
    # ...
    audio_in_sample_rate=8000,
    audio_out_sample_rate=8000,
)
```

---

## Scaling

- Free tier: 5 new streams/minute
- Pay-as-you-go: 100 new streams/minute
- No hard cap on concurrent streams
- Automatic 10% capacity increase every 60 seconds at 70%+ utilization

---

## Accuracy Enhancement Priority

1. **Keyterms prompting** (highest impact) — up to 100 terms, max 50 chars each
2. **Dynamic configuration updates** — contextual adaptation per conversation stage
3. **Silence threshold tuning** — entity preservation
4. **Avoid preprocessing noise cancellation** — artifacts hurt more than noise
