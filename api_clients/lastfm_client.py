"""
api_clients/lastfm_client.py
-----------------------------
Last.fm API client for supplementary popularity metrics,
listener counts, and tag/genre data.
"""

import time
from typing import Optional

import requests

from config.settings import LASTFM_API_KEY, LASTFM_BASE_URL, REQUEST_DELAY
from utils.cache import cache_get, cache_set
from utils.helpers import retry, safe_get
from utils.logger import get_logger

logger = get_logger(__name__)


class LastFmClient:
    """
    Wrapper around the Last.fm REST API.

    Provides artist info, track tags, listener counts, and weekly charts.
    All responses are cached to minimise repeated network calls.
    """

    def __init__(self) -> None:
        if not LASTFM_API_KEY:
            raise EnvironmentError("LASTFM_API_KEY must be set in .env")
        self._session = requests.Session()

    # ── Internal HTTP ──────────────────────────────────────────────────────────

    @retry(times=3, delay=1.0, exceptions=(requests.RequestException,))
    def _call(self, method: str, **params) -> dict:
        """Execute a Last.fm API method call."""
        payload = {
            "method": method,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            **params,
        }
        cache_key = f"lastfm:{method}:{sorted(params.items())}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        resp = self._session.get(LASTFM_BASE_URL, params=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            logger.warning("Last.fm error %s: %s", data["error"], data.get("message"))
            return {}

        cache_set(cache_key, data)
        time.sleep(REQUEST_DELAY)
        return data

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_artist_info(self, artist: str) -> dict:
        """
        Fetch artist bio, listener count, play count and top tags.

        Returns an empty dict when the artist is not found.
        """
        data = self._call("artist.getinfo", artist=artist)
        return safe_get(data, "artist", default={})

    def get_artist_top_tracks(self, artist: str, limit: int = 20) -> list[dict]:
        """Return top tracks for an artist sorted by listener count."""
        data = self._call("artist.gettoptracks", artist=artist, limit=limit)
        return safe_get(data, "toptracks", "track", default=[])

    def get_artist_tags(self, artist: str) -> list[str]:
        """Return the top genre/tag strings for an artist."""
        info = self.get_artist_info(artist)
        tags_raw = safe_get(info, "tags", "tag", default=[])
        return [t["name"] for t in tags_raw if isinstance(t, dict)]

    def get_track_info(self, artist: str, track: str) -> dict:
        """Fetch detailed track info including tags and listener counts."""
        data = self._call("track.getinfo", artist=artist, track=track)
        return safe_get(data, "track", default={})

    def get_similar_artists(self, artist: str, limit: int = 10) -> list[dict]:
        """Return artists similar to *artist* for network graph construction."""
        data = self._call("artist.getsimilar", artist=artist, limit=limit)
        return safe_get(data, "similarartists", "artist", default=[])

    def get_tag_top_artists(self, tag: str, limit: int = 30) -> list[dict]:
        """Return top artists for a given genre tag."""
        data = self._call("tag.gettopartists", tag=tag, limit=limit)
        return safe_get(data, "topartists", "artist", default=[])

    def get_track_playcount(self, artist: str, track: str) -> int:
        """
        Получить реальное количество прослушиваний трека через Last.fm API.
        Это и есть объективная популярность трека!
        """
        try:
            data = self._call("track.getInfo", artist=artist, track=track)
            track_info = safe_get(data, "track", default={})
            playcount = track_info.get("playcount", 0)
            if playcount:
                return int(playcount)
            return 0
        except Exception as e:
            logger.debug(f"Failed to get playcount for {artist} - {track}: {e}")
            return 0