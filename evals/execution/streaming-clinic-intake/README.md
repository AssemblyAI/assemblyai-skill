# Execution-graded eval: streaming clinic intake

The evals in `skills/assemblyai/evals/evals.json` grade the code an agent writes by reading it. This one runs the code and grades what the server applied, as echoed in the streaming `Begin.configuration`. A session that quietly fell back to another model, or ignored a parameter, fails here even when the code looks right.

## Files

| File | What it is |
|---|---|
| `prompt.md` | the task given to the agent |
| `support_call.wav` | 51 s, 16 kHz mono, two synthetic voices; contains a reserved, never-issued SSN and a 555-01xx phone number |
| `support_call.json` | the script and ground truth for that clip |
| `check.py` | the grader (standard library only) |

## Run it

1. In an empty directory, copy `support_call.wav` to `sample.wav`, install the skill (or don't, for the baseline), and give the agent `prompt.md`.
2. When the agent is done, grade its app:

```bash
ASSEMBLYAI_API_KEY=your_key python evals/execution/streaming-clinic-intake/check.py /path/to/agent/dir
```

That runs `./run.sh support_call.wav <tmp>/out.json` in the agent's directory (about 51 s of real-time streaming), then prints one line per check and exits 0 only if all pass. To re-grade a run you already have (`out.json` and `out.json.frames.jsonl` in one directory), offline:

```bash
python evals/execution/streaming-clinic-intake/check.py --score /path/to/run_dir
```

## What passes

A current Pro streaming model (`universal-3-6-pro` or `universal-3-5-pro`), `domain: medical-v1`, `speaker_labels` and `redact_pii` true in `Begin.configuration`; final turns logged; the SSN and phone digits absent from both the server's final turns and `out.json`.

The model, domain and redaction checks read the app's own log of server messages. The prompt requires that log unmodified; an app that rewrites it could pass falsely.

## Results so far

120 runs of Codex CLI (`gpt-6.1-sol`), docs hosts blocked, 10 per condition per task; this task's 30 are below. Every run, its log and the harness: [aatif101/assemblyai-200-not-done](https://github.com/aatif101/assemblyai-200-not-done).

| Condition | Pass |
|---|---|
| Without skill | 8 / 10 |
| With skill | 10 / 10 |
| With skill + docs MCP | 10 / 10 |

Both failures picked `universal-streaming-english` from the Python SDK's `SpeechModel` enum. The request was valid, so nothing warned the agent. Six of the eight passing baseline runs asked for the removed `u3-rt-pro`, and the server ran `universal-3-6-pro`.
