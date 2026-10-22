"""Word-level alignment of what was heard against what was expected."""

from dataclasses import dataclass
from difflib import SequenceMatcher

from .normalize import normalize


@dataclass
class WordResult:
    index: int  # into the expected word list
    status: str  # "correct" | "wrong" | "missed"
    heard: str = ""  # what the model heard instead (for "wrong")


@dataclass
class Extra:
    after: int  # index of the expected word it follows (-1 = before the first)
    heard: str


def align(expected: list[str], heard: list[str]) -> tuple[list[WordResult], list[Extra]]:
    """Both lists are already-normalized words. Returns one result per expected
    word, plus words that were heard but not expected (repetitions, isti'adha,
    basmala, additions)."""
    results: list[WordResult] = []
    extras: list[Extra] = []
    sm = SequenceMatcher(a=expected, b=heard, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            results += [WordResult(i, "correct") for i in range(i1, i2)]
        elif op == "delete":
            results += [WordResult(i, "missed") for i in range(i1, i2)]
        elif op == "insert":
            extras += [Extra(i1 - 1, heard[j]) for j in range(j1, j2)]
        else:  # replace
            # The model sometimes splits or joins words (يا أيها / ياأيها):
            # same letters overall means it was recited correctly.
            if "".join(expected[i1:i2]) == "".join(heard[j1:j2]):
                results += [WordResult(i, "correct") for i in range(i1, i2)]
                continue
            pairs = dict(_pair_by_similarity(expected[i1:i2], heard[j1:j2]))
            for k in range(i2 - i1):
                if k in pairs:
                    results.append(WordResult(i1 + k, "wrong", heard[j1 + pairs[k]]))
                else:
                    results.append(WordResult(i1 + k, "missed"))
            # Unpaired heard words go after the nearest preceding expected word.
            paired_heard = sorted(pairs.items(), key=lambda kv: kv[1])
            for j in set(range(j2 - j1)) - set(pairs.values()):
                before = [k for k, jj in paired_heard if jj < j]
                extras.append(Extra(i1 + before[-1] if before else i1 - 1, heard[j1 + j]))
    return results, extras


def _pair_by_similarity(exp: list[str], hrd: list[str]) -> list[tuple[int, int]]:
    """Order-preserving pairing of expected and heard words that maximizes total
    letter similarity (Needleman-Wunsch with free gaps). Blocks are short."""
    n, m = len(exp), len(hrd)
    sim = [[SequenceMatcher(a=e, b=h).ratio() for h in hrd] for e in exp]
    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            best[i][j] = max(sim[i][j] + best[i + 1][j + 1], best[i + 1][j], best[i][j + 1])
    pairs, i, j = [], 0, 0
    while i < n and j < m:
        if best[i][j] == sim[i][j] + best[i + 1][j + 1]:
            pairs.append((i, j))
            i, j = i + 1, j + 1
        elif best[i][j] == best[i + 1][j]:
            i += 1
        else:
            j += 1
    return pairs


def normalized_words(texts: list[str]) -> list[str]:
    """Normalize each expected word, keeping a 1:1 mapping with the input."""
    return [normalize(t).replace(" ", "") for t in texts]
