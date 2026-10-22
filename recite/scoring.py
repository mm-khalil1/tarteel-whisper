"""Per-page mistake counts and points.

A mistake is a wrong or missed word. Extra words are reported but not counted:
students often repeat a phrase to correct themselves, which is good practice.
"""

from .align import WordResult
from .quran import Word

# Points per page by number of mistakes on that page. Tune with teachers.
POINTS_RULES = [(0, 3), (2, 2)]  # (max mistakes, points); anything above -> 1
NOT_RECITED_RATIO = 0.5  # a page with more than half its words missed scores 0


def page_points(mistakes: int, missed: int, total: int) -> int:
    if total and missed / total > NOT_RECITED_RATIO:
        return 0
    for max_mistakes, points in POINTS_RULES:
        if mistakes <= max_mistakes:
            return points
    return 1


def score(words: list[Word], results: list[WordResult]) -> dict:
    pages: dict[int, dict] = {}
    for r in results:
        p = pages.setdefault(words[r.index].page, {"page": words[r.index].page, "words": 0, "wrong": 0, "missed": 0})
        p["words"] += 1
        if r.status in ("wrong", "missed"):
            p[r.status] += 1
    for p in pages.values():
        p["mistakes"] = p["wrong"] + p["missed"]
        p["points"] = page_points(p["mistakes"], p["missed"], p["words"])
    page_list = sorted(pages.values(), key=lambda p: p["page"])
    return {
        "pages": page_list,
        "total_words": len(results),
        "total_mistakes": sum(p["mistakes"] for p in page_list),
        "total_points": sum(p["points"] for p in page_list),
        "max_points": 3 * len(page_list),
    }
