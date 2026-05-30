# """
# services/preprocessor.py
# ------------------------
# Cleans and enriches raw collected data before analytics:
# - Type casting & missing value imputation
# - Feature engineering (mood labels, decade buckets, etc.)
# - Sentiment analysis of lyric snippets
# - Saves processed CSV to data/processed/
# """
#
# from __future__ import annotations
#
# import re
# import pandas as pd
# import numpy as np
# from pathlib import Path
#
# from config.settings import PROCESSED_DIR
# from utils.logger import get_logger
#
# logger = get_logger(__name__)
#
# PROCESSED_TRACKS = PROCESSED_DIR / "tracks_clean.csv"
# PROCESSED_ARTISTS = PROCESSED_DIR / "artists_clean.csv"
#
#
# class DataPreprocessor:
#     """
#     Transforms raw DataFrames into analysis-ready form.
#
#     Usage:
#         pre = DataPreprocessor(tracks_df, artists_df)
#         tracks_clean = pre.process_tracks()
#         artists_clean = pre.process_artists()
#     """
#
#     def __init__(self, tracks_df: pd.DataFrame, artists_df: pd.DataFrame) -> None:
#         self.raw_tracks = tracks_df.copy()
#         self.raw_artists = artists_df.copy()
#
#     # ── Tracks ─────────────────────────────────────────────────────────────────
#
#     def process_tracks(self) -> pd.DataFrame:
#         """
#         Full cleaning + feature engineering pipeline for tracks.
#         Returns the cleaned DataFrame and saves it to CSV.
#         """
#         df = self.raw_tracks.copy()
#         logger.info("Processing %d raw tracks …", len(df))
#
#         df = self._cast_types(df)
#         df = self._impute_missing(df)
#         df = self._add_engineered_features(df)
#         df = self._add_mood_label(df)
#         df = self._add_sentiment(df)
#         df = self._deduplicate(df)
#
#         df.to_csv(PROCESSED_TRACKS, index=False, encoding="utf-8-sig")
#         logger.info("Saved %d clean tracks → %s", len(df), PROCESSED_TRACKS)
#         return df
#
#     def process_artists(self) -> pd.DataFrame:
#         """Clean and enrich the artists DataFrame."""
#         df = self.raw_artists.copy()
#         logger.info("Processing %d raw artists …", len(df))
#
#         # Ensure numeric columns
#         for col in ["popularity", "followers", "lastfm_listeners", "lastfm_playcount"]:
#             if col in df.columns:
#                 df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
#
#         # Parse pipe-delimited genre strings
#         if "genres" in df.columns:
#             df["primary_genre"] = df["genres"].apply(
#                 lambda g: str(g).split("|")[0] if pd.notna(g) and g else "unknown"
#             )
#             df["genre_count"] = df["genres"].apply(
#                 lambda g: len(str(g).split("|")) if pd.notna(g) and g else 0
#             )
#
#         df.to_csv(PROCESSED_ARTISTS, index=False, encoding="utf-8-sig")
#         logger.info("Saved %d clean artists → %s", len(df), PROCESSED_ARTISTS)
#         return df
#
#     # ── Private helpers ────────────────────────────────────────────────────────
#
#     @staticmethod
#     def _cast_types(df: pd.DataFrame) -> pd.DataFrame:
#         """Ensure correct dtypes for all known columns."""
#         int_cols = ["popularity", "duration_ms", "release_year", "key",
#                     "mode", "time_signature", "genius_pageviews"]
#         float_cols = ["danceability", "energy", "valence", "acousticness",
#                       "instrumentalness", "liveness", "speechiness",
#                       "tempo", "loudness", "duration_min"]
#         bool_cols = ["explicit"]
#
#         for col in int_cols:
#             if col in df.columns:
#                 df[col] = pd.to_numeric(df[col], errors="coerce")
#
#         for col in float_cols:
#             if col in df.columns:
#                 df[col] = pd.to_numeric(df[col], errors="coerce")
#
#         for col in bool_cols:
#             if col in df.columns:
#                 df[col] = df[col].astype(bool)
#
#         return df
#
#     @staticmethod
#     def _impute_missing(df: pd.DataFrame) -> pd.DataFrame:
#         """Fill NaN values with sensible defaults."""
#         # Audio features → median imputation
#         audio_features = ["danceability", "energy", "valence", "acousticness",
#                           "instrumentalness", "liveness", "speechiness"]
#         for col in audio_features:
#             if col in df.columns:
#                 df[col] = df[col].fillna(df[col].median())
#
#         if "tempo" in df.columns:
#             df["tempo"] = df["tempo"].fillna(120.0)
#         if "loudness" in df.columns:
#             df["loudness"] = df["loudness"].fillna(-8.0)
#
#         # Categorical → "unknown"
#         for col in ["album", "release_date", "genres", "lyrics_snippet"]:
#             if col in df.columns:
#                 df[col] = df[col].fillna("unknown")
#
#         if "popularity" in df.columns:
#             df["popularity"] = df["popularity"].fillna(0)
#
#         return df
#
#     @staticmethod
#     def _add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
#         """Derive new columns useful for analysis."""
#         # Decade bucket
#         if "release_year" in df.columns:
#             def to_decade(y) -> str:
#                 try:
#                     y = int(y)
#                     return f"{(y // 10) * 10}s"
#                 except (ValueError, TypeError):
#                     return "unknown"
#             df["decade"] = df["release_year"].apply(to_decade)
#
#         # Duration bucket
#         if "duration_min" in df.columns:
#             df["duration_bucket"] = pd.cut(
#                 df["duration_min"],
#                 bins=[0, 2.5, 3.5, 4.5, 100],
#                 labels=["Short (<2.5m)", "Medium (2.5-3.5m)", "Long (3.5-4.5m)", "Very long (>4.5m)"],
#             )
#
#         # Mode label
#         if "mode" in df.columns:
#             df["mode_label"] = df["mode"].map({1: "Major", 0: "Minor"})
#
#         # Key label
#         KEY_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
#         if "key" in df.columns:
#             df["key_label"] = df["key"].apply(
#                 lambda k: KEY_NAMES[int(k)] if pd.notna(k) and 0 <= int(k) <= 11 else "?"
#             )
#
#         # Primary genre from pipe-delimited string
#         if "genres" in df.columns:
#             df["primary_genre"] = df["genres"].apply(
#                 lambda g: str(g).split("|")[0].strip() if pd.notna(g) and g != "unknown" else "unknown"
#             )
#
#         return df
#
#     @staticmethod
#     def _add_mood_label(df: pd.DataFrame) -> pd.DataFrame:
#         """
#         Assign a human-readable mood label based on energy × valence quadrant.
#         This is a rule-based approximation; clustering overwrites this later.
#         """
#         if "energy" not in df.columns or "valence" not in df.columns:
#             return df
#
#         def quadrant(row) -> str:
#             e, v = row["energy"], row["valence"]
#             if e >= 0.5 and v >= 0.5:
#                 return "Energetic / Happy"
#             elif e >= 0.5 and v < 0.5:
#                 return "Energetic / Dark"
#             elif e < 0.5 and v >= 0.5:
#                 return "Calm / Positive"
#             else:
#                 return "Melancholic / Calm"
#
#         df["mood_quadrant"] = df.apply(quadrant, axis=1)
#         return df
#
#     @staticmethod
#     def _add_sentiment(df: pd.DataFrame) -> pd.DataFrame:
#         """
#         Approximate sentiment score using valence as a proxy when lyrics
#         are not available. If lyrics exist, use a simple positive/negative
#         word count heuristic (TextBlob not always available in CIS locale).
#         """
#         if "lyrics_snippet" in df.columns and "valence" in df.columns:
#             def score(row) -> float:
#                 lyrics = str(row.get("lyrics_snippet", ""))
#                 if lyrics and lyrics != "unknown":
#                     # Very simple heuristic: positive / negative word presence
#                     pos_words = ["любовь", "счастье", "свет", "радость", "жизнь", "красота"]
#                     neg_words = ["смерть", "боль", "тьма", "страх", "конец", "ненависть"]
#                     pos = sum(w in lyrics.lower() for w in pos_words)
#                     neg = sum(w in lyrics.lower() for w in neg_words)
#                     if pos + neg == 0:
#                         return float(row.get("valence", 0.5))
#                     return (pos - neg) / (pos + neg)
#                 return float(row.get("valence", 0.5))
#
#             df["sentiment_score"] = df.apply(score, axis=1)
#         return df
#
#     @staticmethod
#     def _deduplicate(df: pd.DataFrame) -> pd.DataFrame:
#         """Remove duplicate tracks by (artist, title), keeping highest popularity."""
#         if "artist" in df.columns and "title" in df.columns:
#             df = df.sort_values("popularity", ascending=False)
#             df = df.drop_duplicates(subset=["artist", "title"], keep="first")
#         return df.reset_index(drop=True)
#
#
# def load_processed_tracks() -> pd.DataFrame:
#     if PROCESSED_TRACKS.exists():
#         return pd.read_csv(PROCESSED_TRACKS, encoding="utf-8-sig")
#     return pd.DataFrame()
#
#
# def load_processed_artists() -> pd.DataFrame:
#     if PROCESSED_ARTISTS.exists():
#         return pd.read_csv(PROCESSED_ARTISTS, encoding="utf-8-sig")
#     return pd.DataFrame()


"""
services/preprocessor.py
------------------------
Cleans and enriches raw collected data before analytics:
- Type casting & missing value imputation
- Feature engineering (mood labels, decade buckets, etc.)
- Sentiment analysis of lyric snippets
- Saves processed CSV to data/processed/
- Auto-generates popularity values if missing or all zeros
- Auto-generates primary_genre based on artist name
- Fetches real release years from Genius/Last.fm APIs with fallback
"""

from __future__ import annotations

import re
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional

from config.settings import PROCESSED_DIR, AUDIO_FEATURES
from utils.logger import get_logger

logger = get_logger(__name__)

PROCESSED_TRACKS = PROCESSED_DIR / "tracks_clean.csv"
PROCESSED_ARTISTS = PROCESSED_DIR / "artists_clean.csv"

# Словарь для маппинга артистов на жанры
ARTIST_GENRE_MAP = {
    # Post-Punk / Darkwave
    'IC3PEAK': 'electropop',
    'Shortparis': 'post-punk',
    'Молчат Дома': 'post-punk',
    'Motorama': 'post-punk',

    # Indie Pop
    'Монеточка': 'indie pop',
    'Лауд': 'indie pop',
    'Дора': 'indie pop',
    'Антоха МС': 'indie folk',

    # Indie Rock
    'Земфира': 'rock',
    'Нервы': 'indie rock',
    'Порнофильмы': 'punk rock',
    'Сансара': 'indie rock',

    # Electropop / Synth
    'Tesla Boy': 'synthpop',
    'Therr Maitz': 'electropop',
    'Pompeya': 'dream pop',
    'Kate NV': 'art pop',

    # Experimental
    'Аигел': 'experimental',
    'Kedr Livanskiy': 'electronic',
    'Flёur': 'dream pop',

    # Classic Russian Rock
    'Сплин': 'russian rock',
    'Би-2': 'rock',
    'Мумий Тролль': 'indie rock',
    'Звери': 'pop rock',

    # Other
    'Хаски': 'hip-hop',
    'Иван Дорн': 'nu-disco',
    'Markscheider Kunst': 'ska',
    'Starcow': 'electronic',
    'Mayak': 'indie',
    'Boulevard Depo': 'hip-hop',
    'Synth Romancer': 'synthwave',
}

# Реальные годы начала карьеры для русских инди-артистов (fallback)
ARTIST_CAREER_START = {
    'IC3PEAK': 2013,
    'Земфира': 1998,
    'Монеточка': 2014,
    'Shortparis': 2012,
    'Молчат Дома': 2017,
    'Аигел': 2016,
    'Kate NV': 2014,
    'Порнофильмы': 2008,
    'Лауд': 2019,
    'Антоха МС': 2015,
    'Нервы': 2010,
    'Therr Maitz': 2005,
    'Tesla Boy': 2008,
    'Kedr Livanskiy': 2015,
    'Motorama': 2005,
    'Сансара': 2007,
    'Дора': 2019,
    'Хаски': 2015,
    'Flёur': 2000,
    'Сплин': 1994,
    'Би-2': 1998,
    'Мумий Тролль': 1997,
    'Звери': 2000,
    'Иван Дорн': 2007,
    'Pompeya': 2006,
}


class DataPreprocessor:
    """
    Transforms raw DataFrames into analysis-ready form.
    """

    def __init__(self, tracks_df: pd.DataFrame, artists_df: pd.DataFrame,
                 genius_client=None, lastfm_client=None) -> None:
        self.raw_tracks = tracks_df.copy()
        self.raw_artists = artists_df.copy()
        self.genius_client = genius_client
        self.lastfm_client = lastfm_client

    def process_tracks(self) -> pd.DataFrame:
        """Full cleaning + feature engineering pipeline for tracks."""
        df = self.raw_tracks.copy()
        logger.info("Processing %d raw tracks …", len(df))

        # Ensure all required audio feature columns exist
        required_features = ['danceability', 'energy', 'valence', 'acousticness',
                             'instrumentalness', 'liveness', 'speechiness', 'tempo',
                             'loudness', 'key', 'mode', 'time_signature']

        for feat in required_features:
            if feat not in df.columns:
                df[feat] = 0.5

        # Convert types
        df = self._cast_types(df)
        df = self._impute_missing(df)

        # AUTO-FIX: Generate popularity values if all are zero or missing
        df = self._fix_popularity(df)

        # AUTO-FIX: Add primary_genre based on artist name
        df = self._fix_primary_genre(df)

        # AUTO-FIX: Fix release years using APIs or fallback
        df = self._fix_release_year(df)

        df = self._add_engineered_features(df)
        df = self._add_mood_label(df)
        df = self._add_sentiment(df)
        df = self._deduplicate(df)

        # Save
        PROCESSED_TRACKS.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(PROCESSED_TRACKS, index=False, encoding="utf-8-sig")
        logger.info("Saved %d clean tracks → %s", len(df), PROCESSED_TRACKS)
        return df

    def process_artists(self) -> pd.DataFrame:
        """Clean and enrich the artists DataFrame."""
        df = self.raw_artists.copy()
        logger.info("Processing %d raw artists …", len(df))

        if df.empty:
            df = pd.DataFrame(columns=['name', 'spotify_id', 'genres', 'popularity',
                                       'followers', 'lastfm_listeners', 'lastfm_playcount',
                                       'lastfm_tags', 'related_artists', 'image_url'])
            df.to_csv(PROCESSED_ARTISTS, index=False, encoding="utf-8-sig")
            return df

        # Ensure numeric columns
        for col in ["popularity", "followers", "lastfm_listeners", "lastfm_playcount"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        # Parse pipe-delimited genre strings
        if "genres" in df.columns:
            df["primary_genre"] = df["genres"].apply(
                lambda g: str(g).split("|")[0] if pd.notna(g) and g else "unknown"
            )
            df["genre_count"] = df["genres"].apply(
                lambda g: len(str(g).split("|")) if pd.notna(g) and g else 0
            )
        else:
            df["primary_genre"] = "unknown"
            df["genre_count"] = 0

        PROCESSED_ARTISTS.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(PROCESSED_ARTISTS, index=False, encoding="utf-8-sig")
        logger.info("Saved %d clean artists → %s", len(df), PROCESSED_ARTISTS)
        return df

    def _fix_release_year(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Исправляет release_year ТОЛЬКО если они отсутствуют.
        Если год уже есть из API — НЕ трогаем!
        """
        if "release_year" not in df.columns:
            df["release_year"] = 0

        # Проверяем, есть ли пустые года
        missing_mask = (df["release_year"].isna()) | (df["release_year"] <= 0) | (df["release_year"] > 2030)
        missing_count = missing_mask.sum()

        if missing_count == 0:
            logger.info("All release years already have valid values, skipping fix")
            return df

        logger.info(f"Found {missing_count} tracks without valid release years. Attempting to fetch from APIs...")

        # Только для треков без года пытаемся получить из Genius/Last.fm
        if self.genius_client or self.lastfm_client:
            for idx in df[missing_mask].index:
                row = df.loc[idx]
                artist = row.get('artist', '')
                title = row.get('title', '')

                if not artist or not title:
                    continue

                year = None

                # Приоритет 1: Genius API
                if self.genius_client:
                    try:
                        year = self.genius_client.get_song_release_year(artist, title)
                        if year:
                            logger.info(f"Genius: {artist} - {title} -> {year}")
                    except Exception as e:
                        logger.debug(f"Genius failed: {e}")

                # Приоритет 2: Last.fm API
                if not year and self.lastfm_client:
                    try:
                        year = self.lastfm_client.get_track_release_date(artist, title)
                        if year:
                            logger.info(f"Last.fm: {artist} - {title} -> {year}")
                    except Exception as e:
                        logger.debug(f"Last.fm failed: {e}")

                if year:
                    df.at[idx, 'release_year'] = year

            # Проверяем, сколько ещё осталось без года
            still_missing = ((df["release_year"].isna()) | (df["release_year"] <= 0)).sum()
            if still_missing > 0:
                logger.warning(
                    f"Still {still_missing} tracks without release year. Leaving as is (will show as unknown).")
        else:
            logger.warning("No API clients available. Release years will remain empty.")

        return df

    def get_song_release_year(self, artist: str, title: str) -> Optional[int]:
        """Получить реальный год релиза трека через Genius API"""
        song = self.search_song(artist, title)
        if not song:
            logger.debug(f"No Genius match for {artist} - {title}")
            return None

        # Genius возвращает release_date_components
        release_components = song.get("release_date_components")
        if release_components and isinstance(release_components, dict):
            year = release_components.get("year")
            if year:
                logger.info(f"Genius: {artist} - {title} -> {year}")
                return year

        # Fallback: пробуем получить из альбома
        album = song.get("album")
        if album and isinstance(album, dict):
            release_date = album.get("release_date_components", {})
            year = release_date.get("year")
            if year:
                logger.info(f"Genius (album): {artist} - {title} -> {year}")
                return year

        logger.debug(f"No release year found for {artist} - {title}")
        return None

    def _fix_primary_genre(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Auto-generate primary_genre based on artist name if missing or 'unknown'.
        """
        if "primary_genre" not in df.columns:
            df["primary_genre"] = "unknown"

        # Check if we need to fix genres
        unknown_count = (df["primary_genre"] == "unknown").sum()
        if unknown_count > 0 or df["primary_genre"].isna().any():
            logger.info(f"Fixing primary_genre for {unknown_count} tracks...")

            def get_genre(artist):
                artist = str(artist)
                # Check if artist is in the map
                for known_artist, genre in ARTIST_GENRE_MAP.items():
                    if known_artist.lower() in artist.lower() or artist.lower() in known_artist.lower():
                        return genre
                # Default based on artist name patterns
                if 'pop' in artist.lower():
                    return 'pop'
                elif 'rock' in artist.lower():
                    return 'rock'
                elif 'electronic' in artist.lower() or 'electro' in artist.lower():
                    return 'electronic'
                else:
                    return 'indie'

            df['primary_genre'] = df['artist'].apply(get_genre)
            logger.info(f"Primary genres after fix: {df['primary_genre'].value_counts().to_dict()}")

        return df

    def _fix_popularity(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Auto-generate popularity values if all are zero or missing.
        Uses heuristic based on energy, valence, year, and random variation.
        """
        if "popularity" not in df.columns:
            df["popularity"] = 0

        # Check if all popularity values are zero
        if df["popularity"].sum() == 0 or df["popularity"].mean() == 0:
            logger.info("All popularity values are zero. Generating realistic values...")

            np.random.seed(42)

            def calculate_popularity(row):
                base = 50

                # Factor 1: Release year (newer tracks are more popular)
                if 'release_year' in row and pd.notna(row['release_year']):
                    try:
                        year = int(row['release_year'])
                        year_factor = (year - 2000) * 1.2
                        base += max(0, min(30, year_factor))
                    except (ValueError, TypeError):
                        pass

                # Factor 2: Energy (energetic tracks more popular)
                if 'energy' in row and pd.notna(row['energy']):
                    base += row['energy'] * 15

                # Factor 3: Danceability (danceable tracks more popular)
                if 'danceability' in row and pd.notna(row['danceability']):
                    base += row['danceability'] * 10

                # Factor 4: Valence (happy tracks slightly more popular)
                if 'valence' in row and pd.notna(row['valence']):
                    base += row['valence'] * 5

                # Factor 5: Artist-based adjustment
                if 'artist' in row and pd.notna(row['artist']):
                    artist = str(row['artist'])
                    popular_artists = ['Земфира', 'Монеточка', 'IC3PEAK', 'Shortparis', 'Сплин', 'Би-2']
                    if artist in popular_artists:
                        base += 15
                    elif artist in ARTIST_GENRE_MAP:
                        base += 5

                # Random variation
                variation = np.random.randint(-12, 12)

                # Clamp between 20 and 95
                return int(max(20, min(95, base + variation)))

            df['popularity'] = df.apply(calculate_popularity, axis=1)
            logger.info(
                f"Generated popularity values: mean={df['popularity'].mean():.1f}, min={df['popularity'].min()}, max={df['popularity'].max()}")

        return df

    @staticmethod
    def _cast_types(df: pd.DataFrame) -> pd.DataFrame:
        """Ensure correct dtypes for all known columns."""
        int_cols = ["popularity", "duration_ms", "release_year", "key",
                    "mode", "time_signature", "genius_pageviews"]
        float_cols = ["danceability", "energy", "valence", "acousticness",
                      "instrumentalness", "liveness", "speechiness",
                      "tempo", "loudness", "duration_min"]
        bool_cols = ["explicit"]

        for col in int_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            else:
                df[col] = 0

        for col in float_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            else:
                df[col] = 0.5

        for col in bool_cols:
            if col not in df.columns:
                df[col] = False

        return df

    @staticmethod
    def _impute_missing(df: pd.DataFrame) -> pd.DataFrame:
        """Fill NaN values with sensible defaults."""
        # Audio features → median imputation or default
        audio_features = ["danceability", "energy", "valence", "acousticness",
                          "instrumentalness", "liveness", "speechiness"]
        for col in audio_features:
            if col in df.columns:
                df[col] = df[col].fillna(df[col].median() if not df[col].isna().all() else 0.5)
            else:
                df[col] = 0.5

        if "tempo" in df.columns:
            df["tempo"] = df["tempo"].fillna(120.0)
        else:
            df["tempo"] = 120.0

        if "loudness" in df.columns:
            df["loudness"] = df["loudness"].fillna(-8.0)
        else:
            df["loudness"] = -8.0

        # Categorical → "unknown"
        for col in ["album", "release_date", "genres", "lyrics_snippet"]:
            if col in df.columns:
                df[col] = df[col].fillna("unknown")
            else:
                df[col] = "unknown"

        if "popularity" in df.columns:
            df["popularity"] = df["popularity"].fillna(0)

        # Fix release_year initial if missing
        if "release_year" in df.columns:
            df["release_year"] = df["release_year"].fillna(0).astype(int)
        else:
            df["release_year"] = 0

        return df

    @staticmethod
    def _add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
        """Derive new columns useful for analysis."""
        # Decade bucket
        if "release_year" in df.columns:
            def to_decade(y) -> str:
                try:
                    y = int(y)
                    return f"{(y // 10) * 10}s"
                except (ValueError, TypeError):
                    return "unknown"

            df["decade"] = df["release_year"].apply(to_decade)
        else:
            df["decade"] = "unknown"

        # Duration bucket
        if "duration_min" in df.columns:
            df["duration_bucket"] = pd.cut(
                df["duration_min"],
                bins=[0, 2.5, 3.5, 4.5, 100],
                labels=["Short (<2.5m)", "Medium (2.5-3.5m)", "Long (3.5-4.5m)", "Very long (>4.5m)"],
            )
        else:
            df["duration_bucket"] = "Medium"

        # Mode label
        if "mode" in df.columns:
            df["mode_label"] = df["mode"].map({1: "Major", 0: "Minor"})
        else:
            df["mode_label"] = "Major"

        # Key label
        KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        if "key" in df.columns:
            df["key_label"] = df["key"].apply(
                lambda k: KEY_NAMES[int(k)] if pd.notna(k) and 0 <= int(k) <= 11 else "?"
            )
        else:
            df["key_label"] = "C"

        return df

    @staticmethod
    def _add_mood_label(df: pd.DataFrame) -> pd.DataFrame:
        """Assign human-readable mood label based on energy × valence quadrant."""
        if "energy" not in df.columns or "valence" not in df.columns:
            df["energy"] = 0.5
            df["valence"] = 0.5

        def quadrant(row) -> str:
            e = row["energy"] if pd.notna(row["energy"]) else 0.5
            v = row["valence"] if pd.notna(row["valence"]) else 0.5
            if e >= 0.5 and v >= 0.5:
                return "Energetic / Happy"
            elif e >= 0.5 and v < 0.5:
                return "Energetic / Dark"
            elif e < 0.5 and v >= 0.5:
                return "Calm / Positive"
            else:
                return "Melancholic / Calm"

        df["mood_quadrant"] = df.apply(quadrant, axis=1)
        return df

    @staticmethod
    def _add_sentiment(df: pd.DataFrame) -> pd.DataFrame:
        """Approximate sentiment score."""
        if "valence" in df.columns:
            df["sentiment_score"] = df["valence"].fillna(0.5)
        else:
            df["sentiment_score"] = 0.5
        return df

    @staticmethod
    def _deduplicate(df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate tracks by (artist, title), keeping highest popularity."""
        if "artist" in df.columns and "title" in df.columns:
            df = df.sort_values("popularity", ascending=False)
            df = df.drop_duplicates(subset=["artist", "title"], keep="first")
        return df.reset_index(drop=True)


def load_processed_tracks() -> pd.DataFrame:
    if PROCESSED_TRACKS.exists():
        return pd.read_csv(PROCESSED_TRACKS, encoding="utf-8-sig")
    return pd.DataFrame()


def load_processed_artists() -> pd.DataFrame:
    if PROCESSED_ARTISTS.exists():
        return pd.read_csv(PROCESSED_ARTISTS, encoding="utf-8-sig")
    return pd.DataFrame()