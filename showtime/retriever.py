"""Retrieval over the catalog: fuzzy title lookup and related-title scoring."""
import json
from difflib import SequenceMatcher
from pathlib import Path

from .models import Title

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.json"


def load_catalog(path: Path = CATALOG_PATH) -> list:
    """Load titles from JSON. Season keys come back as ints."""
    with open(path, encoding="utf-8") as handle:
        rows = json.load(handle)
    titles = []
    for row in rows:
        row["seasons"] = {int(k): v for k, v in row.get("seasons", {}).items()}
        titles.append(Title(**row))
    return titles


def _norm(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum() or ch == " ").strip()


def find_title(query: str, titles: list, threshold: float = 0.6) -> tuple:
    """Return (best Title or None, match score 0..1). Substring hits score high."""
    q = _norm(query)
    if not q:
        return None, 0.0
    best, best_score = None, 0.0
    for title in titles:
        name = _norm(title.name)
        score = SequenceMatcher(None, q, name).ratio()
        if q == name:
            score = 1.0
        elif q in name or name in q:
            score = max(score, 0.85)
        if score > best_score:
            best, best_score = title, score
    if best_score < threshold:
        return None, round(best_score, 2)
    return best, round(best_score, 2)


def related(title: Title, titles: list, k: int = 3) -> list:
    """Return up to k (Title, score, reason) ranked by shared director, cast, and genres."""
    ranked = []
    for other in titles:
        if other.name == title.name:
            continue
        score, reasons = 0.0, []
        if title.director and other.director == title.director:
            score += 3
            reasons.append(f"same director/creator ({other.director})")
        shared_cast = sorted(set(title.cast) & set(other.cast))
        if shared_cast:
            score += 2 * len(shared_cast)
            reasons.append("shared cast: " + ", ".join(shared_cast))
        shared_genres = sorted(set(title.genres) & set(other.genres))
        if shared_genres:
            score += len(shared_genres)
            reasons.append("shared genre: " + ", ".join(shared_genres))
        if score > 0:
            ranked.append((other, score, "; ".join(reasons)))
    ranked.sort(key=lambda r: (-r[1], r[0].name))
    return ranked[:k]
