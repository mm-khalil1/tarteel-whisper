"""Build data/quran.json from the Quran.com API (run once; the output is committed).

For every ayah we keep each word in Uthmani script (for display), in imlaei
(standard) spelling (for matching -- it's what the ASR model outputs), and the
Madani mushaf page it sits on (for per-page scoring).

Usage:
    python scripts/build_quran_data.py
"""

import json
import time
import urllib.request
from pathlib import Path

API = "https://api.quran.com/api/v4"
OUT = Path(__file__).resolve().parent.parent / "data" / "quran.json"


def get(url: str) -> dict:
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "tarteel-whisper-data-builder/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2**attempt)


def main():
    chapters = get(f"{API}/chapters?language=en")["chapters"]
    surahs = []
    for ch in chapters:
        n = ch["id"]
        ayahs, page = [], 1
        while page:
            data = get(
                f"{API}/verses/by_chapter/{n}?words=true&per_page=50&page={page}"
                "&word_fields=text_uthmani,text_imlaei"
            )
            for v in data["verses"]:
                words = [
                    [w["text_uthmani"], w["text_imlaei"], w["page_number"]]
                    for w in v["words"]
                    if w["char_type_name"] == "word"
                ]
                ayahs.append({"n": v["verse_number"], "words": words})
            page = data["pagination"]["next_page"]
        assert len(ayahs) == ch["verses_count"], (n, len(ayahs))
        surahs.append(
            {
                "n": n,
                "name_ar": ch["name_arabic"],
                "name_en": ch["name_simple"],
                "ayahs": ayahs,
            }
        )
        print(f"{n:3d} {ch['name_simple']:<20} {len(ayahs)} ayahs")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"surahs": surahs}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
