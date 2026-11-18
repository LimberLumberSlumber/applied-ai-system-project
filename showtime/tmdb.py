"""Optional live source: TMDB v3 API. Returns None when no key is set so the catalog is used.

This product uses the TMDB API but is not endorsed or certified by TMDB.
"""
import os
import statistics
from pathlib import Path

import requests

from .models import Title

BASE = "https://api.themoviedb.org/3"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
TIMEOUT = 6


def get_key():
    """API key from env var TMDB_API_KEY, else from a gitignored .env file. None if absent."""
    key = os.environ.get("TMDB_API_KEY")
    if key:
        return key.strip()
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.startswith("TMDB_API_KEY="):
                return line.split("=", 1)[1].strip() or None
    return None


def _get(path: str, key: str, **params) -> dict:
    resp = requests.get(f"{BASE}{path}", params={"api_key": key, **params}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _people(credits: dict) -> tuple:
    director = next((c["name"] for c in credits.get("crew", []) if c.get("job") == "Director"), "")
    cast = [c["name"] for c in credits.get("cast", [])[:3]]
    return director, cast


def lookup(query: str, getter=_get):
    """Search TMDB for a movie or show and return a Title (source 'tmdb'), or None.

    Raises on network or HTTP errors; the planner catches these and falls back to the catalog.
    """
    key = get_key()
    if not key or not (query or "").strip():
        return None
    hits = getter("/search/multi", key, query=query).get("results", [])
    hit = next((h for h in hits if h.get("media_type") in ("movie", "tv")), None)
    if hit is None:
        return None
    if hit["media_type"] == "movie":
        data = getter(f"/movie/{hit['id']}", key, append_to_response="credits")
        director, cast = _people(data.get("credits", {}))
        return Title(
            name=data["title"], kind="movie", runtime=data.get("runtime") or 0,
            director=director, cast=cast, genres=[g["name"].lower() for g in data.get("genres", [])],
            year=int((data.get("release_date") or "0")[:4] or 0), source="tmdb",
        )
    data = getter(f"/tv/{hit['id']}", key, append_to_response="credits")
    seasons = {s["season_number"]: s["episode_count"] for s in data.get("seasons", [])
               if s.get("season_number", 0) > 0 and s.get("episode_count", 0) > 0}
    runtime = _episode_runtime(data, seasons, key, getter, hit["id"])
    _, cast = _people(data.get("credits", {}))
    creators = data.get("created_by", [])
    return Title(
        name=data["name"], kind="show", runtime=runtime, seasons=seasons,
        director=creators[0]["name"] if creators else "", cast=cast,
        genres=[g["name"].lower() for g in data.get("genres", [])],
        year=int((data.get("first_air_date") or "0")[:4] or 0), source="tmdb",
    )


def _episode_runtime(data: dict, seasons: dict, key: str, getter, tv_id: int) -> int:
    """episode_run_time is often empty, so fall back to the median of real episode runtimes."""
    if data.get("episode_run_time"):
        return int(statistics.median(data["episode_run_time"]))
    if seasons:
        first = getter(f"/tv/{tv_id}/season/{min(seasons)}", key)
        runtimes = [e["runtime"] for e in first.get("episodes", []) if e.get("runtime")]
        if runtimes:
            return int(statistics.median(runtimes))
    return 0
