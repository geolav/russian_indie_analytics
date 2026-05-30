# """
# services/collector.py
# ---------------------
# Orchestrates data collection from Spotify, Last.fm, and Genius.
# Converts raw API responses into TrackRecord / ArtistRecord objects
# and persists them to CSV files for downstream analytics.
# """
#
# from __future__ import annotations
#
# import time
# from pathlib import Path
# from typing import Optional
#
# import pandas as pd
#
# from api_clients import SpotifyClient, LastFmClient, GeniusClient
# from config.settings import (
#     SEED_ARTISTS,
#     MAX_TRACKS_PER_ARTIST,
#     RAW_DIR,
#     REQUEST_DELAY,
# )
# from data.models import ArtistRecord, TrackRecord
# from utils.helpers import ms_to_min, safe_get
# from utils.logger import get_logger
#
# logger = get_logger(__name__)
#
#
# class DataCollector:
#     """
#     High-level data collection pipeline.
#
#     Usage:
#         collector = DataCollector()
#         collector.collect_all()        # fetch everything
#         collector.load_tracks_df()     # returns pd.DataFrame
#     """
#
#     TRACKS_CSV = RAW_DIR / "tracks.csv"
#     ARTISTS_CSV = RAW_DIR / "artists.csv"
#     NETWORK_CSV = RAW_DIR / "artist_network.csv"
#
#     def __init__(self) -> None:
#         self.spotify = SpotifyClient()
#         self.lastfm = LastFmClient()
#         self.genius = GeniusClient()
#
#         self._artists: dict[str, ArtistRecord] = {}   # spotify_id → ArtistRecord
#         self._tracks: list[TrackRecord] = []
#
#     # ── Main entry point ───────────────────────────────────────────────────────
#
#     def collect_all(self, artists: Optional[list[str]] = None) -> None:
#         """
#         Run the full collection pipeline for *artists* (default: SEED_ARTISTS).
#         Saves results to CSV at the end.
#         """
#         targets = artists or SEED_ARTISTS
#         logger.info("Starting data collection for %d artists …", len(targets))
#
#         for name in targets:
#             try:
#                 self._collect_artist(name)
#             except Exception as exc:
#                 logger.error("Failed to collect data for '%s': %s", name, exc)
#             time.sleep(REQUEST_DELAY)
#
#         self._save_to_csv()
#         logger.info(
#             "Collection complete. %d artists, %d tracks saved.",
#             len(self._artists), len(self._tracks),
#         )
#
#     # ── Per-artist collection ──────────────────────────────────────────────────
#
#     def _collect_artist(self, name: str) -> None:
#         """Collect all data for a single artist by name."""
#         logger.info("Collecting: %s", name)
#
#         # 1. Resolve Spotify artist
#         sp_artist = self.spotify.search_artist(name)
#         if not sp_artist:
#             return
#
#         artist_id = sp_artist["id"]
#         genres = sp_artist.get("genres", [])
#         followers = safe_get(sp_artist, "followers", "total", default=0)
#
#         # 2. Last.fm supplementary data
#         lfm_info = self.lastfm.get_artist_info(name)
#         listeners = int(safe_get(lfm_info, "stats", "listeners", default=0) or 0)
#         playcount = int(safe_get(lfm_info, "stats", "playcount", default=0) or 0)
#         lfm_tags = self.lastfm.get_artist_tags(name)
#
#         # 3. Related artists for network graph
#         related = self.spotify.get_related_artists(artist_id)
#         related_names = [r["name"] for r in related[:5]]
#
#         # 4. Build ArtistRecord
#         artist = ArtistRecord(
#             spotify_id=artist_id,
#             name=sp_artist.get("name", name),
#             genres=genres,
#             popularity=sp_artist.get("popularity", 0),
#             followers=followers,
#             lastfm_listeners=listeners,
#             lastfm_playcount=playcount,
#             lastfm_tags=lfm_tags,
#             related_artists=related_names,
#             image_url=safe_get(sp_artist, "images", 0, "url", default=""),
#         )
#         self._artists[artist_id] = artist
#
#         # 5. Collect top tracks + audio features
#         sp_tracks = self.spotify.get_artist_top_tracks(artist_id)
#         sp_tracks = sp_tracks[:MAX_TRACKS_PER_ARTIST]
#         track_ids = [t["id"] for t in sp_tracks]
#         features_list = self.spotify.get_audio_features(track_ids)
#         features_map = {f["id"]: f for f in features_list if f and "id" in f}
#
#         for sp_track in sp_tracks:
#             self._build_track(sp_track, artist, features_map)
#
#     def _build_track(
#         self,
#         sp_track: dict,
#         artist: ArtistRecord,
#         features_map: dict[str, dict],
#     ) -> None:
#         """Convert Spotify track + audio features into a TrackRecord."""
#         tid = sp_track.get("id", "")
#         feats = features_map.get(tid, {})
#
#         # Release year extraction
#         release_date = safe_get(sp_track, "album", "release_date", default="")
#         release_year: Optional[int] = None
#         try:
#             release_year = int(release_date[:4]) if release_date else None
#         except ValueError:
#             pass
#
#         album_name = safe_get(sp_track, "album", "name", default="")
#
#         # Genius lyrics snippet
#         lyrics = self.genius.get_lyrics_text(artist.name, sp_track.get("name", ""))
#
#         track = TrackRecord(
#             track_id=tid,
#             title=sp_track.get("name", ""),
#             artist=artist.name,
#             artist_id=artist.spotify_id,
#             album=album_name,
#             release_date=release_date,
#             release_year=release_year,
#             popularity=sp_track.get("popularity", 0),
#             duration_ms=sp_track.get("duration_ms", 0),
#             duration_min=ms_to_min(sp_track.get("duration_ms", 0)),
#             explicit=sp_track.get("explicit", False),
#             preview_url=sp_track.get("preview_url") or "",
#             spotify_url=safe_get(sp_track, "external_urls", "spotify", default=""),
#             danceability=feats.get("danceability", 0.0),
#             energy=feats.get("energy", 0.0),
#             valence=feats.get("valence", 0.0),
#             acousticness=feats.get("acousticness", 0.0),
#             instrumentalness=feats.get("instrumentalness", 0.0),
#             liveness=feats.get("liveness", 0.0),
#             speechiness=feats.get("speechiness", 0.0),
#             tempo=feats.get("tempo", 0.0),
#             loudness=feats.get("loudness", 0.0),
#             key=feats.get("key", 0),
#             mode=feats.get("mode", 1),
#             time_signature=feats.get("time_signature", 4),
#             lyrics_snippet=lyrics,
#         )
#         self._tracks.append(track)
#
#     # ── Persistence ────────────────────────────────────────────────────────────
#
#     def _save_to_csv(self) -> None:
#         """Persist collected data to CSV files."""
#         # Tracks
#         if self._tracks:
#             df_tracks = pd.DataFrame([t.__dict__ for t in self._tracks])
#             df_tracks.to_csv(self.TRACKS_CSV, index=False, encoding="utf-8-sig")
#             logger.info("Saved %d tracks → %s", len(df_tracks), self.TRACKS_CSV)
#
#         # Artists
#         if self._artists:
#             rows = []
#             for ar in self._artists.values():
#                 row = ar.__dict__.copy()
#                 row["genres"] = "|".join(ar.genres)
#                 row["lastfm_tags"] = "|".join(ar.lastfm_tags)
#                 row["related_artists"] = "|".join(ar.related_artists)
#                 rows.append(row)
#             df_artists = pd.DataFrame(rows)
#             df_artists.to_csv(self.ARTISTS_CSV, index=False, encoding="utf-8-sig")
#             logger.info("Saved %d artists → %s", len(df_artists), self.ARTISTS_CSV)
#
#         # Network edges
#         edges = []
#         for ar in self._artists.values():
#             for rel in ar.related_artists:
#                 edges.append({"source": ar.name, "target": rel})
#         if edges:
#             pd.DataFrame(edges).to_csv(self.NETWORK_CSV, index=False, encoding="utf-8-sig")
#             logger.info("Saved %d network edges → %s", len(edges), self.NETWORK_CSV)
#
#     # ── Data loaders ───────────────────────────────────────────────────────────
#
#     @staticmethod
#     def load_tracks_df() -> pd.DataFrame:
#         """Load the tracks CSV into a DataFrame. Returns empty DF if missing."""
#         path = DataCollector.TRACKS_CSV
#         if not path.exists():
#             logger.warning("Tracks CSV not found at %s", path)
#             return pd.DataFrame()
#         return pd.read_csv(path, encoding="utf-8-sig")
#
#     @staticmethod
#     def load_artists_df() -> pd.DataFrame:
#         """Load the artists CSV into a DataFrame."""
#         path = DataCollector.ARTISTS_CSV
#         if not path.exists():
#             logger.warning("Artists CSV not found at %s", path)
#             return pd.DataFrame()
#         return pd.read_csv(path, encoding="utf-8-sig")


"""
services/collector.py
---------------------
Orchestrates data collection from Yandex Music, Last.fm, and Genius.
Converts raw API responses into TrackRecord / ArtistRecord objects
and persists them to CSV files for downstream analytics.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import pandas as pd

from api_clients import YandexMusicClient, LastFmClient, GeniusClient
from config.settings import (
    SEED_ARTISTS,
    MAX_TRACKS_PER_ARTIST,
    RAW_DIR,
    REQUEST_DELAY,
)
from data.models import ArtistRecord, TrackRecord
from utils.helpers import ms_to_min, safe_get
from utils.logger import get_logger

logger = get_logger(__name__)


class DataCollector:
    """
    High-level data collection pipeline using Yandex Music API.

    Usage:
        collector = DataCollector()
        collector.collect_all()        # fetch everything
        collector.load_tracks_df()     # returns pd.DataFrame
    """

    TRACKS_CSV = RAW_DIR / "tracks.csv"
    ARTISTS_CSV = RAW_DIR / "artists.csv"
    NETWORK_CSV = RAW_DIR / "artist_network.csv"

    def __init__(self) -> None:
        self.yandex = YandexMusicClient()
        self.lastfm = LastFmClient()
        self.genius = GeniusClient()

        self._artists: dict[str, ArtistRecord] = {}   # yandex_id → ArtistRecord
        self._tracks: list[TrackRecord] = []

    # ── Main entry point ───────────────────────────────────────────────────────

    def collect_all(self, artists: Optional[list[str]] = None) -> None:
        """
        Run the full collection pipeline for *artists* (default: SEED_ARTISTS).
        Saves results to CSV at the end.
        """
        targets = artists or SEED_ARTISTS
        logger.info("Starting data collection for %d artists …", len(targets))

        for name in targets:
            try:
                self._collect_artist(name)
            except Exception as exc:
                logger.error("Failed to collect data for '%s': %s", name, exc)
            time.sleep(REQUEST_DELAY)

        self._save_to_csv()
        logger.info(
            "Collection complete. %d artists, %d tracks saved.",
            len(self._artists), len(self._tracks),
        )

    # ── Per-artist collection ──────────────────────────────────────────────────

    def _collect_artist(self, name: str) -> None:
        """Collect all data for a single artist by name."""
        logger.info("Collecting: %s", name)

        # 1. Resolve artist via Yandex Music
        ya_artist = self.yandex.search_artist(name)
        if not ya_artist:
            logger.warning("Artist '%s' not found on Yandex Music", name)
            return

        artist_id = ya_artist["id"]
        genres = ya_artist.get("genres", [])
        if isinstance(genres, str):
            genres = [genres]
        followers = ya_artist.get("followers", 0)

        # 2. Last.fm supplementary data
        lfm_info = self.lastfm.get_artist_info(name)
        listeners = int(safe_get(lfm_info, "stats", "listeners", default=0) or 0)
        playcount = int(safe_get(lfm_info, "stats", "playcount", default=0) or 0)
        lfm_tags = self.lastfm.get_artist_tags(name)

        # 3. Related artists for network graph
        related = self.yandex.get_related_artists(artist_id)
        related_names = [r["name"] for r in related[:5]]

        # 4. Build ArtistRecord
        artist = ArtistRecord(
            spotify_id=artist_id,  # store yandex id here
            name=ya_artist.get("name", name),
            genres=genres,
            popularity=ya_artist.get("popularity", 50),
            followers=followers,
            lastfm_listeners=listeners,
            lastfm_playcount=playcount,
            lastfm_tags=lfm_tags,
            related_artists=related_names,
            image_url=ya_artist.get("image_url", ""),
        )
        self._artists[artist_id] = artist

        # 5. Collect top tracks + audio features
        ya_tracks = self.yandex.get_artist_top_tracks(artist_id)
        ya_tracks = ya_tracks[:MAX_TRACKS_PER_ARTIST]

        for ya_track in ya_tracks:
            self._build_track(ya_track, artist)

    def _build_track(
            self,
            ya_track: dict,
            artist: ArtistRecord,
    ) -> None:
        """Convert Yandex track + audio features into a TrackRecord."""
        tid = ya_track.get("id", "")

        # ПОЛУЧАЕМ РЕАЛЬНЫЙ ГОД ЧЕРЕЗ GENIUS
        release_year = None
        track_title = ya_track.get("name", "")

        if self.genius:
            try:
                release_year = self.genius.get_song_release_year(artist.name, track_title)
                if release_year:
                    logger.info(f"Found real year via Genius: {artist.name} - {track_title} -> {release_year}")
            except Exception as e:
                logger.debug(f"Genius year fetch failed for {artist.name}: {e}")

        # Если Genius не дал год, пробуем Last.fm
        if not release_year and self.lastfm:
            try:
                release_year = self.lastfm.get_track_release_date(artist.name, track_title)
                if release_year:
                    logger.info(f"Found real year via Last.fm: {artist.name} - {track_title} -> {release_year}")
            except Exception as e:
                logger.debug(f"Last.fm year fetch failed for {artist.name}: {e}")

        # Если всё ещё нет года — оставляем пустым (preprocessor заполнит)

        album_name = ya_track.get("album", "")

        # Get audio features (approximated from Yandex)
        audio_feats = self.yandex.get_track_audio_features(tid)

        # Genius lyrics snippet
        lyrics = self.genius.get_lyrics_text(artist.name, track_title) if self.genius else ""

        track = TrackRecord(
            track_id=tid,
            title=track_title,
            artist=artist.name,
            artist_id=artist.spotify_id,
            album=album_name,
            release_date="",
            release_year=release_year,  # ← реальный год или None
            popularity=ya_track.get("popularity", 50),
            duration_ms=ya_track.get("duration_ms", 0),
            duration_min=ms_to_min(ya_track.get("duration_ms", 0)),
            explicit=ya_track.get("explicit", False),
            preview_url="",
            spotify_url="",
            danceability=audio_feats.get("danceability", 0.5),
            energy=audio_feats.get("energy", 0.5),
            valence=audio_feats.get("valence", 0.5),
            acousticness=audio_feats.get("acousticness", 0.5),
            instrumentalness=audio_feats.get("instrumentalness", 0.1),
            liveness=audio_feats.get("liveness", 0.1),
            speechiness=audio_feats.get("speechiness", 0.05),
            tempo=audio_feats.get("tempo", 120.0),
            loudness=audio_feats.get("loudness", -8.0),
            key=audio_feats.get("key", 0),
            mode=audio_feats.get("mode", 1),
            time_signature=audio_feats.get("time_signature", 4),
            lyrics_snippet=lyrics,
        )
        self._tracks.append(track)

    # ── Persistence ────────────────────────────────────────────────────────────

    def _save_to_csv(self) -> None:
        """Persist collected data to CSV files."""
        # Tracks
        if self._tracks:
            df_tracks = pd.DataFrame([t.__dict__ for t in self._tracks])
            df_tracks.to_csv(self.TRACKS_CSV, index=False, encoding="utf-8-sig")
            logger.info("Saved %d tracks → %s", len(df_tracks), self.TRACKS_CSV)

        # Artists
        if self._artists:
            rows = []
            for ar in self._artists.values():
                row = ar.__dict__.copy()
                row["genres"] = "|".join(ar.genres)
                row["lastfm_tags"] = "|".join(ar.lastfm_tags)
                row["related_artists"] = "|".join(ar.related_artists)
                rows.append(row)
            df_artists = pd.DataFrame(rows)
            df_artists.to_csv(self.ARTISTS_CSV, index=False, encoding="utf-8-sig")
            logger.info("Saved %d artists → %s", len(df_artists), self.ARTISTS_CSV)

        # Network edges
        edges = []
        for ar in self._artists.values():
            for rel in ar.related_artists:
                edges.append({"source": ar.name, "target": rel})
        if edges:
            pd.DataFrame(edges).to_csv(self.NETWORK_CSV, index=False, encoding="utf-8-sig")
            logger.info("Saved %d network edges → %s", len(edges), self.NETWORK_CSV)

    # ── Data loaders ───────────────────────────────────────────────────────────

    @staticmethod
    def load_tracks_df() -> pd.DataFrame:
        """Load the tracks CSV into a DataFrame. Returns empty DF if missing."""
        path = DataCollector.TRACKS_CSV
        if not path.exists():
            logger.warning("Tracks CSV not found at %s", path)
            return pd.DataFrame()
        return pd.read_csv(path, encoding="utf-8-sig")

    @staticmethod
    def load_artists_df() -> pd.DataFrame:
        """Load the artists CSV into a DataFrame."""
        path = DataCollector.ARTISTS_CSV
        if not path.exists():
            logger.warning("Artists CSV not found at %s", path)
            return pd.DataFrame()
        return pd.read_csv(path, encoding="utf-8-sig")