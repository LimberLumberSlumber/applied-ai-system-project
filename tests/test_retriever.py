from showtime.retriever import find_title, load_catalog, related

CAT = load_catalog()


def test_catalog_loads_with_int_seasons():
    assert len(CAT) >= 20
    bb = next(t for t in CAT if t.name == "Breaking Bad")
    assert bb.seasons[1] == 7


def test_exact_and_fuzzy_match():
    assert find_title("inception", CAT)[0].name == "Inception"
    title, score = find_title("breaking bda", CAT)
    assert title.name == "Breaking Bad" and score < 1.0


def test_partial_name_match():
    assert find_title("Stranger", CAT)[0].name == "Stranger Things"


def test_unknown_and_empty_return_none():
    assert find_title("zzzzqqq", CAT)[0] is None
    assert find_title("   ", CAT)[0] is None


def test_related_prefers_same_director():
    inception = find_title("Inception", CAT)[0]
    names = [r[0].name for r in related(inception, CAT, 3)]
    assert names[0] in {"Interstellar", "The Dark Knight", "The Prestige"}
    assert "Inception" not in names


def test_related_uses_cast_and_explains():
    bladerunner = find_title("Blade Runner 2049", CAT)[0]
    top = related(bladerunner, CAT, 5)
    assert any("Ryan Gosling" in reason for _, _, reason in top)
