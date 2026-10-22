"""Access to the Quran text in data/quran.json (see scripts/build_quran_data.py)."""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "quran.json"


@dataclass
class Word:
    surah: int
    ayah: int
    position: int  # 1-based within the ayah
    uthmani: str  # for display
    imlaei: str  # standard spelling, for matching
    page: int  # Madani mushaf page


@lru_cache(maxsize=1)
def _surahs() -> list[dict]:
    return json.loads(DATA.read_text(encoding="utf-8"))["surahs"]


def surah_list() -> list[dict]:
    return [
        {"n": s["n"], "name_ar": s["name_ar"], "name_en": s["name_en"], "ayahs": len(s["ayahs"])}
        for s in _surahs()
    ]


def passage(from_surah: int, to_surah: int, from_ayah: int = 1, to_ayah: int | None = None) -> list[Word]:
    """All words from from_surah:from_ayah to to_surah:to_ayah (inclusive).
    to_ayah defaults to the last ayah of to_surah."""
    if not 1 <= from_surah <= to_surah <= 114:
        raise ValueError("surah range must satisfy 1 <= from_surah <= to_surah <= 114")
    words = []
    for s in _surahs()[from_surah - 1 : to_surah]:
        for a in s["ayahs"]:
            if s["n"] == from_surah and a["n"] < from_ayah:
                continue
            if s["n"] == to_surah and to_ayah is not None and a["n"] > to_ayah:
                continue
            for i, (uthmani, imlaei, page) in enumerate(a["words"], 1):
                words.append(Word(s["n"], a["n"], i, uthmani, imlaei, page))
    if not words:
        raise ValueError("the requested range contains no ayat")
    return words
