# AssemblyAI LLM Gateway Reference

## Overview

The LLM Gateway is an OpenAI-compatible API provided by AssemblyAI for applying LLMs to transcripts and for general chat completions. It replaces LeMUR, which is deprecated and scheduled for sunset on March 31, 2026.

**Key difference from LeMUR:** Instead of passing `transcript_ids`, you pass transcript text directly in the `messages` array. This gives you full control over what context the LLM receives.

**Base URLs:**
- Global: `https://llm-gateway.assemblyai.com/v1`
- EU: `https://llm-gateway.eu.assemblyai.com/v1`

**EU Region Limitation:** Only Anthropic Claude and Google Gemini models are available in the EU region. OpenAI (GPT) models are **not** supported in EU.

**Global routing (lower cost):** Add the optional request field `"model_region": "global"` to route a request to the provider's global, non-region endpoints for lower-cost processing. The only accepted value is `"global"`; omit the field for default in-region processing. Currently live for Anthropic Claude models, with Google Gemini 3 series coming soon. Use it when you have **no** data residency, compliance, or latency requirements and want cheaper calls. It layers on top of the default (US) endpoint.

> **Price change:** Effective **July 1, 2026**, in-region LLM Gateway requests cost **10% more** — a direct pass-through of provider price increases, with no AssemblyAI upcharge. Opting into global routing keeps current pricing.

**Authentication:**
- Header: `Authorization: API_KEY`
- Note: Do NOT use a `Bearer` prefix. Pass the API key directly.

---

## Available Models

Model IDs have NO provider prefix (e.g., use `claude-sonnet-4-5-20250929`, not `anthropic/claude-sonnet-4-5-20250929`).

### Anthropic (Claude)

| Model | ID |
|-------|----|
| Claude Opus 4.7 | `claude-opus-4-7` |
| Claude Opus 4.6 | `claude-opus-4-6` |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` |
| Claude Opus 4.5 | `claude-opus-4-5-20251101` |
| Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` |
| Claude Opus 4 ⚠️ **removed June 2026** | `claude-opus-4-20250514` |
| Claude Sonnet 4 ⚠️ **removed June 2026** | `claude-sonnet-4-20250514` |
| Claude 3.0 Haiku ⚠️ **retired** | `claude-3-haiku-20240307` |

`claude-opus-4-20250514` and `claude-sonnet-4-20250514` were removed from the LLM Gateway's available-models list in June 2026 — don't suggest them. Use Claude Opus 4.5/4.6/4.7 or Claude Sonnet 4.5/4.6 instead.

### OpenAI (GPT)

| Model | ID |
|-------|----|
| GPT-5.5 | `gpt-5.5` |
| GPT-5.2 | `gpt-5.2` |
| GPT-5.1 | `gpt-5.1` |
| GPT-5 | `gpt-5` |
| GPT-5 nano | `gpt-5-nano` |
| GPT-5 mini | `gpt-5-mini` |
| GPT-4.1 | `gpt-4.1` |
| gpt-oss-120b | `gpt-oss-120b` |
| gpt-oss-20b | `gpt-oss-20b` |

### Google (Gemini)

| Model | ID |
|-------|----|
| Gemini 3.5 Flash | `gemini-3.5-flash` |
| Gemini 3 Flash Preview | `gemini-3-flash-preview` |
| Gemini 3.1 Flash Lite Preview ⚠️ US-only | `gemini-3.1-flash-lite-preview` |
| Gemini 2.5 Pro | `gemini-2.5-pro` |
| Gemini 2.5 Flash | `gemini-2.5-flash` |
| Gemini 2.5 Flash-Lite | `gemini-2.5-flash-lite` |

### Alibaba (Qwen)

| Model | ID |
|-------|----|
| Qwen3 Next 80B | `qwen3-next-80b-a3b` |
| Qwen3 32B | `qwen3-32B` |

### Moonshot AI (Kimi)

| Model | ID |
|-------|----|
| Kimi K2.5 | `kimi-k2.5` |

---

## Chat Completions

**Endpoint:** `POST /v1/chat/completions`

The request and response formats follow the OpenAI Chat Completions specification. Access the LLM response via `result.choices[0].message.content`.

Supports:
- Multi-turn conversations (pass full message history)
- System prompts (`role: "system"`)
- User and assistant messages
- `prompt` shorthand — pass a simple string instead of a `messages` array for single-turn requests
- `stream: true` — stream responses as server-sent events (SSE). **OpenAI models only.**
- `transcript_id` — top-level field that injects a transcript's text into the prompt (see [Inject a Transcript by ID](#inject-a-transcript-by-id) below)
- `post_processing_steps` — ordered server-side fixes applied after generation. Currently supports `{"type": "json-repair"}` to automatically fix malformed JSON in content and tool call arguments
- `reasoning` — control reasoning behavior for supported models (see [Reasoning](#reasoning) below)
- `model_region` — set to `"global"` to opt into global routing for lower-cost processing (Claude now, Gemini 3 coming soon). Omit for default in-region processing. See [Global routing](#overview) above.

### Inject a Transcript by ID

Pass `transcript_id` at the top level of the request to have the API replace the literal tag `{{ transcript }}` in your messages with the transcript's `text` field. This avoids fetching the transcript yourself before calling the LLM Gateway — just transcribe, then pass the ID.

```bash
curl -X POST "https://llm-gateway.assemblyai.com/v1/chat/completions" \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-6",
    "messages": [
      {"role": "user", "content": "Summarize this transcript: {{ transcript }}"}
    ],
    "transcript_id": "YOUR_TRANSCRIPT_ID"
  }'
```

Important rules:
- Only the **first occurrence** of `{{ transcript }}` in the **first message that contains it** is substituted — additional tags or tags in later messages are left as-is.
- The tag must be exactly `{{ transcript }}` (with the spaces). Variants like `{{transcript}}` or `{{ TRANSCRIPT }}` are **not** substituted.
- The endpoint returns **404** if the transcript ID does not exist or belongs to a different account.

### cURL Example

```bash
curl https://llm-gateway.assemblyai.com/v1/chat/completions \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful assistant that analyzes transcripts."
      },
      {
        "role": "user",
        "content": "Summarize this transcript:\n\n<transcript>\nSpeaker A: Welcome to the meeting...\n</transcript>"
      }
    ]
  }'
```

### Python (requests) Example

```python
import requests

url = "https://llm-gateway.assemblyai.com/v1/chat/completions"
headers = {
    "Authorization": "YOUR_API_KEY",
    "Content-Type": "application/json",
}
data = {
    "model": "claude-sonnet-4-5-20250929",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Summarize this transcript:\n\n" + transcript_text},
    ],
}

response = requests.post(url, headers=headers, json=data)
result = response.json()
print(result["choices"][0]["message"]["content"])
```

### JavaScript (fetch) Example

```javascript
const response = await fetch(
  "https://llm-gateway.assemblyai.com/v1/chat/completions",
  {
    method: "POST",
    headers: {
      Authorization: "YOUR_API_KEY",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "claude-sonnet-4-5-20250929",
      messages: [
        { role: "system", content: "You are a helpful assistant." },
        { role: "user", content: `Summarize this transcript:\n\n${transcriptText}` },
      ],
    }),
  }
);

const result = await response.json();
console.log(result.choices[0].message.content);
```

### Response Format

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1711000000,
  "model": "claude-sonnet-4-5-20250929",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Here is a summary of the transcript..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "input_tokens": 150,
    "output_tokens": 200,
    "total_tokens": 350
  }
}
```

**Note:** Usage field names are `input_tokens` / `output_tokens` / `total_tokens` (matching the canonical AssemblyAI response shape), not `prompt_tokens` / `completion_tokens`.

---

## Reasoning

Control the reasoning behavior of supported models by including a top-level `reasoning` object in your request. Supported on **OpenAI-compatible models, Gemini 3+ models, and Anthropic models**.

Use `effort` to set the reasoning effort level, or `max_tokens` to cap the number of tokens the model can use for internal reasoning. Most models use `effort`.

| Key | Type | Description |
|-----|------|-------------|
| `effort` | string | `"low"`, `"medium"`, or `"high"`. Supported by most reasoning models. |
| `max_tokens` | integer | Maximum tokens the model can use for internal reasoning. |

```json
{
  "model": "claude-sonnet-4-6",
  "messages": [
    {"role": "user", "content": "Explain quantum entanglement step by step."}
  ],
  "max_tokens": 1000,
  "reasoning": {
    "effort": "medium"
  }
}
```

---

## Tool / Function Calling

The LLM Gateway supports tool (function) calling. Define tools in the `tools` array and control tool selection with `tool_choice`.

### Defining Tools

```json
{
  "model": "claude-sonnet-4-5-20250929",
  "messages": [
    {"role": "user", "content": "What is the weather in San Francisco?"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get the current weather for a location.",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "The city and state, e.g. San Francisco, CA"
            }
          },
          "required": ["location"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

### `tool_choice` Options

- `"auto"` — The model decides whether to call a tool (default).
- `"none"` — The model will not call any tools.
- `{"type": "function", "function": {"name": "get_weather"}}` — Force a specific tool.

### Tool Call Response

When the model calls a tool, the tool calls appear under `choices[i].message.tool_calls`:

```json
{
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"location\": \"San Francisco, CA\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_use"
    }
  ]
}
```

> **`finish_reason` is provider-native — do NOT branch on `"tool_calls"` alone.** The Gateway passes the provider's value through unchanged: OpenAI returns `"tool_calls"` / `"stop"`, while **Claude returns `"tool_use"` / `"end_turn"`** and Gemini has its own values. Detect a tool call by the **presence of `message.tool_calls`**, not by `finish_reason`. The model may also split its response across multiple `choices` (e.g. one with text content, another carrying the `tool_calls` array, each with its own `index`), so iterate all choices when collecting tool calls.

### Returning Tool Results

After executing the tool, pass the result back using the `tool` role with `tool_call_id`:

```json
{
  "model": "claude-sonnet-4-5-20250929",
  "messages": [
    {"role": "user", "content": "What is the weather in San Francisco?"},
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_abc123",
          "type": "function",
          "function": {
            "name": "get_weather",
            "arguments": "{\"location\": \"San Francisco, CA\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_abc123",
      "content": "{\"temperature\": 62, \"unit\": \"fahrenheit\", \"condition\": \"foggy\"}"
    }
  ]
}
```

Message roles used in tool calling:
- `assistant` (with `tool_calls` array) — The model's response when invoking a tool.
- `tool` (with `tool_call_id`) — Return the result of a tool execution back to the model.

---

## Agentic Workflows

For multi-step agentic workflows, use a loop pattern where the model autonomously chains tool calls until it produces a final answer (no `tool_calls` in the response). Branch on the **presence of `message.tool_calls`**, not on `finish_reason` — the latter is provider-specific (`"tool_calls"` for OpenAI, `"tool_use"` for Claude).

### Loop Pattern with `max_iterations`

```python
import requests

url = "https://llm-gateway.assemblyai.com/v1/chat/completions"
headers = {
    "Authorization": "YOUR_API_KEY",
    "Content-Type": "application/json",
}

messages = [
    {"role": "system", "content": "You are a research assistant with access to tools."},
    {"role": "user", "content": "Find the weather in NYC and SF, then compare them."},
]

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"],
            },
        },
    }
]

max_iterations = 10

for i in range(max_iterations):
    response = requests.post(
        url,
        headers=headers,
        json={"model": "claude-sonnet-4-5-20250929", "messages": messages, "tools": tools},
    )
    result = response.json()
    choice = result["choices"][0]
    assistant_message = choice["message"]
    messages.append(assistant_message)

    tool_calls = assistant_message.get("tool_calls")
    if not tool_calls:
        # No tool calls — model has finished; print final answer
        print(assistant_message["content"])
        break

    for tool_call in tool_calls:
        # Execute the tool (your implementation)
        tool_result = execute_tool(tool_call["function"]["name"], tool_call["function"]["arguments"])
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": tool_result,
        })
```

The model will call `get_weather` for each city in separate iterations, then produce a final comparison once it has all the data.

---

## Structured Outputs

Use the `response_format` parameter with `type: "json_schema"` to get structured JSON responses that conform to a specific schema.

**Supported models:** OpenAI (GPT-4.1, GPT-5.x), Gemini, Claude (4.5+), Alibaba Cloud Qwen, Moonshot AI Kimi. **NOT supported:** `gpt-oss` models, Claude 3.x models. For unsupported models, instruct via system prompt instead.

The `json_schema.strict` field **defaults to `false`** — set it to `true` (as in the examples below) to enforce strict schema adherence.

### Example

```json
{
  "model": "gpt-5-mini",
  "messages": [
    {
      "role": "system",
      "content": "Extract action items from the following transcript."
    },
    {
      "role": "user",
      "content": "Transcript text here..."
    }
  ],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "action_items",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {
          "action_items": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "assignee": { "type": "string" },
                "task": { "type": "string" },
                "due_date": { "type": "string" }
              },
              "required": ["assignee", "task", "due_date"],
              "additionalProperties": false
            }
          }
        },
        "required": ["action_items"],
        "additionalProperties": false
      }
    }
  }
}
```

### Python Example

```python
import requests
import json

url = "https://llm-gateway.assemblyai.com/v1/chat/completions"
headers = {
    "Authorization": "YOUR_API_KEY",
    "Content-Type": "application/json",
}

data = {
    "model": "gpt-5-mini",
    "messages": [
        {"role": "system", "content": "Extract action items from the transcript."},
        {"role": "user", "content": transcript_text},
    ],
    "response_format": {
        "type": "json_schema",
        "json_schema": {
            "name": "action_items",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "action_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "assignee": {"type": "string"},
                                "task": {"type": "string"},
                                "due_date": {"type": "string"},
                            },
                            "required": ["assignee", "task", "due_date"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["action_items"],
                "additionalProperties": False,
            },
        },
    },
}

response = requests.post(url, headers=headers, json=data)
result = response.json()
action_items = json.loads(result["choices"][0]["message"]["content"])
print(action_items)
```

---

## Fallback Models

Use `fallbacks` to specify backup models that the LLM Gateway automatically tries if the primary model fails. Specify `fallback_config.depth` to chain up to 2 fallbacks.

```json
{
  "model": "kimi-k2.5",
  "messages": [{"role": "user", "content": "Summarize this transcript..."}],
  "fallbacks": [
    {"model": "claude-sonnet-4-6"}
  ]
}
```

Override any field per fallback (messages, temperature, max_tokens). Fields not specified inherit from the original request.

**Retry behavior:** By default, `fallback_config.retry` is `true`, which automatically retries the request once after 500ms on failure — even if no `fallbacks` are set. To disable: `{"fallback_config": {"retry": false}}`.

---

## Prompt Caching (Public Beta)

Cache large, reusable prompt prefixes (system prompts, long transcripts, tool definitions) to cut cost and latency on repeated calls.

| Provider | Caching | Configuration |
|----------|---------|---------------|
| Claude (Anthropic) | Explicit opt-in | Add `cache_control` to the message(s) you want cached |
| OpenAI, Gemini, Kimi | **Automatic** | None — caching happens implicitly, no config needed |

**Claude — explicit `cache_control`:** mark a content block (a message, or a tool-result message) with `cache_control` set to `{"type": "ephemeral"}`:

```json
{
  "role": "system",
  "content": "<long reusable context...>",
  "cache_control": {"type": "ephemeral"}
}
```

- **TTL is a Gateway extension:** `"cache_control": {"type": "ephemeral", "ttl": "5m"}`. The `ttl` field is NOT part of Anthropic's native API — if omitted, Anthropic's default cache duration applies.
- A top-level `cache_control` acts as a request-level default for Claude. `prompt_cache_retention` and `prompt_cache_key` are passed through to OpenAI/Kimi.
- **Minimum cacheable prompt length (Claude varies by model):** Opus 4.5/4.6/4.7 and Haiku 4.5 = **4,096** tokens; Sonnet 4.6 = **2,048**; Sonnet 4.5, Sonnet 4, Opus 4 = **1,024**. OpenAI = **1,024**. Below the threshold the request runs uncached with no error.

**Cache metrics** are returned under `usage.prompt_tokens_details`: `cached_tokens` (cache reads) and `cache_creation.ephemeral_5m_input_tokens` / `ephemeral_1h_input_tokens` (cache writes).

---

## Speech Understanding Endpoint

Besides `/v1/chat/completions`, the LLM Gateway exposes **`POST /v1/understanding`** (`https://llm-gateway.assemblyai.com/v1/understanding`) for Translation, Speaker Identification, and Custom Formatting on an existing transcript. Pass `transcript_id` plus a `speech_understanding.request.<feature>` body. See `speech-understanding.md` for the full request/response shapes.

---

## Rate Limits

Paid accounts: **30 requests/minute per model** (each model has its own 60-second window). The LLM Gateway is **not available on free accounts**. A `429` means you've hit a model's limit — back off with jitter (read `X-RateLimit-*` headers) or set `fallbacks` so traffic spills to another model.

---

## Error Responses

Most errors return a **flattened** JSON body (changed June 2026 — fields were previously nested under an `error` object):

```json
{
  "code": 400,
  "message": "invalid request body",
  "request_id": "2a9adf03-c73e-4333-a42d-54b515e6afbd",
  "metadata": {
    "errors": ["one of messages or prompt required"]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `code` | number | HTTP status code. |
| `message` | string | Human-readable description. |
| `request_id` | string | Unique request ID — include it when contacting support. |
| `metadata.errors` | string[] | Present on 400 responses: lists every field that failed validation. |

| Status | Meaning / common cause |
|--------|------------------------|
| `400` | Bad request — missing `model` or `messages`/`prompt`, unrecognized model ID, `max_tokens` out of range, or wrong field type. Inspect `metadata.errors`. Common strings: `"model {x} is not supported"`, `"model context limit exceeded"`, `"model_region can only be set to global"`, `"fallback_config depth cannot be greater than 2"`, `"response_format is invalid: ..."`. |
| `401` / `403` | Auth error — missing/invalid/expired key, wrong account or region, or a `Bearer` prefix was used. **Note:** auth errors still use the older shape `{"error": "...", "status": "error", "request_id": "..."}`. |
| `404` | `transcript_id` not found (wrong account/region) or deleted (message `"transcript deleted"`). |
| `429` | Per-model rate limit exceeded within a 60-second window (each model has its own limit). Read the `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` response headers and back off with jitter, or set `fallbacks` so traffic spills over to another model. |
| `5xx` | Transient AssemblyAI or upstream-provider issue — retry with exponential backoff and jitter. |

---

## Data Retention by Provider

Data retention policies vary by the underlying provider used by AssemblyAI:

| Provider | Backend | Data Retention Policy |
|----------|---------|----------------------|
| Claude (Anthropic) | Amazon Bedrock | No data storage. Inputs and outputs are not stored or used for training. |
| Gemini (Google) | Google AI | Zero Data Retention (ZDR). No data is stored or used for training. |
| GPT (OpenAI) | OpenAI API | Retains abuse monitoring logs for 30 days. Data is not used for training. |

---

## Common Pattern: Transcribe Then Analyze

The most common workflow is to transcribe audio with AssemblyAI's Speech-to-Text API, then send the transcript text to the LLM Gateway for analysis.

### Full Workflow Example (Python)

```python
import requests

API_KEY = "YOUR_API_KEY"

# Step 1: Transcribe audio
transcript_response = requests.post(
    "https://api.assemblyai.com/v2/transcript",
    headers={"Authorization": API_KEY, "Content-Type": "application/json"},
    json={"audio_url": "https://example.com/audio.mp3"},
)
transcript_id = transcript_response.json()["id"]

# Step 2: Poll for completion
import time

while True:
    polling_response = requests.get(
        f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
        headers={"Authorization": API_KEY},
    )
    status = polling_response.json()["status"]
    if status == "completed":
        transcript_text = polling_response.json()["text"]
        break
    elif status == "error":
        raise Exception("Transcription failed: " + polling_response.json().get("error", ""))
    time.sleep(3)

# Step 3: Send transcript to LLM Gateway for analysis
llm_response = requests.post(
    "https://llm-gateway.assemblyai.com/v1/chat/completions",
    headers={"Authorization": API_KEY, "Content-Type": "application/json"},
    json={
        "model": "claude-sonnet-4-5-20250929",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert at analyzing meeting transcripts.",
            },
            {
                "role": "user",
                "content": f"Analyze this transcript and provide:\n1. A brief summary\n2. Key decisions made\n3. Action items with assignees\n\nTranscript:\n{transcript_text}",
            },
        ],
    },
)

analysis = llm_response.json()["choices"][0]["message"]["content"]
print(analysis)
```

### Using the AssemblyAI Python SDK

```python
import assemblyai as aai

aai.settings.api_key = "YOUR_API_KEY"

# Step 1: Transcribe
transcriber = aai.Transcriber()
transcript = transcriber.transcribe("https://example.com/audio.mp3")

if transcript.status == aai.TranscriptStatus.error:
    raise Exception(f"Transcription failed: {transcript.error}")

# Step 2: Send to LLM Gateway
import requests

llm_response = requests.post(
    "https://llm-gateway.assemblyai.com/v1/chat/completions",
    headers={"Authorization": aai.settings.api_key, "Content-Type": "application/json"},
    json={
        "model": "claude-sonnet-4-5-20250929",
        "messages": [
            {"role": "system", "content": "Summarize the following transcript."},
            {"role": "user", "content": transcript.text},
        ],
    },
)

summary = llm_response.json()["choices"][0]["message"]["content"]
print(summary)
```

### Key Points for the Transcribe-Then-Analyze Pattern

- Use the same API key for both the Transcription API and the LLM Gateway.
- Pass `transcript.text` (the full text) in the user message. Do NOT pass transcript IDs to the LLM Gateway (that was the LeMUR pattern).
- For speaker-labeled analysis, format utterances from `transcript.utterances` before sending to the LLM.
- You can include other transcript features (sentiment analysis results, entity detection, etc.) in the prompt for richer analysis.
