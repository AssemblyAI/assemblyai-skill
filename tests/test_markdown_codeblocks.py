from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import textwrap
import wave
from dataclasses import dataclass
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
API_KEY_ENV = "ASSEMBLYAI_API_KEY"
RUN_LIVE = os.environ.get("ASSEMBLYAI_RUN_LIVE_CODEBLOCKS") == "1"
DEFAULT_AUDIO_URL = "https://storage.googleapis.com/aai-web-samples/5_common_sports_injuries.mp3"
FENCE_RE = re.compile(r"^```([^\n`]*)\n(.*?)^```\s*$", re.MULTILINE | re.DOTALL)


@dataclass(frozen=True)
class CodeBlock:
    path: Path
    line: int
    lang: str
    code: str

    @property
    def id(self) -> str:
        rel = self.path.relative_to(ROOT)
        return f"{rel}:{self.line}:{self.lang or 'plain'}"


def markdown_files() -> list[Path]:
    return [ROOT / "README.md", *sorted((ROOT / "skills").glob("**/*.md"))]


def collect_codeblocks() -> list[CodeBlock]:
    blocks: list[CodeBlock] = []
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        for match in FENCE_RE.finditer(text):
            info = match.group(1).strip().split()
            lang = info[0].lower() if info else ""
            line = text[: match.start()].count("\n") + 1
            blocks.append(CodeBlock(path=path, line=line, lang=lang, code=match.group(2).rstrip()))
    return blocks


CODEBLOCKS = collect_codeblocks()


def _write_sample_wav(path: Path) -> Path:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(b"\0\0" * 16_000)
    return path


def _codeblock_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("ASSEMBLYAI_TEST_AUDIO_URL", DEFAULT_AUDIO_URL)
    env.setdefault("ASSEMBLYAI_TEST_AUDIO_FILE", str(_write_sample_wav(tmp_path / "sample.wav")))
    return env


def _require_api_key() -> None:
    if not os.environ.get(API_KEY_ENV):
        pytest.fail(f"{API_KEY_ENV} must be set when ASSEMBLYAI_RUN_LIVE_CODEBLOCKS=1")


def _replace_python_placeholders(code: str) -> str:
    replacements = {
        '"YOUR_API_KEY"': f'os.environ["{API_KEY_ENV}"]',
        "'YOUR_API_KEY'": f'os.environ["{API_KEY_ENV}"]',
        '"https://example.com/audio.mp3"': 'os.environ["ASSEMBLYAI_TEST_AUDIO_URL"]',
        "'https://example.com/audio.mp3'": 'os.environ["ASSEMBLYAI_TEST_AUDIO_URL"]',
        '"/path/to/local/audio.mp3"': 'os.environ["ASSEMBLYAI_TEST_AUDIO_FILE"]',
        "'/path/to/local/audio.mp3'": 'os.environ["ASSEMBLYAI_TEST_AUDIO_FILE"]',
        '"/path/to/local/recording.wav"': 'os.environ["ASSEMBLYAI_TEST_AUDIO_FILE"]',
        "'/path/to/local/recording.wav'": 'os.environ["ASSEMBLYAI_TEST_AUDIO_FILE"]',
        "aai.SpeechModel.universal_3_pro": '"universal-3-pro"',
    }
    for before, after in replacements.items():
        code = code.replace(before, after)
    return code


def _python_source(code: str) -> str:
    code = _replace_python_placeholders(code)
    prelude = f"""
import json
import os
import time

transcript_text = "Speaker A: Welcome to the meeting. Speaker B: Thanks for joining."

def execute_tool(name, arguments):
    return json.dumps({{"tool": name, "arguments": arguments, "ok": True}})

def run_tool(name, arguments):
    return {{"tool": name, "arguments": arguments, "ok": True}}

class _CodeBlockWebSocket:
    async def send(self, payload):
        return None

ws = _CodeBlockWebSocket()
event = {{"type": "reply.done", "name": "get_weather", "arguments": {{}}, "call_id": "call_test", "status": "completed"}}
t = event["type"]

try:
    import assemblyai as aai
except ImportError:
    aai = None
else:
    aai.settings.api_key = os.environ.get("{API_KEY_ENV}", "test-token")
    transcriber = aai.Transcriber()
"""
    wrapped = "async def __codeblock_main__():\n" + textwrap.indent(code, "    ")
    return f"{prelude}\n{wrapped}\n"


def _run_python(block: CodeBlock, tmp_path: Path) -> None:
    source = _python_source(block.code)
    compile(source, block.id, "exec")
    if not RUN_LIVE:
        return

    if _skip_live_python_execution(block):
        return

    _require_api_key()
    script = tmp_path / "codeblock.py"
    script.write_text(
        f"{source}\nimport asyncio\nasyncio.run(__codeblock_main__())\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["python", str(script)],
        cwd=ROOT,
        env=_codeblock_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=int(os.environ.get("ASSEMBLYAI_CODEBLOCK_TIMEOUT", "300")),
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def _skip_live_python_execution(block: CodeBlock) -> bool:
    if any(package in block.code for package in ("livekit", "pipecat")):
        return True

    if block.path.name == "voice-agents.md" and any(
        symbol in block.code for symbol in ("AssemblyAISTTService(", "TelnyxTransport(")
    ):
        return True

    return False


def _replace_shell_placeholders(code: str, tmp_path: Path) -> str:
    code = re.sub(
        r"""(['"])([Aa]uthorization:\s*(?:Bearer\s+)?)YOUR_API_KEY\1""",
        r'"\2${ASSEMBLYAI_API_KEY}"',
        code,
    )
    audio_url = os.environ.get("ASSEMBLYAI_TEST_AUDIO_URL", DEFAULT_AUDIO_URL)
    code = code.replace("https://example.com/audio.mp3", audio_url)
    sample = str(tmp_path / "sample.wav")
    code = code.replace("@audio.mp3", f"@{sample}")
    code = code.replace("@sample.wav", f"@{sample}")
    return code


def _run_shell(block: CodeBlock, tmp_path: Path) -> None:
    source = _replace_shell_placeholders(block.code, tmp_path)
    script = tmp_path / "codeblock.sh"
    script.write_text(source + "\n", encoding="utf-8")

    syntax = subprocess.run(
        ["bash", "-n", str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert syntax.returncode == 0, syntax.stderr

    if not RUN_LIVE or "curl" not in block.code:
        return

    _require_api_key()
    env = _codeblock_env(tmp_path)
    result = subprocess.run(
        ["bash", str(script)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=int(os.environ.get("ASSEMBLYAI_CODEBLOCK_TIMEOUT", "300")),
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def _strip_typescript_only_syntax(code: str) -> str:
    code = re.sub(r"(?<=[A-Za-z0-9_\]\)])!", "", code)
    return code


def _javascript_source(code: str, *, typescript: bool) -> str:
    if typescript:
        code = _strip_typescript_only_syntax(code)

    imports: list[str] = []
    body: list[str] = []
    for line in code.splitlines():
        if line.startswith("import "):
            imports.append(line)
        else:
            body.append(line)

    prelude = """
const client = {
  transcripts: {
    transcribe: async () => ({
      text: "hello world",
      status: "completed",
      utterances: [],
      sentiment_analysis_results: [],
      entities: [],
      chapters: [],
      content_safety_labels: { results: [] },
    }),
  },
  realtime: { transcriber: () => ({ on() {}, connect: async () => {}, close: async () => {} }) },
  streaming: { transcriber: () => ({ on() {}, connect: async () => {}, close: async () => {} }) },
};
"""
    if any("const client" in line for line in body):
        prelude = ""

    wrapped = "async function __codeblock_main__() {\n"
    wrapped += textwrap.indent(prelude + "\n".join(body), "  ")
    wrapped += "\n}\n"
    return "\n".join(imports) + "\n" + wrapped


def _run_javascript(block: CodeBlock, tmp_path: Path) -> None:
    source = _javascript_source(block.code, typescript=block.lang == "typescript")
    suffix = ".mjs"
    script = tmp_path / f"codeblock{suffix}"
    script.write_text(source, encoding="utf-8")

    node = shutil.which("node")
    if node is None:
        pytest.fail("node is required to syntax-check JavaScript and TypeScript code blocks")

    result = subprocess.run(
        [node, "--check", str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


@pytest.mark.codeblocks
def test_collects_markdown_codeblocks() -> None:
    assert CODEBLOCKS


@pytest.mark.codeblocks
@pytest.mark.parametrize("block", CODEBLOCKS, ids=[block.id for block in CODEBLOCKS])
def test_markdown_codeblock(block: CodeBlock, tmp_path: Path) -> None:
    lang = block.lang

    if lang == "json":
        json.loads(block.code)
    elif lang == "python":
        _run_python(block, tmp_path)
    elif lang in {"bash", "sh", "shell", "zsh"}:
        _run_shell(block, tmp_path)
    elif lang in {"javascript", "js", "typescript", "ts"}:
        _run_javascript(block, tmp_path)
    elif lang in {"", "text", "plain", "markdown"}:
        assert block.code.strip()
    else:
        pytest.fail(f"Unsupported Markdown code block language: {lang!r}")
