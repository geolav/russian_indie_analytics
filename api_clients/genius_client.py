"""
api_clients/genius_client.py
-----------------------------
Genius API client for fetching song lyrics.
Falls back gracefully when lyrics are unavailable.
"""

import re
import time
from typing import Optional

import requests

from config.settings import GENIUS_ACCESS_TOKEN, GENIUS_BASE_URL, REQUEST_DELAY
from utils.cache import cache_get, cache_set
from utils.helpers import retry, clean_text
from utils.logger import get_logger

logger = get_logger(__name__)


class GeniusClient:
    """
    Lightweight Genius API wrapper.

    Searches for songs by artist + title and returns cleaned lyric text.
    HTML tags from the annotations endpoint are stripped automatically.
    """

    def __init__(self) -> None:
        if not GENIUS_ACCESS_TOKEN:
            logger.warning("GENIUS_ACCESS_TOKEN not set – lyrics unavailable.")
        self._session = requests.Session()
        if GENIUS_ACCESS_TOKEN:
            self._session.headers.update({"Authorization": f"Bearer {GENIUS_ACCESS_TOKEN}"})

    # ── Internal HTTP ──────────────────────────────────────────────────────────

    @retry(times=3, delay=1.0, exceptions=(requests.RequestException,))
    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        cache_key = f"genius:{endpoint}:{sorted((params or {}).items())}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        url = f"{GENIUS_BASE_URL}{endpoint}"
        resp = self._session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        cache_set(cache_key, data)
        time.sleep(REQUEST_DELAY)
        return data

    # ── Public API ─────────────────────────────────────────────────────────────

    def search_song(self, artist: str, title: str) -> Optional[dict]:
        """
        Search Genius for a song.

        Returns the first hit's metadata dict or None.
        """
        if not GENIUS_ACCESS_TOKEN:
            return None

        query = f"{artist} {title}"
        data = self._get("/search", {"q": query})
        hits = data.get("response", {}).get("hits", [])

        for hit in hits:
            result = hit.get("result", {})
            artist_name = result.get("primary_artist", {}).get("name", "").lower()
            if artist.lower() in artist_name or artist_name in artist.lower():
                return result

        logger.debug("No Genius match for: %s – %s", artist, title)
        return None

    def get_lyrics_text(self, artist: str, title: str) -> str:
        """
        Return cleaned plain-text lyrics for artist/title.

        Returns an empty string when unavailable.
        Note: Full lyric scraping requires BeautifulSoup and respects ToS limits.
        This implementation returns the lyric preview/snippet from the API.
        """
        song = self.search_song(artist, title)
        if not song:
            return ""

        # The Genius public API returns a snippet/excerpt, not full lyrics.
        # Full lyrics require HTML scraping (out of scope for this example).
        snippet = song.get("snippet") or song.get("title_with_featured", "")
        return clean_text(snippet)

    def get_song_metadata(self, artist: str, title: str) -> dict:
        """Return enriched metadata (release year, features, hot status)."""
        song = self.search_song(artist, title)
        if not song:
            return {}
        return {
            "genius_id": song.get("id"),
            "genius_title": song.get("title"),
            "genius_url": song.get("url"),
            "release_date": song.get("release_date_components"),
            "hot": song.get("stats", {}).get("hot", False),
            "pageviews": song.get("stats", {}).get("pageviews", 0),
        }
