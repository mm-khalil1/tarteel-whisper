"""Check a transcript against a passage: the core of the /api/check endpoint."""

from .align import align, normalized_words
from .normalize import words as heard_words
from .quran import Word
from .scoring import score


def check(passage: list[Word], transcript: str) -> dict:
    results, extras = align(normalized_words([w.imlaei for w in passage]), heard_words(transcript))
    return {
        "transcript": transcript,
        "words": [
            {
                "surah": passage[r.index].surah,
                "ayah": passage[r.index].ayah,
                "position": passage[r.index].position,
                "page": passage[r.index].page,
                "text": passage[r.index].uthmani,
                "status": r.status,
                **({"heard": r.heard} if r.heard else {}),
            }
            for r in results
        ],
        "extras": [{"after": e.after, "heard": e.heard} for e in extras],
        **score(passage, results),
    }
