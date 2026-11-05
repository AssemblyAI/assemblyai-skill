# AssemblyAI Remote MCP Server Reference

## Overview

AssemblyAI provides an official remote [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server (`AssemblyAI/assemblyai-mcp`) hosted on **Streamable HTTP**. It allows any MCP-compatible AI agent (Claude Code, Cursor, Claude.ai, MCP Inspector, and custom agent runtimes) to transcribe audio, extract insights, run Speech Understanding, and summarize recordings with native MCP tools.

**Default Host:**
- Hosted MCP Endpoint: `https://mcp.assemblyai.com/mcp`
- Local dev: `http://localhost:3000/mcp` (via `npm run dev`)

---

## Authentication

The MCP server supports two authentication paths:

### 1. Sign in with AssemblyAI (OAuth) — Recommended for MCP Auth Clients

Clients that support MCP authorization (Claude Code, Cursor, MCP Inspector) can connect with **no headers**. The client automatically completes PKCE authorization against AssemblyAI's authorization server and securely exchanges the resulting access token for an API key.

**Claude Code CLI:**
```bash
claude mcp add --transport http assemblyai https://mcp.assemblyai.com/mcp
```

When first connecting:
1. The server challenges requests with a `401 Unauthorized` pointing to `/.well-known/oauth-protected-resource` (scopes: `aai:api` and `offline_access`).
2. The MCP client opens AssemblyAI's sign-in and consent page in the browser.
3. The server exchanges the access token for the connection API key and proceeds with the request.

### 2. API Key Authentication (Bearer Header)

For clients that do not support OAuth authorization, pass your AssemblyAI API key as the `Bearer` token in the `Authorization` header.

> **CRITICAL AUTH GOTCHA:**
> - Core AssemblyAI REST and WebSocket endpoints (`api.assemblyai.com`, `tts.us.assemblyai.com`, `streaming.assemblyai.com`) require the raw API key **without** a `Bearer` prefix: `Authorization: YOUR_API_KEY`.
> - The AssemblyAI MCP Server adheres to standard HTTP Bearer authorization and requires `Authorization: Bearer YOUR_API_KEY`.

**Claude Code CLI with API Key:**
```bash
claude mcp add --transport http assemblyai https://mcp.assemblyai.com/mcp --header "Authorization: Bearer $ASSEMBLYAI_API_KEY"
```

**Generic MCP Client Configuration (`claude_desktop_config.json` / settings):**
```json
{
  "mcpServers": {
    "assemblyai": {
      "url": "https://mcp.assemblyai.com/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

---

## Tools

The MCP server exposes five tools:

| Tool | Purpose | Key Parameters |
|---|---|---|
| `submit_transcript` | Submit a public audio or video URL for async transcription | `audio_url` (required), `speech_model`, `language_code`, `speaker_labels`, `punctuate`, `format_text`, `speech_understanding`, `prompt`, `keyterms_prompt` |
| `get_transcript` | Fetch transcript status and formatted results | `transcript_id` (required) |
| `understand_transcript` | Run Speech Understanding on a completed transcript without re-uploading audio | `transcript_id` (required), `speech_understanding` (required object containing `request`) |
| `summarize_transcript` | Generate a quick summary of a completed transcript using the LLM Gateway | `transcript_id` (required), `style` (`"bullets"`, `"paragraph"`, `"headline"`, `"action_items"`, `"custom"`), `custom_prompt` |
| `delete_transcript` | Permanently delete transcript data from AssemblyAI storage | `transcript_id` (required) |

---

## Tool Details & Examples

### 1. `submit_transcript`

Starts an asynchronous transcription job. Accepts the full public async transcription parameter surface using API-native names.

- **Audio source**: Requires a publicly accessible `audio_url` (e.g. `https://storage.googleapis.com/...`).
- **Prompting**: `prompt` provides topical context (not instructions); `keyterms_prompt` boosts specific jargon or vocabulary.
- **Inline Speech Understanding**: Can include `speech_understanding` config in the initial submission to run analysis in the same pass.

Returns immediately:
```json
{
  "transcript_id": "9ea68fd3-f953-42c1-9742-976c447fb463",
  "status": "queued"
}
```

### 2. `get_transcript`

Polls the status of a transcription job and retrieves the completed results.

- Status progression: `queued` → `processing` → `completed` (or `error`).
- **Polling interval:** Agents should poll approximately every 3 seconds.
- Output formatting: Renders the transcript text along with formatted sections if available:
  - `--- utterances (speaker-labeled)`
  - `--- su_summary (chaptered summary)`
  - `--- su_action_items`
  - `--- speaker_identification`
  - `--- translation`
  - `--- custom_formatting`
  - `--- content_safety`

### 3. `understand_transcript`

Executes Speech Understanding features on an already-completed transcript via AssemblyAI's LLM Gateway (`POST /v1/understanding`). Useful when analysis requirements (such as translation or action items) are decided after viewing the transcript.

Parameters:
- `transcript_id`: ID of the completed transcript.
- `speech_understanding`: Object with `request` containing:
  - `translation`: `{ "target_languages": ["es", "fr"] }`
  - `summarization`: `{ "summary_type": "bullets" }`
  - `speaker_identification`: `{ "speaker_type": "name" }`
  - `custom_formatting`: `{ "format_utterances": true }`

### 4. `summarize_transcript`

Produces an LLM Gateway transcript summary. Supports 5 preset styles:
- `"bullets"` (default): Concise bulleted highlights.
- `"paragraph"`: Structured narrative overview.
- `"headline"`: Single-sentence high-level summary.
- `"action_items"`: Extracted follow-ups and next steps.
- `"custom"`: Tailored summary responding to the text in `custom_prompt`.

### 5. `delete_transcript`

Permanently deletes transcript data and audio metadata.
> **Caution:** Deletion is permanent and irreversible. Agents should only execute `delete_transcript` upon explicit user request.

---

## Typical Agent Pattern

1. **Submit**: Call `submit_transcript(audio_url="https://...")`.
2. **Poll**: Call `get_transcript(transcript_id=...)` every ~3 seconds until `status: "completed"`.
3. **Analyze**: Use `understand_transcript` or `summarize_transcript` for targeted follow-up questions.
4. **Clean up**: Call `delete_transcript` only if instructed by the user.
