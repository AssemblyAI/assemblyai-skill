"""Offline tests for evals/execution/streaming-clinic-intake/check.py. No network."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "stream_check", ROOT / "evals" / "execution" / "streaming-clinic-intake" / "check.py")
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)

GOOD_CONFIG = {"model": "universal-3-6-pro", "domain": "medical-v1", "speaker_labels": True, "redact_pii": True}


def _run(tmp_path: Path, config: dict, turn_text: str = "My number is [PHONE_NUMBER].") -> Path:
    out = tmp_path / "out.json"
    out.write_text(json.dumps({"turns": [{"speaker": "A", "text": turn_text}]}), encoding="utf-8")
    frames = [{"type": "Begin", "configuration": config},
              {"type": "Turn", "end_of_turn": True, "transcript": turn_text}]
    (tmp_path / "out.json.frames.jsonl").write_text("\n".join(json.dumps(f) for f in frames), encoding="utf-8")
    return out


def test_passes_when_server_applied_everything(tmp_path):
    assert check.score(_run(tmp_path, GOOD_CONFIG))["pass"]


def test_fails_on_a_valid_but_older_model(tmp_path):
    result = check.score(_run(tmp_path, {**GOOD_CONFIG, "model": "universal-streaming-english"}))
    assert not result["pass"]
    assert [k for k, v in result["checks"].items() if not v["pass"]] == ["model_current_pro"]


def test_fails_when_ssn_digits_survive(tmp_path):
    result = check.score(_run(tmp_path, GOOD_CONFIG, "It's 987-65-4321."))
    assert not result["checks"]["ssn_absent_output"]["pass"]
    assert not result["checks"]["ssn_absent_server_turns"]["pass"]


def test_fails_without_a_logged_begin(tmp_path):
    out = _run(tmp_path, GOOD_CONFIG)
    out.with_name("out.json.frames.jsonl").write_text("", encoding="utf-8")
    assert not check.score(out)["pass"]


def test_fails_when_run_sh_failed(tmp_path):
    assert not check.score(_run(tmp_path, GOOD_CONFIG), exit_code=1)["pass"]
