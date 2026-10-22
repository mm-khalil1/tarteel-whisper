from recite.align import align, normalized_words
from recite.normalize import normalize, words
from recite.quran import passage
from recite.scoring import page_points, score


def test_normalize_drops_harakat_and_unifies_letters():
    assert normalize("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ") == "بسم الله الرحمن الرحيم"
    assert normalize("ٱلصَّلَوٰةَ") == normalize("الصلوة")
    assert normalize("إِنَّ") == "ان"


def test_imlaei_text_matches_model_style_output():
    expected = normalized_words([w.imlaei for w in passage(1, 1)])
    heard = words("بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ")
    results, _ = align(expected[:8], heard)
    assert all(r.status == "correct" for r in results)


def test_wrong_missed_and_extra():
    expected = ["قل", "هو", "الله", "احد"]
    results, extras = align(expected, ["قل", "هو", "الله", "الله", "واحد"])
    assert [r.status for r in results] == ["correct", "correct", "correct", "wrong"]
    assert results[3].heard == "واحد" and [e.heard for e in extras] == ["الله"]

    results, _ = align(expected, ["قل", "الله", "احد"])
    assert [r.status for r in results] == ["correct", "missed", "correct", "correct"]


def test_split_or_joined_words_count_as_correct():
    results, extras = align(["يا", "ايها"], ["ياايها"])
    assert [r.status for r in results] == ["correct", "correct"] and not extras


def test_passage_range_and_pages():
    words_ = passage(112, 114)
    assert (words_[0].surah, words_[0].ayah) == (112, 1)
    assert (words_[-1].surah, words_[-1].ayah) == (114, 6)
    assert {w.page for w in words_} == {604}
    assert len(passage(2, 2, 255, 255)) == 50  # Ayat al-Kursi


def test_points():
    assert page_points(0, 0, 100) == 3
    assert page_points(2, 1, 100) == 2
    assert page_points(5, 0, 100) == 1
    assert page_points(60, 60, 100) == 0

    ws = passage(112, 112)
    results, _ = align(normalized_words([w.imlaei for w in ws]), [])
    assert score(ws, results)["total_points"] == 0
