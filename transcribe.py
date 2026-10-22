"""Transcribe a recitation, and optionally check it against the Quran.

Usage:
    python transcribe.py recitation.mp3                  # just the transcript
    python transcribe.py recitation.mp3 --surah 67       # check against Al-Mulk
    python transcribe.py recitation.mp3 --surah 112 --to-surah 114
"""

import argparse
import json
import sys
from pathlib import Path

from recite import asr, quran
from recite.checker import check


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("audio", help="Path to an audio file (wav, flac, ogg, mp3)")
    parser.add_argument("--surah", type=int, help="Surah to check against")
    parser.add_argument("--to-surah", type=int, help="Last surah of the range (default: --surah)")
    parser.add_argument("--json", action="store_true", help="Print the full check result as JSON")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252

    print(f"Loading {asr.MODEL_ID} on {asr.device()}...", file=sys.stderr)
    audio = asr.load_audio(Path(args.audio).read_bytes())
    print(f"Audio length: {len(audio) / asr.SAMPLE_RATE:.1f} s", file=sys.stderr)
    transcript = asr.transcribe(audio)
    if not args.surah:
        print(transcript)
        return

    result = check(quran.passage(args.surah, args.to_surah or args.surah), transcript)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(transcript, "\n")
    for w in result["words"]:
        if w["status"] != "correct":
            heard = f" (heard {w['heard']})" if "heard" in w else ""
            print(f"  {w['surah']}:{w['ayah']} word {w['position']}: {w['status']} {w['text']}{heard}")
    for p in result["pages"]:
        print(f"Page {p['page']}: {p['mistakes']} mistakes -> {p['points']} points")
    print(f"Total: {result['total_mistakes']} mistakes, {result['total_points']}/{result['max_points']} points")


if __name__ == "__main__":
    main()
