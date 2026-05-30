# """
# api_clients/spotify_client.py
# ------------------------------
# Spotify Web API client with OAuth2 client-credentials flow,
# automatic token refresh, caching, and polite rate limiting.
# """
#
# import time
# import base64
# from typing import Optional
#
# import requests
#
# from config.settings import (
#     SPOTIFY_CLIENT_ID,
#     SPOTIFY_CLIENT_SECRET,
#     SPOTIFY_MARKET,
#     REQUEST_DELAY,
# )
# from utils.cache import cache_get, cache_set
# from utils.helpers import retry, safe_get
# from utils.logger import get_logger
#
# logger = get_logger(__name__)
#
# _TOKEN_URL = "https://accounts.spotify.com/api/token"
# _API_BASE = "https://api.spotify.com/v1"
#
#
# class SpotifyClient:
#     """
#     Thin wrapper around the Spotify Web API.
#
#     Features:
#     - Automatic client-credentials token acquisition & refresh
#     - Request-level caching (TTL defined in settings)
#     - Exponential back-off on transient failures
#     - Polite rate-limiting delay between requests
#     """
#
#     def __init__(self) -> None:
#         self._access_token: str = ""
#         self._token_expires_at: float = 0.0
#         self._session = requests.Session()
#
#     # ── Auth ───────────────────────────────────────────────────────────────────
#
#     def _get_token(self) -> None:
#         """Fetch a new access token using client credentials."""
#         if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
#             raise EnvironmentError(
#                 "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env"
#             )
#         credentials = base64.b64encode(
#             f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
#         ).decode()
#         resp = self._session.post(
#             _TOKEN_URL,
#             headers={"Authorization": f"Basic {credentials}"},
#             data={"grant_type": "client_credentials"},
#             timeout=10,
#         )
#         resp.raise_for_status()
#         data = resp.json()
#         self._access_token = data["access_token"]
#         self._token_expires_at = time.time() + data.get("expires_in", 3600) - 60
#
#     def _ensure_token(self) -> None:
#         if time.time() >= self._token_expires_at:
#             logger.info("Refreshing Spotify access token …")
#             self._get_token()
#
#     # ── Internal HTTP ──────────────────────────────────────────────────────────
#
#     @retry(times=3, delay=1.5, exceptions=(requests.RequestException,))
#     def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
#         """Perform an authenticated GET against the Spotify API."""
#         self._ensure_token()
#         cache_key = f"spotify:{endpoint}:{sorted((params or {}).items())}"
#         cached = cache_get(cache_key)
#         if cached is not None:
#             return cached
#
#         url = f"{_API_BASE}{endpoint}"
#         resp = self._session.get(
#             url,
#             headers={"Authorization": f"Bearer {self._access_token}"},
#             params=params,
#             timeout=15,
#         )
#         if resp.status_code == 429:
#             retry_after = int(resp.headers.get("Retry-After", 5))
#             logger.warning("Rate limited by Spotify, sleeping %ds …", retry_after)
#             time.sleep(retry_after)
#             resp = self._session.get(
#                 url,
#                 headers={"Authorization": f"Bearer {self._access_token}"},
#                 params=params,
#                 timeout=15,
#             )
#         resp.raise_for_status()
#         data = resp.json()
#         cache_set(cache_key, data)
#         time.sleep(REQUEST_DELAY)
#         return data
#
#     # ── Public API ─────────────────────────────────────────────────────────────
#
#     def search_artist(self, name: str) -> Optional[dict]:
#         """
#         Search for an artist by name.
#
#         Returns the top match or None if no results.
#         """
#         data = self._get("/search", {"q": name, "type": "artist", "limit": 1})
#         items = safe_get(data, "artists", "items", default=[])
#         if not items:
#             logger.warning("Artist not found on Spotify: %s", name)
#             return None
#         return items[0]
#
#     def get_artist_top_tracks(self, artist_id: str) -> list[dict]:
#         """Return up to 10 top tracks for an artist in the RU market."""
#         data = self._get(f"/artists/{artist_id}/top-tracks", {})
#         return data.get("tracks", [])
#
#     def get_artist_albums(self, artist_id: str, limit: int = 20) -> list[dict]:
#         """Return albums for an artist (albums + singles)."""
#         data = self._get(
#             f"/artists/{artist_id}/albums",
#             {"include_groups": "album,single", "limit": limit},
#         )
#         return data.get("items", [])
#
#     def get_album_tracks(self, album_id: str) -> list[dict]:
#         """Return tracks inside an album."""
#         data = self._get(f"/albums/{album_id}/tracks", {"limit": 50})
#         return data.get("items", [])
#
#     def get_audio_features(self, track_ids: list[str]) -> list[dict]:
#         """
#         Return audio features for up to 100 tracks at once.
#
#         Automatically chunks larger lists.
#         """
#         results: list[dict] = []
#         for i in range(0, len(track_ids), 100):
#             chunk = track_ids[i : i + 100]
#             data = self._get("/audio-features", {"ids": ",".join(chunk)})
#             features = data.get("audio_features") or []
#             results.extend([f for f in features if f])  # filter None entries
#         return results
#
#     def get_track(self, track_id: str) -> Optional[dict]:
#         """Fetch full track metadata."""
#         try:
#             return self._get(f"/tracks/{track_id}", {})
#         except requests.HTTPError as exc:
#             logger.error("Failed to fetch track %s: %s", track_id, exc)
#             return None
#
#     def get_related_artists(self, artist_id: str) -> list[dict]:
#         """Return related artists for building the network graph."""
#         data = self._get(f"/artists/{artist_id}/related-artists")
#         return data.get("artists", [])
