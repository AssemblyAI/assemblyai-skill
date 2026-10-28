# Voice Agent Integrations

AssemblyAI supports three paths for building voice agents on its streaming speech-to-text (Universal-3.6 Pro):

1. **LiveKit Agents** — fastest path to deployment
2. **Pipecat (by Daily)** — open-source, maximum customizability
3. **Direct WebSocket** — fully custom STT builds (see `streaming.md`)

## Reference Voice Agents

Start from these maintained reference agents, which wire AssemblyAI streaming STT, LLM Gateway and AssemblyAI text-to-speech into each framework, with turn detection, browser and phone calling, tests and deployment:

- **LiveKit:** https://github.com/AssemblyAI-Solutions/assemblyai-livekit-reference-voice-agent
- **Pipecat:** https://github.com/AssemblyAI-Solutions/assemblyai-pipecat-reference-voice-agent

Read the matching repo before building a LiveKit or Pipecat agent from scratch, and follow its setup and versions. The sections below cover the STT configuration those agents rely on.

## Recommended Model

**`universal-3-6-pro`** (Universal-3.6 Pro Streaming, Sept 29, 2026) is the recommended default model for new STT-based voice agent work. The raw streaming API defaults to it when `speech_model` is omitted, and so does the Python LiveKit plugin from 1.8.4, but **Pipecat (`pipecat-ai` 1.12) and the Node LiveKit plugin (`@livekit/agents-plugin-assemblyai` 1.9) still default to `universal-3-5-pro`**, so always pass the model explicitly. `universal-3-5-pro` remains fully supported with the same features (19 languages).

| Feature | universal-3-6-pro | universal-streaming-english | universal-streaming-multilingual |
|---------|-------------------|------------------------------|----------------------------------|
| Turn detection | Punctuation-based | Confidence-based | Confidence-based |
| Custom prompting | Yes | No | No |
| Keyterms boosting | Yes | Yes | Yes |
| Speaker diarization | Yes | Yes | Yes |
| Dynamic mid-session updates | Yes | Yes | Yes |
| Multilingual code switching | Yes | No | Yes |
| Languages | 32 (af, ar, yue, ca, da, nl, en, et, fi, fr, gl, de, he, hi, it, ja, ko, zh, mr, no, nn, fa, pt, ro, ru, es, sv, tr, ur, vi, xh, zu) | English only | 6 (en, es, de, fr, pt, it) |

(`u3-rt-pro` / Universal-3 Pro Streaming was removed from the streaming model picker and spec enum in July 2026 — superseded by the Universal-3.5/3.6 Pro models.)

`end_of_turn_confidence_threshold` and `format_turns` do NOT work with `universal-3-6-pro`/`universal-3-5-pro`; they only apply to the Universal Streaming (English/Multilingual) models.

## Turn Detection (universal-3-6-pro)

1. User pauses for `min_turn_silence` (e.g., 100ms)
2. Model checks for terminal punctuation (`.` `?` `!`)
3. If found: turn ends immediately (`end_of_turn: true`)
4. If not found: partial emitted, listening continues
5. If silence reaches `max_turn_silence`: turn forced to end regardless

API defaults come from `mode` (min/max turn silence): `min_latency` 128/640ms, `balanced` 128/1280ms (default), `max_accuracy` 512/2560ms (holds turns open longer so entities aren't split). See `streaming.md` → Turn Detection.

## Silence Settings by Use Case

These are for **Universal Streaming** models. Universal-3.6/3.5 Pro defaults come from the `mode` preset above (640/768ms with `speaker_labels`).

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
# universal-3-6-pro needs livekit-agents / livekit-plugins-assemblyai 1.8.0+
# (LiveKit Inference "assemblyai/universal-3-6-pro" needs 1.8.3+;
# the plugin defaults to universal-3-6-pro from 1.8.4).
pip install "livekit-agents[assemblyai,silero,codecs]~=1.8" python-dotenv
# If using MultilingualModel turn detection, also install:
pip install "livekit-plugins-turn-detector~=1.0"
```

Required env vars: `ASSEMBLYAI_API_KEY`, `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, plus LLM/TTS provider keys.

### Turn Detection Modes

#### STT-based (recommended for universal-3-6-pro)

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
            model="universal-3-6-pro",  # explicit: plugin releases before 1.8.4 default to universal-3-5-pro
            mode="balanced",  # use the API's preset (128/1280ms) instead of the plugin's 100ms windows
            vad_threshold=0.3,
            # continuous_partials defaults to True: ~1s partials during long turns. Set False for ~3s.
            # interruption_delay=0,  # Optional: faster first partial (256ms effective). Default 500 (756ms effective).
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
    stt=assemblyai.STT(model="universal-3-6-pro", vad_threshold=0.3),
    vad=silero.VAD.load(activation_threshold=0.3),
)
```

Other modes: **VAD-only** (purely silence-based) and **Manual** (explicit `session.commit_user_turn()`, `session.clear_user_turn()`, `session.interrupt()`).

### LiveKit Pitfalls

| Pitfall | Fix |
|---------|-----|
| The plugin sends **100ms** `min_turn_silence`/`max_turn_silence` on U3 Pro models unless you set `mode` (API `balanced` default is 128/1280ms). `max_turn_silence` has no default of its own: when unset, the plugin sends it equal to `min_turn_silence`, even with `mode` set | In STT mode, pass `mode="balanced"` (the plugin then drops its 100ms windows) or set both silences explicitly (e.g. `min_turn_silence=128, max_turn_silence=1280`). Don't set only `min_turn_silence` |
| `endpointing.min_delay` adds **500ms** on top of AssemblyAI endpointing | Set `endpointing={"min_delay": 0}` inside `TurnHandlingOptions` in STT mode |
| Silero VAD default threshold is 0.5, AssemblyAI's U3 Pro default is 0.2 | Set both to 0.3 (`vad_threshold=0.3` on the STT, `activation_threshold=0.3` on Silero). A mismatch creates a dead zone that delays interruption |
| `universal-3-6-pro` rejected with a validation error | Needs `livekit-agents`/`livekit-plugins-assemblyai` **1.8.0+** (LiveKit Inference `stt="assemblyai/universal-3-6-pro"` needs **1.8.3+**). The Python plugin's `model` default is `universal-3-6-pro` from 1.8.4 (earlier releases and the Node plugin default to `universal-3-5-pro`), so pass it explicitly |
| Old API: `turn_detection="stt"` directly on `AgentSession` | Use `turn_handling=TurnHandlingOptions(turn_detection="stt", ...)` (livekit-agents v1.5+) |
| `continuous_partials` defaults to **`true`** (both the API and the LiveKit plugin, as of June 2026) | ~1s partials during long turns. `continuous_partials=False` slows mid-turn partials to ~3s |
| Want faster barge-in / TTFT | Lower `interruption_delay` (default `500` → 756ms effective); `interruption_delay=0` → 256ms effective first partial (the server adds a fixed 256ms) |
| `mode`, `voice_focus`, `previous_context_n_turns` changed via `update_options()` | Connect-time only in the plugin; set them on `assemblyai.STT(...)` |

You can update `prompt`, `keyterms_prompt`, `min_turn_silence`, `max_turn_silence`, `continuous_partials`, and `interruption_delay` mid-session via `stt.update_options(...)` — e.g. raise `max_turn_silence` during entity dictation, or lower `interruption_delay` when the agent is speaking for faster barge-in.

LiveKit automatically forwards the agent's spoken replies to the STT as `agent_context` (on by default, livekit-agents 1.6.6+, and on LiveKit Inference 1.8.3+), so the STT knows what question the user is answering (see Context Carryover in `streaming.md`). Opt out with `AgentSession(..., stt_context_options={"forward_chat_context": False})`. The plugin's old `agent_context_carryover` param is **deprecated**. `language_codes` (max 10) is plugin-only; LiveKit Inference doesn't take it yet.

---

## Pipecat Integration

### Setup

```bash
# universal-3-6-pro needs pipecat-ai 1.9.0+; steering language_codes across all 32 languages needs 1.11.0+
pip install "pipecat-ai[assemblyai,openai,cartesia]>=1.11"
# or swap providers:
pip install "pipecat-ai[assemblyai,anthropic,elevenlabs]>=1.11"
```

Configure the service with `settings=AssemblyAISTTService.Settings(...)`. The older `connection_params=AssemblyAIConnectionParams(...)` is **deprecated** (removed in Pipecat 2.0), and it can't carry newer fields like `mode`, `voice_focus`, `language_codes`, or `agent_context`. The service's `model` default is still `universal-3-5-pro` (as of `pipecat-ai` 1.12), so **pass `model="universal-3-6-pro"`**.

### Turn Detection Modes

#### AssemblyAI's built-in turn detection (recommended)

```python
import os

from pipecat.services.assemblyai.stt import AssemblyAISTTService

stt = AssemblyAISTTService(
    api_key=os.getenv("ASSEMBLYAI_API_KEY"),
    settings=AssemblyAISTTService.Settings(
        model="universal-3-6-pro",
        mode="balanced",  # or set min_turn_silence / max_turn_silence explicitly
    ),
    vad_force_turn_endpoint=False,  # AssemblyAI controls turns
)
```

#### Pipecat-controlled (Pipecat's default)

```python
stt = AssemblyAISTTService(
    api_key=os.getenv("ASSEMBLYAI_API_KEY"),
    settings=AssemblyAISTTService.Settings(
        model="universal-3-6-pro",
        min_turn_silence=100,
    ),
    vad_force_turn_endpoint=True,  # Default — Pipecat's VAD + Smart Turn control turns
)
```

In Pipecat mode, VAD + Smart Turn analyzer controls endpointing. `max_turn_silence` is always forced equal to `min_turn_silence`, and a `ForceEndpoint` message is sent to AssemblyAI when VAD detects silence.

### Keyterms and Prompting

```python
stt = AssemblyAISTTService(
    api_key=os.getenv("ASSEMBLYAI_API_KEY"),
    settings=AssemblyAISTTService.Settings(
        model="universal-3-6-pro",
        keyterms_prompt=["Xiomara", "Saoirse", "Pipecat", "AssemblyAI"],
        prompt="Dental office scheduling call.",  # combinable with keyterms_prompt on U3 Pro models
    ),
)
```

### Dynamic Mid-Session Updates

```python
from pipecat.frames.frames import STTUpdateSettingsFrame

await task.queue_frame(
    STTUpdateSettingsFrame(
        delta=AssemblyAISTTService.Settings(
            keyterms_prompt=["NewName", "NewCompany"],
            min_turn_silence=200,
            max_turn_silence=3000,
        )
    )
)
```

In `pipecat-ai` 1.12, only `agent_context` and `language_codes` are applied **live**, via `UpdateConfiguration`. Changing any other setting (keyterms, prompt, silences, `mode`, …) makes the service **reconnect** the WebSocket, which drops the server-side conversation history. The last `agent_context` is re-seeded on reconnect.

### Speaker Diarization

```python
stt = AssemblyAISTTService(
    api_key=os.getenv("ASSEMBLYAI_API_KEY"),
    settings=AssemblyAISTTService.Settings(
        model="universal-3-6-pro",
        speaker_labels=True,
    ),
    speaker_format="<Speaker {speaker}>{text}</Speaker {speaker}>",
)
```

### Pipecat Pitfalls

- `prompt` and `keyterms_prompt` **can** be combined on U3 Pro models (`universal-3-6-pro`/`universal-3-5-pro`); older Pipecat releases rejected the combination client-side. On Universal Streaming models only `keyterms_prompt` applies.
- The agent's replies are fed back as `agent_context` **automatically** by Pipecat's context aggregator. Set `agent_context` in `Settings` only to seed the opening line, and call `update_agent_context()` only in custom pipelines. `previous_context_n_turns=0` disables the automatic feed. The plugin clips `agent_context` to ~1500 characters.

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

## Telephony Integration

Phone calls reach a voice agent through the framework: a SIP trunk into LiveKit rooms, or a carrier's media stream into a Pipecat transport. The reference agents above show phone calling end to end (the Pipecat agent answers Twilio Media Streams). Telephony audio is 8 kHz G.711; for any other carrier, check the current docs rather than assuming support either way.

### Telnyx — Via LiveKit
A Telnyx SIP trunk routes phone calls into LiveKit rooms, and the LiveKit agent uses `assemblyai.STT(...)` as above. Configure inbound/outbound trunks and dispatch rules.

### Telnyx — Via Pipecat
WebSocket media streaming with TeXML, using Pipecat's `FastAPIWebsocketTransport` with a `TelnyxFrameSerializer` (there is no `TelnyxTransport` class). **Critical: Telnyx uses 8kHz audio**, not 16kHz:

```python
import os

from pipecat.serializers.telnyx import TelnyxFrameSerializer
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

transport = FastAPIWebsocketTransport(
    websocket=websocket,  # the FastAPI WebSocket Telnyx connected to
    params=FastAPIWebsocketParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        audio_in_sample_rate=8000,
        audio_out_sample_rate=8000,
        serializer=TelnyxFrameSerializer(
            stream_id=stream_id,
            inbound_encoding="PCMU",
            outbound_encoding="PCMU",
            call_control_id=call_control_id,  # needed for auto hang-up
            api_key=os.getenv("TELNYX_API_KEY"),
        ),
    ),
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
