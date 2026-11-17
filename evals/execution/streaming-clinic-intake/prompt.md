We run a small clinic and want live transcription of our phone intake calls. Please build the piece that takes the call audio and transcribes it in real time with AssemblyAI.

What matters to us:

- Medical terminology comes up constantly (medications, conditions, procedures), so it needs to be as accurate as possible on medical vocabulary.
- We need to know who said what, so label the speakers.
- Personal details (names, phone numbers, social security numbers and so on) must be masked as they are transcribed. We can't store them.

For now the "live call" is an audio file: stream it to AssemblyAI at real-time speed, as if it were arriving from the phone line, and collect the transcript as it comes back.

My AssemblyAI API key is in the `ASSEMBLYAI_API_KEY` environment variable. There is a sample recording at `./sample.wav` (16 kHz mono WAV) you can test with. Anything you install in this environment stays installed.

When you are done, I will run it myself from this directory, in a fresh shell, as:

    ./run.sh <audio.wav> <out.json>

It must exit 0 on success and non-zero on failure.

It must write `<out.json>` as `{"turns": [{"speaker": "...", "text": "..."}]}` with the final text of each turn in order. For our audit log, it must also write every message it receives from AssemblyAI, unmodified and in the order received, one JSON object per line, to the path formed by appending `.frames.jsonl` to the second argument (so `out.json.frames.jsonl`).
