# AssemblyAI Skill for AI Coding Agents

A skill that gives AI coding agents accurate, up-to-date knowledge of AssemblyAI's speech-to-text APIs, SDKs, and voice agent integrations. Install with `npx skills add AssemblyAI/assemblyai-skill` — works with Claude Code, Cursor, Copilot, Codex, and [60+ other coding agents](https://github.com/vercel-labs/skills).

## Why a skill?

LLM training data contains outdated AssemblyAI patterns — deprecated LeMUR API calls, discontinued SDK usage, wrong auth headers, and no knowledge of newer features like the LLM Gateway, streaming v3, or voice agent framework integrations. This skill corrects those mistakes and adds coverage for the full current API surface.

**Without the skill**, coding agents will:
- Use the deprecated LeMUR API instead of the LLM Gateway
- Use `Authorization: Bearer KEY` instead of `Authorization: KEY`
- Use `word_boost` instead of `keyterms_prompt`
- Use discontinued Java/Go/C# SDKs
- Write Python 0.x SDK patterns removed in 1.0.0 (`aai.Lemur`, `assemblyai[extras]`, `MicrophoneStream`)
- Miss all LiveKit/Pipecat-specific gotchas for voice agents
- Use wrong model ID formats (`anthropic/claude-...` instead of `claude-...`)

## What's covered

| Area | Details |
|------|---------|
| **Pre-recorded transcription** | Universal-3.5 Pro, Universal-2, prompting, speech_models fallback |
| **Streaming STT** | v3 protocol, v2 legacy, Whisper Streaming, temp tokens, error codes |
| **Voice agents** | LiveKit and Pipecat integrations, universal-3-5-pro defaults, turn detection, silence tuning, latency optimization |
| **LLM Gateway** | Chat completions, tool calling, agentic workflows, structured output caveats, full model list |
| **Audio intelligence** | PII redaction, diarization, summarization, sentiment, entity detection, content safety, chapters |
| **Speech understanding** | Translation, speaker identification, custom formatting |
| **SDKs** | Current Python (`1.1.0`) and JS/TS (`4.37.1`) patterns, the 0.x→1.x Python migration, Ruby status, discontinued SDK warnings |
| **API reference** | Full parameter list, export endpoints, webhooks, custom spelling, multichannel, code switching |

## Installation

### Quick install (recommended)

Install using the [skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add AssemblyAI/assemblyai-skill
```

This works with Claude Code, Cursor, Copilot, and 60+ other coding agents. The CLI will prompt you to choose which agent(s) to install for.

To check for updates later: `npx skills check`
To update: `npx skills update`

### Manual install

#### Claude Code

Copy the `skills/assemblyai/` directory into your Claude skills folder:

```bash
# Personal (available in all projects)
cp -r skills/assemblyai ~/.claude/skills/

# Project-level (checked into version control, shared with team)
cp -r skills/assemblyai .claude/skills/
```

#### Codex

Copy the `skills/assemblyai/` directory into your project, then reference it in your `AGENTS.md`:

```markdown
When working with AssemblyAI, read and follow the instructions in assemblyai/SKILL.md
```

#### Cursor / Windsurf / Other Agents

Copy the `skills/assemblyai/` directory into your project and add a rule or instruction pointing to `assemblyai/SKILL.md`. Most agents that support custom rules or docs can ingest the skill content directly.

## Skill structure

The skill uses progressive disclosure to keep context usage efficient. The core `SKILL.md` (122 lines) is always loaded and contains auth patterns, model overview, common mistakes, and gotchas. Detailed reference files are only loaded when relevant:

```
skills/
└── assemblyai/
    ├── SKILL.md                      # Core skill (always loaded)
    └── references/
        ├── python-sdk.md             # Python SDK patterns
        ├── js-sdk.md                 # JS/TS SDK patterns
        ├── streaming.md              # Streaming STT protocol details
        ├── voice-agents.md           # LiveKit, Pipecat integrations
        ├── llm-gateway.md            # LLM Gateway models and usage
        ├── speech-understanding.md   # Translation, speaker ID, formatting
        ├── audio-intelligence.md     # PII, diarization, summarization, etc.
        └── api-reference.md          # Full API parameters, endpoints, webhooks
```

## Testing code blocks

The repo includes a pytest suite that collects every fenced code block in `README.md` and `skills/**/*.md`.

Run the offline checks:

```bash
python -m pytest -m codeblocks
```

Offline mode does not call AssemblyAI. It parses JSON blocks, compiles Python blocks, checks shell blocks with `bash -n`, syntax-checks JavaScript/TypeScript blocks with Node, and counts plain/Markdown fences.

Run live API checks:

```bash
ASSEMBLYAI_API_KEY=your_key ASSEMBLYAI_RUN_LIVE_CODEBLOCKS=1 python -m pytest -m codeblocks
```

Live mode executes examples that can run as standalone AssemblyAI API calls. It rewrites `YOUR_API_KEY`, `https://example.com/audio.mp3`, and local audio placeholders to use environment-backed test values. Context-dependent LiveKit, Pipecat, and telephony fragments are still compiled, but not live-executed outside their host app.

Optional live-mode overrides:

```bash
ASSEMBLYAI_TEST_AUDIO_URL=https://example.com/short-audio.mp3
ASSEMBLYAI_TEST_AUDIO_FILE=/path/to/sample.wav
ASSEMBLYAI_CODEBLOCK_TIMEOUT=300
```

## Eval results

The `assemblyai-workspace/` directory contains test results comparing skill vs. no-skill outputs across three scenarios:

| Test Case | With Skill | Without Skill |
|-----------|-----------|---------------|
| Basic transcription + summary (Python) | 4/4 | 4/4 |
| Voice agent with LiveKit | 7/7 | 0/7 |
| LLM Gateway + PII redaction (TypeScript) | 6/6 | 3/6 |
| **Overall** | **17/17 (100%)** | **7/17 (41%)** |

The skill provides the most value for voice agent integrations (where LLMs have no training data for framework-specific pitfalls) and LLM Gateway usage (where LLMs default to the deprecated LeMUR API). Evals were run with Claude Code but results should generalize to other agents.
