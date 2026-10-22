"""Arabic normalization so that the ASR output and the Quran text compare on
letters only. Harakat are dropped: the model isn't reliable on them, and
flagging them would bury real word mistakes under false alarms."""

import re

_MARKS = re.compile(
    "["
    "ؐ-ؚ"  # Quranic honorifics / small signs
    "ً-ٟ"  # harakat, shadda, sukun, ...
    "ٰ"  # superscript alef
    "ۖ-ۭ"  # Quranic annotation marks (waqf signs, small letters)
    "ـ"  # tatweel
    "]"
)
_LETTERS = str.maketrans(
    {
        "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
        "ى": "ي", "ئ": "ي", "ؤ": "و",
        "ة": "ه",
    }
)
_NON_ARABIC = re.compile(r"[^ء-ي\s]")


def normalize(text: str) -> str:
    text = _MARKS.sub("", text).translate(_LETTERS)
    return " ".join(_NON_ARABIC.sub(" ", text).split())


def words(text: str) -> list[str]:
    return normalize(text).split()
