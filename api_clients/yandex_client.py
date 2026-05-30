"""
api_clients/yandex_client.py
-----------------------------
Yandex Music API client using the unofficial yandex-music library.
Provides artist search, top tracks, albums, and audio features.
"""

import time
from typing import Optional, List, Dict, Any

import requests

from config.settings import YANDEX_MUSIC_TOKEN, REQUEST_DELAY
from utils.cache import cache_get, cache_set
from utils.helpers import retry, safe_get
from utils.logger import get_logger

logger = get_logger(__name__)


class YandexMusicClient:
    """
    Wrapper around Yandex Music API.

    Features:
    - Artist search and metadata retrieval
    - Top tracks and albums
    - Audio features (normalized values where available)
    - Request caching
    """

    def __init__(self) -> None:
        if not YANDEX_MUSIC_TOKEN:
            raise EnvironmentError(
                "YANDEX_MUSIC_TOKEN must be set in .env. "
                "Get it via: https://oauth.yandex.ru/authorize?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d"
            )
        self._token = YANDEX_MUSIC_TOKEN
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"OAuth {self._token}"})
        self._api_base = "https://api.music.yandex.net"

    # ── Internal HTTP ──────────────────────────────────────────────────────────

    @retry(times=3, delay=1.5, exceptions=(requests.RequestException,))
    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Perform an authenticated GET against the Yandex Music API."""
        cache_key = f"yandex:{endpoint}:{sorted((params or {}).items())}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        url = f"{self._api_base}{endpoint}"
        logger.debug("Yandex API request: %s", url)
        resp = self._session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        cache_set(cache_key, data)
        time.sleep(REQUEST_DELAY)
        return data

    # ── Public API ─────────────────────────────────────────────────────────────

    def search_artist(self, name: str) -> Optional[dict]:
        """
        Search for an artist by name.

        Returns the top match or None if no results.
        """
        try:
            data = self._get("/search", {"text": name, "type": "artist", "page": 0})
            # Response structure: data["result"]["artists"]["results"]
            result = data.get("result", {})
            artists_data = result.get("artists", {})
            items = artists_data.get("results", []) if isinstance(artists_data, dict) else []

            if not items:
                logger.warning("Artist not found on Yandex Music: %s", name)
                return None

            # Find best match (exact name or closest)
            best = items[0]
            for artist in items:
                artist_name = artist.get("name", "") if isinstance(artist, dict) else ""
                if artist_name.lower() == name.lower():
                    best = artist
                    break

            if not isinstance(best, dict):
                logger.warning("Invalid artist data for %s", name)
                return None

            return {
                "id": best.get("id"),
                "name": best.get("name", name),
                "genres": best.get("genres", []),
                "popularity": best.get("popularity", 50),
                "followers": best.get("counts", {}).get("fans", 0) if isinstance(best.get("counts"), dict) else 0,
                "image_url": best.get("cover", {}).get("uri", "") if isinstance(best.get("cover"), dict) else "",
            }
        except Exception as e:
            logger.error("Error searching artist %s: %s", name, e)
            return None

    def get_artist_top_tracks(self, artist_id: str, limit: int = 20) -> list[dict]:
        """Return top tracks for an artist."""
        try:
            data = self._get(f"/artists/{artist_id}/tracks", {"page_size": limit})
            result = data.get("result", {})
            # Result can be a dict with 'tracks' or a list
            if isinstance(result, dict):
                tracks = result.get("tracks", [])
            elif isinstance(result, list):
                tracks = result
            else:
                tracks = []

            result_list = []
            for track in tracks[:limit]:
                if not isinstance(track, dict):
                    continue
                # Get album info
                albums = track.get("albums", [])
                album = albums[0] if albums else {}
                result_list.append({
                    "id": track.get("id"),
                    "name": track.get("title"),
                    "duration_ms": track.get("duration_ms", 0),
                    "explicit": track.get("explicit", False),
                    "popularity": track.get("popularity", 0),
                    "album": album.get("title", "") if isinstance(album, dict) else "",
                    "release_date": album.get("release_date", "") if isinstance(album, dict) else "",
                })
            return result_list
        except Exception as e:
            logger.error("Error getting top tracks for artist %s: %s", artist_id, e)
            return []

    def get_artist_albums(self, artist_id: str, limit: int = 20) -> list[dict]:
        """Return albums for an artist."""
        try:
            data = self._get(f"/artists/{artist_id}/albums", {"page_size": limit})
            result = data.get("result", {})
            if isinstance(result, dict):
                albums = result.get("albums", [])
            elif isinstance(result, list):
                albums = result
            else:
                albums = []

            result_list = []
            for album in albums[:limit]:
                if not isinstance(album, dict):
                    continue
                result_list.append({
                    "id": album.get("id"),
                    "title": album.get("title"),
                    "year": album.get("year"),
                    "track_count": album.get("track_count", 0),
                    "genre": album.get("genre", "unknown"),
                })
            return result_list
        except Exception as e:
            logger.error("Error getting albums for artist %s: %s", artist_id, e)
            return []

    def get_album_tracks(self, album_id: str) -> list[dict]:
        """Return tracks inside an album."""
        try:
            data = self._get(f"/albums/{album_id}/with-tracks")
            result = data.get("result", {})
            if isinstance(result, dict):
                volumes = result.get("volumes", [])
                tracks = volumes[0] if volumes else []
            elif isinstance(result, list):
                tracks = result
            else:
                tracks = []

            result_list = []
            for track in tracks:
                if not isinstance(track, dict):
                    continue
                result_list.append({
                    "id": track.get("id"),
                    "name": track.get("title"),
                    "duration_ms": track.get("duration_ms", 0),
                })
            return result_list
        except Exception as e:
            logger.error("Error getting album tracks for album %s: %s", album_id, e)
            return []

    def get_track_audio_features(self, track_id: str) -> dict:
        """
        Return audio features for a track.
        Yandex provides limited audio features; we derive what we can.
        """
        try:
            data = self._get(f"/tracks/{track_id}")
            result = data.get("result", {})
            if isinstance(result, list):
                track = result[0] if result else {}
            else:
                track = result

            if not isinstance(track, dict):
                return self._get_default_features()

            duration = track.get("duration_ms", 0)

            # Get genre from albums
            albums = track.get("albums", [])
            album = albums[0] if albums else {}
            genres = album.get("genre", "unknown") if isinstance(album, dict) else "unknown"
            genres_str = " ".join(genres) if isinstance(genres, list) else str(genres)

            # Simple heuristic based on genre
            genres_lower = genres_str.lower()
            if "rock" in genres_lower or "punk" in genres_lower:
                energy = 0.7
                danceability = 0.5
                valence = 0.6
            elif "pop" in genres_lower:
                energy = 0.65
                danceability = 0.7
                valence = 0.7
            elif "electronic" in genres_lower or "dance" in genres_lower:
                energy = 0.8
                danceability = 0.8
                valence = 0.6
            elif "folk" in genres_lower or "acoustic" in genres_lower:
                energy = 0.3
                danceability = 0.4
                valence = 0.5
            else:
                energy = 0.5
                danceability = 0.5
                valence = 0.5

            # Duration-based adjustments
            if duration > 300000:  # >5 min
                energy *= 0.9

            return {
                "danceability": danceability,
                "energy": energy,
                "valence": valence,
                "acousticness": 0.5,
                "instrumentalness": 0.1,
                "liveness": 0.1,
                "speechiness": 0.05,
                "tempo": 120.0,
                "loudness": -8.0,
                "key": 0,
                "mode": 1,
                "time_signature": 4,
            }
        except Exception as e:
            logger.error("Error getting audio features for track %s: %s", track_id, e)
            return self._get_default_features()

    def _get_default_features(self) -> dict:
        """Return default audio features."""
        return {
            "danceability": 0.5,
            "energy": 0.5,
            "valence": 0.5,
            "acousticness": 0.5,
            "instrumentalness": 0.1,
            "liveness": 0.1,
            "speechiness": 0.05,
            "tempo": 120.0,
            "loudness": -8.0,
            "key": 0,
            "mode": 1,
            "time_signature": 4,
        }

    def get_related_artists(self, artist_id: str) -> list[dict]:
        """Return similar artists for building the network graph."""
        try:
            data = self._get(f"/artists/{artist_id}/similar")
            result = data.get("result", {})
            if isinstance(result, dict):
                artists = result.get("artists", [])
            elif isinstance(result, list):
                artists = result
            else:
                artists = []

            result_list = []
            for artist in artists[:10]:
                if not isinstance(artist, dict):
                    continue
                result_list.append({
                    "id": artist.get("id"),
                    "name": artist.get("name"),
                })
            return result_list
        except Exception as e:
            logger.error("Error getting related artists for %s: %s", artist_id, e)
            return []

    def get_track(self, track_id: str) -> Optional[dict]:
        """Fetch full track metadata."""
        try:
            data = self._get(f"/tracks/{track_id}")
            result = data.get("result", {})
            if isinstance(result, list):
                track = result[0] if result else {}
            else:
                track = result

            if not isinstance(track, dict):
                return None

            return {
                "id": track.get("id"),
                "title": track.get("title"),
                "duration_ms": track.get("duration_ms", 0),
                "explicit": track.get("explicit", False),
            }
        except requests.HTTPError as exc:
            logger.error("Failed to fetch track %s: %s", track_id, exc)
            return None