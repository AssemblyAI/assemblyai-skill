#!/usr/bin/env python3
"""Grade an agent-built streaming app by running it and reading what the server applied.

    python check.py <app_dir>          run <app_dir>/run.sh on support_call.wav, then grade
    python check.py --score <run_dir>  grade an existing out.json + out.json.frames.jsonl

Run mode needs ASSEMBLYAI_API_KEY in the environment (the app reads it) and streams about 51 s
of audio. Score mode needs nothing and makes no network calls.

A run passes only if every check passes:

  runs                 run.sh exited 0 inside the timeout and out.json has a non-empty "turns" list
  begin_logged         the app logged the server's Begin message
  model_current_pro    Begin.configuration.model is a current Pro streaming model
  medical_mode         Begin.configuration.domain is "medical-v1"
  speaker_labels       Begin.configuration.speaker_labels is true
  redact_pii           Begin.configuration.redact_pii is true
  final_turns_logged   at least one Turn with end_of_turn was logged
  *_absent_*           the fixture's SSN and phone digits appear neither in the server's final
                       turns nor in out.json

The model, domain and redaction checks read Begin.configuration, the server's echo of what it
applied, so a session that silently fell back to another model or ignored a parameter fails even
when the code looks right. Standard library only.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "support_call.wav"
GROUND_TRUTH = json.loads((HERE / "support_call.json").read_text(encoding="utf-8"))["ground_truth"]
CURRENT_PRO_MODELS = {"universal-3-6-pro", "universal-3-5-pro"}
TIMEOUT_S = 240


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def _frames(path: Path) -> list[dict]:
    frames = []
    if not path.is_file():
        return frames
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            frames.append(obj)
    return frames


def score(out_json: Path, exit_code: int | None = 0, timed_out: bool = False) -> dict:
    """Checks for one run. `out_json` is the path given to run.sh; frames sit next to it."""
    checks: dict[str, tuple[bool, str]] = {}

    try:
        out = json.loads(out_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        out = None
    turns = out.get("turns") if isinstance(out, dict) else None
    turns_ok = isinstance(turns, list) and bool(turns) and all(
        isinstance(t, dict) and isinstance(t.get("text"), str) for t in turns)
    checks["runs"] = (exit_code == 0 and not timed_out and turns_ok,
                      f"exit={exit_code}, timed_out={timed_out}, turns={'ok' if turns_ok else 'missing or malformed'}")

    frames = _frames(out_json.with_name(out_json.name + ".frames.jsonl"))
    begin = next((f for f in frames if f.get("type") == "Begin"), None)
    cfg = (begin or {}).get("configuration") or {}
    checks["begin_logged"] = (begin is not None, f"{len(frames)} frames logged")
    checks["model_current_pro"] = (cfg.get("model") in CURRENT_PRO_MODELS, f"model={cfg.get('model')!r}")
    checks["medical_mode"] = (cfg.get("domain") == "medical-v1", f"domain={cfg.get('domain')!r}")
    checks["speaker_labels"] = (cfg.get("speaker_labels") is True, f"speaker_labels={cfg.get('speaker_labels')!r}")
    checks["redact_pii"] = (cfg.get("redact_pii") is True, f"redact_pii={cfg.get('redact_pii')!r}")

    finals = [f for f in frames if f.get("type") == "Turn" and f.get("end_of_turn")]
    checks["final_turns_logged"] = (bool(finals), f"{len(finals)} final turns")
    server_text = " ".join(str(f.get("transcript") or f.get("utterance") or "") for f in finals)
    out_text = " ".join(str(t.get("text") or "") for t in turns) if turns_ok else ""
    for label in ("ssn", "phone"):
        digits = GROUND_TRUTH[f"{label}_digits"]
        for where, text in (("server_turns", server_text), ("output", out_text)):
            present = digits in _digits(text)
            checks[f"{label}_absent_{where}"] = (bool(text.strip()) and not present,
                                                 "digits present" if present else ("no text" if not text.strip() else "digits absent"))

    return {"pass": all(ok for ok, _ in checks.values()),
            "checks": {name: {"pass": ok, "evidence": ev} for name, (ok, ev) in checks.items()}}


def run(app_dir: Path) -> dict:
    run_sh = app_dir / "run.sh"
    if not run_sh.is_file():
        raise SystemExit(f"{run_sh} not found")
    with tempfile.TemporaryDirectory() as tmp:
        out_json = Path(tmp) / "out.json"
        try:
            proc = subprocess.run(["bash", "run.sh", str(FIXTURE), str(out_json)], cwd=app_dir,
                                  timeout=TIMEOUT_S, capture_output=True)
            result = score(out_json, proc.returncode)
        except subprocess.TimeoutExpired:
            result = score(out_json, None, timed_out=True)
    return result


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "--score":
        result = score(Path(argv[1]) / "out.json")
    elif len(argv) == 1:
        result = run(Path(argv[0]).resolve())
    else:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    for name, c in result["checks"].items():
        print(f"{'PASS' if c['pass'] else 'FAIL'}  {name:28s} {c['evidence']}")
    print("\nRESULT:", "PASS" if result["pass"] else "FAIL")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
