#!/usr/bin/env -S uv run --quiet
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "elevenlabs>=1.5.0",
#   "python-dotenv>=1.0.0",
# ]
# ///
"""Render the Granum demo voiceover via ElevenLabs.

Usage:
    uv run scripts/render_voiceover.py                 # dry-run; prints per-beat plan, no API calls
    uv run scripts/render_voiceover.py --render        # actually calls the API and writes MP3s (BURNS CREDITS)
    uv run scripts/render_voiceover.py --render --beat 3   # render only one beat (useful for re-records)

Reads:
    docs/voiceover.txt — beat markers `### BEAT N — ... ###` separate sections.

Writes:
    videos/audio/beat_{N}.mp3       — one file per beat
    videos/audio/granum_demo.mp3    — ffmpeg-concatenated full track

Env:
    ELEVENLABS_API_KEY              (required for --render)
    ELEVENLABS_VOICE_ID             (optional; default 'JBFqnCBsd6RMkjVDRZzb' = George, warm US male narrator)
    ELEVENLABS_MODEL_ID             (optional; default 'eleven_multilingual_v2' — best SSML <break> fidelity)

Voice settings tuned for documentary narration:
    stability=0.55, similarity_boost=0.85, style=0.05, speed=1.0

The script intentionally defaults to dry-run so accidental invocations don't burn paid credits.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VOICEOVER_SOURCE = REPO_ROOT / "docs" / "voiceover.txt"
AUDIO_DIR = REPO_ROOT / "videos" / "audio"
CONCAT_LIST = AUDIO_DIR / "_concat.txt"
FULL_TRACK = AUDIO_DIR / "granum_demo.mp3"

DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # George
DEFAULT_MODEL_ID = "eleven_multilingual_v2"

BEAT_HEADER_RE = re.compile(r"^###\s*BEAT\s+(\d+)\b.*###\s*$", re.MULTILINE)


@dataclass
class Beat:
    number: int
    header: str
    text: str

    @property
    def word_count(self) -> int:
        # Strip SSML tags before counting
        plain = re.sub(r"<[^>]+>", "", self.text)
        return len(plain.split())

    @property
    def filename(self) -> str:
        return f"beat_{self.number}.mp3"


def parse_voiceover(source: Path) -> list[Beat]:
    raw = source.read_text(encoding="utf-8")
    # Strip comment lines (lines starting with `#` that aren't beat headers)
    lines: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") and not stripped.startswith("###"):
            continue
        lines.append(line)
    clean = "\n".join(lines)

    matches = list(BEAT_HEADER_RE.finditer(clean))
    if not matches:
        raise SystemExit(f"No `### BEAT N ###` markers found in {source}")

    beats: list[Beat] = []
    for i, m in enumerate(matches):
        number = int(m.group(1))
        header = m.group(0).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(clean)
        text = clean[start:end].strip()
        if not text:
            raise SystemExit(f"Beat {number} has empty body")
        beats.append(Beat(number=number, header=header, text=text))
    return beats


def print_plan(beats: list[Beat], voice_id: str, model_id: str) -> None:
    print("=" * 72)
    print("Granum voiceover render plan (DRY RUN — no API calls made)")
    print("=" * 72)
    print(f"Source:    {VOICEOVER_SOURCE.relative_to(REPO_ROOT)}")
    print(f"Output:    {AUDIO_DIR.relative_to(REPO_ROOT)}/")
    print(f"Voice ID:  {voice_id}")
    print(f"Model:     {model_id}")
    print(f"Beats:     {len(beats)}")
    total_words = sum(b.word_count for b in beats)
    print(f"Total words: {total_words} (~{total_words / 140:.1f} min at 140 wpm)")
    print()
    for b in beats:
        print(f"  Beat {b.number}: {b.word_count:>3} words  -> {b.filename}")
        first_line = b.text.splitlines()[0][:80]
        print(f"           preview: {first_line}{'...' if len(b.text.splitlines()[0]) > 80 else ''}")
    print()
    print("To actually render, re-run with --render (requires ELEVENLABS_API_KEY).")


def render_beat(client, beat: Beat, voice_id: str, model_id: str, out_path: Path) -> None:
    from elevenlabs import VoiceSettings, save

    print(f"  Beat {beat.number}: rendering {beat.word_count} words... ", end="", flush=True)
    audio = client.text_to_speech.convert(
        text=beat.text,
        voice_id=voice_id,
        model_id=model_id,
        voice_settings=VoiceSettings(
            stability=0.55,
            similarity_boost=0.85,
            style=0.05,
            speed=1.0,
        ),
    )
    save(audio, str(out_path))
    size_kb = out_path.stat().st_size // 1024
    print(f"wrote {out_path.name} ({size_kb} KB)")


def concatenate(beats: list[Beat]) -> None:
    if not shutil.which("ffmpeg"):
        print("WARNING: ffmpeg not on PATH; skipping concatenation. Per-beat MP3s are still in place.")
        return
    CONCAT_LIST.write_text(
        "\n".join(f"file '{(AUDIO_DIR / b.filename).resolve()}'" for b in beats) + "\n",
        encoding="utf-8",
    )
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(CONCAT_LIST),
        "-c", "copy",
        str(FULL_TRACK),
    ]
    print(f"Concatenating with: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffmpeg failed:\n{result.stderr}")
        raise SystemExit(result.returncode)
    size_kb = FULL_TRACK.stat().st_size // 1024
    print(f"Wrote {FULL_TRACK.relative_to(REPO_ROOT)} ({size_kb} KB)")
    CONCAT_LIST.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--render", action="store_true", help="Actually call ElevenLabs API (burns credits)")
    parser.add_argument("--beat", type=int, default=None, help="Render only one beat number")
    parser.add_argument("--voice-id", default=os.environ.get("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID))
    parser.add_argument("--model-id", default=os.environ.get("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID))
    parser.add_argument("--no-concat", action="store_true", help="Skip ffmpeg concatenation step")
    args = parser.parse_args()

    if not VOICEOVER_SOURCE.exists():
        print(f"ERROR: {VOICEOVER_SOURCE} not found", file=sys.stderr)
        return 1
    beats = parse_voiceover(VOICEOVER_SOURCE)
    if args.beat is not None:
        beats = [b for b in beats if b.number == args.beat]
        if not beats:
            print(f"ERROR: --beat {args.beat} not found in source", file=sys.stderr)
            return 1

    if not args.render:
        print_plan(beats, args.voice_id, args.model_id)
        return 0

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("ERROR: ELEVENLABS_API_KEY not set. Add it to .env or export in shell.", file=sys.stderr)
        return 2

    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env", override=False)
    api_key = os.environ.get("ELEVENLABS_API_KEY") or api_key

    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=api_key)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Rendering {len(beats)} beat(s) with voice={args.voice_id} model={args.model_id}")
    for beat in beats:
        out_path = AUDIO_DIR / beat.filename
        render_beat(client, beat, args.voice_id, args.model_id, out_path)

    if args.beat is None and not args.no_concat:
        concatenate(beats)

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
